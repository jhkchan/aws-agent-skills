# Example usage: vpc-connectivity-troubleshooter

A walkthrough showing the skill diagnosing a cross-VPC connectivity
failure that looks like an application outage, demonstrating the
OSI-aligned probe order, the cross-VPC security-group reference
gotcha, the silent-failure pattern, and the evidence-backed
ROOT_CAUSE_FOUND verdict.

## Input (user prompt)

> Our payments service in vpc-source (10.0.0.0/16) cannot reach the
> orders database in vpc-target (172.16.0.0/16) on tcp/5432. telnet
> hangs and times out. The two VPCs are peered (pcx-aaa, status:
> Active). We've been debugging this as a database outage for 30
> minutes — please help us find the actual root cause.

```text
Source: i-app-payments (private IP 10.0.1.10, subnet subnet-app,
  CIDR 10.0.1.0/24, SG sg-app-payments, AZ us-east-1a, VPC vpc-source
  10.0.0.0/16)
Destination: i-db-orders (private IP 172.16.1.10, subnet subnet-db,
  CIDR 172.16.1.0/24, SG sg-db-orders, AZ us-east-1b, VPC vpc-target
  172.16.0.0/16)
Path: same region (us-east-1), VPC peering pcx-aaa (Active)

Observed: nc -vz 172.16.1.10 5432 from i-app-payments hangs and
returns "Connection timed out" after 10 seconds. No error appears in
the PostgreSQL log.

Route tables:
  - subnet-app: local 10.0.0.0/16 + pcx-aaa → 172.16.0.0/16
  - subnet-db: local 172.16.0.0/16 + pcx-aaa → 10.0.0.0/16

NACLs (both subnets): default VPC NACL (allow all in and out)

SG sg-db-orders inbound rules:
  - tcp/5432 from sg-app-payments-old (the previous payments app SG;
    sg-app-payments-old was DELETED last week during an SG cleanup)
  - tcp/5432 from 172.16.0.0/16 (same-VPC admin access)

SG sg-app-payments egress: allow all
```

## Skill output

```text
TARGET: i-app-payments (10.0.1.10, subnet-app, vpc-source) → i-db-
  orders (172.16.1.10, subnet-db, vpc-target) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination SG sg-db-orders has no inbound rule matching
  the caller's source CIDR 10.0.1.0/24 on tcp/5432. The only
  cross-VPC rule references sg-app-payments-old, which is a deleted
  security group — the rule is silently dead. The local-VPC rule
  (172.16.0.0/16) does not match the cross-VPC caller. The SYN is
  dropped at the instance's security group (Step 2e).
LAYER: SG_INBOUND
EVIDENCE:
  - Symptom: application on i-app-payments (10.0.1.10) reports
    "Operation timed out" connecting to i-db-orders:5432. nc -vz
    hangs and times out after 10 seconds.
  - Probe: aws ec2 describe-security-groups --group-ids sg-db-orders
    returns inbound rules allowing tcp/5432 from sg-app-payments-old
    and tcp/5432 from 172.16.0.0/16. sg-app-payments-old is in a
    DELETED state (cross-verify: aws ec2 describe-security-groups
    --group-ids sg-app-payments-old returns InvalidGroup.NotFound).
    Neither rule matches the caller's source CIDR 10.0.1.0/24.
  - Probe: aws ec2 describe-security-groups --group-ids
    sg-app-payments confirms the caller's SG exists in vpc-source
    (10.0.0.0/16), which is peered with vpc-target via pcx-aaa. A
    CIDR rule for 10.0.0.0/16 (or 10.0.1.0/24) on sg-db-orders would
    work, OR a referenced-SG rule if the peering route is in the
    route table.
  - Passing: route table for subnet-app has pcx-aaa → 172.16.0.0/16;
    route table for subnet-db has pcx-aaa → 10.0.0.0/16; peering
    pcx-aaa is Active; VPC CIDRs do not overlap (10.0.0.0/16 vs
    172.16.0.0/16); NACLs on both subnets are default (allow all);
    the caller's SG egress allows all; nc -vz from a bastion in
    subnet-db to 172.16.1.10:5432 succeeds.
REMEDIATION:
  1. Replace the dead SG reference with a CIDR rule for the source
     VPC CIDR (peering is in the route table, so the rule will match):
     aws ec2 revoke-security-group-ingress --group-id sg-db-orders
       --protocol tcp --port 5432 --source-security-group-id
       sg-app-payments-old
     aws ec2 authorize-security-group-ingress --group-id sg-db-orders
       --protocol tcp --port 5432 --cidr 10.0.0.0/16 --profile <p>
  2. (Alternative) Use a referenced SG in vpc-target that mirrors the
     caller's identity. This requires creating sg-app-payments-mirror
     in vpc-target and applying it to the resources that need the
     rule. CIDR is simpler for cross-VPC.
  3. Verify from the caller: nc -vz 172.16.1.10 5432 (should now
     succeed within 1s).
  4. Restart the application's connection pool to clear failed
     connection attempts.
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to revoke sg-app-payments-old and authorize
   10.0.0.0/16 on sg-db-orders in us-east-1 for tcp/5432. Proceed?
   (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **The dead SG reference.** A generic assistant says "check the
   security group." The skill recognises that `sg-app-payments-old`
   was deleted last week and the inbound rule referencing it is
   silently ignored. The application's new SG
   (`sg-app-payments`) was never added to `sg-db-orders`. An
   operator staring at the console sees "the SG has a rule for
   sg-app-payments" and assumes it works.

2. **OSI-aligned probe order.** The skill ran the route table, SG,
   NACL, and peering checks in order — and confirmed each layer
   passed before concluding the SG was the cause. A generic assistant
   jumps to "it must be the SG" without ruling out routing, NACL, or
   peering issues.

3. **The local-VPC rule does not match.** The skill recognises that
   the `172.16.0.0/16` rule on `sg-db-orders` is for same-VPC admin
   access, not for the cross-VPC caller. A generic assistant sees "a
   5432 rule exists" and stops. The skill distinguishes same-VPC vs
   cross-VPC reachability and verifies which rule applies.

4. **Evidence-backed verdict.** The skill produces a positive failing
   probe (the describe-security-groups output showing only the dead
   reference and the local-VPC rule) AND passing probes (route
   tables, peering, NACLs, caller egress, bastion reachability). A
   generic assistant asserts the cause without evidence; an operator
   implementing the wrong fix loses another 30 minutes.

5. **Preserve the dead rule's revoke.** The skill includes
   `revoke-security-group-ingress` for the dead reference, not just
   the authorize for the new CIDR. Dead references accumulate in
   long-lived security groups; cleaning them up prevents future
   confusion.

## Slash-command invocation

```
/aws:troubleshoot-vpc-connectivity
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why i-app-payments in vpc-source cannot reach
      i-db-orders in vpc-target on tcp/5432"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: vpc-connectivity-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the connectivity from the source host:

```bash
# Confirm the SG rule now references the live caller CIDR
aws ec2 describe-security-groups --group-ids sg-db-orders \
  --profile default --output json | \
  jq '.SecurityGroups[].IpPermissions[] | select(.FromPort == 5432)'

# Confirm TCP reachability from the application host
ssh i-app-payments --profile default
nc -vz 172.16.1.10 5432

# Run Reachability Analyzer to confirm the path
PATH_ID=$(aws ec2 create-network-insights-path \
  --source $(aws ec2 describe-instances --instance-ids i-app-payments \
    --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
    --output text) \
  --destination $(aws ec2 describe-instances --instance-ids i-db-orders \
    --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
    --output text) \
  --destination-port 5432 --protocol tcp \
  --output text --query 'NetworkInsightsPath.NetworkInsightsPathId')

aws ec2 start-network-insights-analysis \
  --network-insights-path-id $PATH_ID --profile default
```

Then monitor CloudTrail for `AuthorizeSecurityGroupIngress` and
`RevokeSecurityGroupIngress` events on `sg-db-orders` for 1-2 weeks to
confirm no further drift.
