# Worked Examples — VPC Connectivity Troubleshooter

Secondary worked examples and output-contract templates moved out of the SKILL.md body. Loaded on demand.

## NEED_MORE_INFO malformed-input template

```text
TARGET: <source → destination pair, or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum a symptom
  description (timeout, refused, DNS failure), a source identifier
  (instance / subnet / IP), a destination identifier (instance / IP /
  hostname), and the port and protocol under test.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed symptom, (2) the source identifier (EC2 instance / Lambda
  function name / ECS task / on-prem CIDR), (3) the destination
  identifier, and (4) the port/protocol under test.
```

## Worked example — NACL missing ephemeral outbound

```text
TARGET: i-app (10.0.1.10, subnet-aaa) → i-db (172.16.1.10,
  subnet-bbb) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination subnet's custom NACL (acl-bbb) has an inbound
  allow on tcp/5432 but no outbound allow on the ephemeral range
  (1024-65535) for the return SYN-ACK — the SYN reaches the
  destination but the SYN-ACK is dropped on the outbound evaluation
  (Step 2h).
LAYER: NACL_STATELESS
EVIDENCE:
  - Symptom: nc -vz 172.16.1.10 5432 from 10.0.1.10 hangs and times
    out. nc -vz in the reverse direction also fails.
  - Probe: aws ec2 describe-network-acls for subnet-bbb returns
    acl-bbb with inbound rule 100: tcp/5432 from 10.0.0.0/8 (allow)
    and outbound rule 100: tcp/5432 to 10.0.0.0/8 (allow) — but NO
    outbound rule for the ephemeral range (1024-65535). The default
    rule * denies all other outbound.
  - Passing: SG on both sides allows the rule; route table on both
    sides has the peering route; peering is Active; CIDRs do not
    overlap.
REMEDIATION:
  1. Add an outbound rule on acl-bbb for the ephemeral range back to
     the source CIDR:
     aws ec2 create-network-acl-entry --network-acl-id acl-bbb
       --rule-number 110 --protocol tcp --port-range From=1024,To=65535
       --cidr-block 10.0.0.0/8 --rule-action allow --egress --profile <p>
  2. Verify from the source: nc -vz 172.16.1.10 5432.
CONFIRM: Before modifying the NACL, emit and await operator approval.
```

## Worked example — overlapping CIDR (silent peering failure)

```text
TARGET: i-app (10.0.1.10, vpc-source 10.0.0.0/16) → i-db
  (10.0.2.10, vpc-target 10.0.0.0/16) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The source and destination VPCs both use 10.0.0.0/16. AWS
  silently refuses to route traffic between overlapping CIDRs via
  peering. The peering connection pcx-aaa is Active but packets do
  not deliver (Step 2d).
LAYER: ROUTE_OVERLAPPING_CIDR
EVIDENCE:
  - Symptom: nc -vz 10.0.2.10 5432 from 10.0.1.10 times out despite
    peering being Active, route tables both having the pcx route,
    SGs allowing the rule, and NACLs being default.
  - Probe: aws ec2 describe-vpcs for both VPCs returns
    CidrBlock 10.0.0.0/16 for each.
  - Passing: peering Active; route tables correct; SGs correct;
    NACLs default.
REMEDIATION:
  1. Renumber one VPC to a non-overlapping CIDR (e.g., change vpc-
     target to 10.99.0.0/16). This requires recreating subnets,
     updating route tables, and migrating workloads — plan a
     maintenance window.
  2. Or migrate the connectivity to a Transit Gateway with
     PrivateLink overlay for network translation. This avoids
     renumbering but adds complexity.
  3. Verify after renumbering: nc -vz 10.0.2.10 5432 from 10.0.1.10
     (with the new subnet's IP) succeeds.
CONFIRM: VPC renumbering is a major change. Emit and await operator
  approval before any state-changing CLI.
```

## Worked example — VPC endpoint policy blocking S3 PutObject

```text
TARGET: i-app (10.0.1.10, vpc-source) → s3:PutObject on
  arn:aws:s3:::logs-bucket-prod/*
VERDICT: ROOT_CAUSE_FOUND
REASON: The S3 VPC Gateway endpoint (vpce-aaa) policy allows only
  s3:GetObject; s3:PutObject is denied by the endpoint policy even
  though the IAM role allows it. Bypassing the endpoint (over NAT)
  succeeds — confirming the endpoint policy is the cause.
LAYER: ENDPOINT_POLICY
EVIDENCE:
  - Symptom: application on i-app fails to upload to
     s3://logs-bucket-prod/ with AccessDenied. The IAM role policy
     includes s3:PutObject on the bucket ARN (verified via
     simulate-principal-policy).
  - Probe: aws ec2 describe-vpc-endpoints for vpce-aaa returns a
     policy with a single statement: Allow s3:GetObject on
     arn:aws:s3:::logs-bucket-prod/*. No statement allows
     s3:PutObject.
  - Probe: bypass the endpoint (route via a NAT Gateway in a test
     subnet) — s3:PutObject succeeds. This confirms the endpoint
     policy is the cause.
  - Passing: IAM policy allows; bucket policy allows; network
    path is fine.
REMEDIATION:
  1. Update the endpoint policy to allow s3:PutObject:
     aws ec2 modify-vpc-endpoint --vpc-endpoint-id vpce-aaa
       --policy-document '<JSON with Allow statement for
       s3:PutObject on the bucket ARN>' --profile <p>
  2. Verify from the source: re-run the upload; it should succeed.
  3. Re-enable the endpoint for production traffic once verified.
CONFIRM: Before modifying the endpoint policy, emit and await
  operator approval.
```

## Required output structure — literal block template

```text
TARGET: <source → destination pair, including IPs / subnets / VPCs>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <one of the 18 LAYER enum values — never blank, never prose>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out, with the probe that ruled them out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <id> in <region>. Proceed?
  (yes/no)"
```

## Perfect example output

```text
TARGET: i-app (10.0.1.10, subnet-aaa, vpc-source) → i-db
  (172.16.1.10, subnet-bbb, vpc-target) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination SG sg-db has no inbound rule matching the
  source CIDR 10.0.1.0/24 on port 5432 — the SYN is dropped at the
  instance's security group (Step 2e).
LAYER: SG_INBOUND
EVIDENCE:
  - Symptom: application on i-app (10.0.1.10) reports "Operation
    timed out" connecting to i-db (172.16.1.10:5432). nc -vz hangs.
  - Probe: aws ec2 describe-security-groups --group-ids sg-db returns
    inbound rules allowing 172.16.0.0/16 on 5432 only — no rule
    matches 10.0.1.0/24 (source VPC CIDR).
  - Passing: route table for subnet-aaa has pcx-aaa route to
    172.16.0.0/16; route table for subnet-bbb has pcx-aaa route back
    to 10.0.0.0/16; peering pcx-aaa is Active; VPC CIDRs do not
    overlap; NACL on both subnets allows inbound 5432 AND outbound
    ephemeral 1024-65535 (verified in both directions).
REMEDIATION:
  1. Add an inbound rule to sg-db for the source CIDR on tcp/5432:
     aws ec2 authorize-security-group-ingress --group-id sg-db \
       --protocol tcp --port 5432 --cidr 10.0.1.0/24
  2. Verify from the source: nc -vz 172.16.1.10 5432 (should succeed
     within 1s).
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-db in
   us-east-1 for 10.0.1.0/24 on tcp/5432. Proceed? (yes/no)"
```
