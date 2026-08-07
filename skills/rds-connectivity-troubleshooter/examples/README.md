# Example usage: rds-connectivity-troubleshooter

A walkthrough showing the skill diagnosing a connection timeout that
mimics an engine-level outage, demonstrating the OSI-aligned probe order,
the security-group cross-VPC reference gotcha, and the evidence-backed
ROOT_CAUSE_FOUND verdict.

## Input (user prompt)

> Our payments service started failing at 03:17 UTC. The application
> cannot reach the RDS MySQL writer. telnet hangs. We've been debugging
> this as a database outage for 30 minutes — please help us find the
> actual root cause.

```text
DBInstanceIdentifier: db-payments-prod-mysql
Engine: mysql
DBInstanceStatus: available
Endpoint: db-payments-prod-mysql.cid.on.aws:3306
VpcSecurityGroups: [{VpcSecurityGroupId: sg-rds-prod, Status: active}]
Security group sg-rds-prod inbound rules:
  - tcp/3306 from sg-app-payments-old (a deleted security group)

Caller context: i-app-payments-v2 (private IP 10.42.5.10, subnet
subnet-payments-v2, security group sg-app-payments-v2, AZ us-east-1a).
Subnet-payments-v2 was provisioned last week as part of a VPC refresh.
NACL: default VPC NACL. Route table: local route to RDS CIDR.
```

## Skill output

```text
TARGET: db-payments-prod-mysql
VERDICT: ROOT_CAUSE_FOUND
REASON: The RDS security group sg-rds-prod has no inbound rule matching
  the caller's security group sg-app-payments-v2. The only inbound rule
  references sg-app-payments-old, which is a deleted security group —
  the rule is silently dead. The SYN is dropped at the instance's
  security group (Step 2b).
LAYER: NETWORK_SG
EVIDENCE:
  - Symptom: application on i-app-payments-v2 (10.42.5.10) reports
    "Operation timed out" connecting to db-payments-prod-mysql:3306.
    telnet hangs and times out after 10 seconds.
  - Probe: aws ec2 describe-security-groups --group-ids sg-rds-prod
    returns inbound rules allowing tcp/3306 from sg-app-payments-old
    only. sg-app-payments-old is in a DELETED state
    (cross-verify: aws ec2 describe-security-groups --group-ids
    sg-app-payments-old returns InvalidGroup.NotFound).
  - Probe: aws ec2 describe-security-groups --group-ids
    sg-app-payments-v2 confirms the caller's SG exists in the SAME VPC
    as sg-rds-prod (vpc-aaa) — a referenced-SG rule would work if
    added.
  - Passing: route table for subnet-payments-v2 has a local route to
    the RDS CIDR; NACL is the default VPC NACL (allow all in/out); the
    caller's SG egress allows all; nc -vz from a bastion in the
    payments VPC succeeds against the RDS endpoint on 3306.
REMEDIATION:
  1. Replace the dead SG reference with the new caller SG:
     aws ec2 revoke-security-group-ingress --group-id sg-rds-prod
       --protocol tcp --port 3306 --source-security-group-id
       sg-app-payments-old
     aws ec2 authorize-security-group-ingress --group-id sg-rds-prod
       --protocol tcp --port 3306 --source-security-group-id
       sg-app-payments-v2 --profile <p>
  2. Verify from the caller: nc -vz db-payments-prod-mysql.cid.on.aws 3306
     (should now succeed within 1s).
  3. Restart the application's connection pool to clear failed
     connection attempts.
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to revoke sg-app-payments-old and authorize
   sg-app-payments-v2 on sg-rds-prod in us-east-1 for tcp/3306.
   Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **The dead SG reference.** A generic assistant says "check the security
   group." The skill recognises that `sg-app-payments-old` was deleted
   and the inbound rule referencing it is silently ignored. The
   application's new SG (`sg-app-payments-v2`) was provisioned as part
   of the VPC refresh, but the RDS SG was never updated to reference it.
   An operator staring at the console sees "the SG has a rule for
   sg-app-payments" and assumes it works.

2. **OSI-aligned probe order.** The skill ran the source-IP, SG, NACL,
   and route checks in order — and confirmed each layer passed before
   concluding the SG was the cause. A generic assistant jumps to "it
   must be the SG" without ruling out routing, NACL, or subnet issues.

3. **Evidence-backed verdict.** The skill produces a positive failing
   probe (the describe-security-groups output showing only the dead
   reference) AND passing probes (route table, NACL, caller egress,
   bastion reachability). A generic assistant asserts the cause without
   evidence; an operator implementing the wrong fix loses another 30
   minutes.

4. **Preserve the dead rule's revoke.** The skill includes
   `revoke-security-group-ingress` for the dead reference, not just the
   authorize for the new SG. Dead references accumulate in long-lived
   security groups; cleaning them up prevents future confusion.

## Slash-command invocation

```
/aws:troubleshoot-rds-connectivity
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why the payments service can't reach db-payments-prod-mysql"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: rds-connectivity-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the connectivity from the caller host:

```bash
# Confirm the SG rule now references the live caller SG
aws ec2 describe-security-groups --group-ids sg-rds-prod \
  --profile default --output json | \
  jq '.SecurityGroups[].IpPermissions[].UserIdGroupPairs'

# Confirm TCP reachability from the application host
ssh i-app-payments-v2 --profile default
nc -vz db-payments-prod-mysql.cid.on.aws 3306
```

Then monitor CloudTrail for `AuthorizeSecurityGroupIngress` and
`RevokeSecurityGroupIngress` events on `sg-rds-prod` for 1-2 weeks to
confirm no further drift.
