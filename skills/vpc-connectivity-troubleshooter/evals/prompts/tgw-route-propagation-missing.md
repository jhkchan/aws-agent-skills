# Eval prompt: tgw-route-propagation-missing

Diagnose the VPC connectivity failure for the following source-destination
pair. Walk the OSI-aligned diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `i-app` (private IP 10.1.1.10, subnet subnet-a, vpc-a
10.1.0.0/16) cannot reach `i-db` (private IP 10.2.1.10, subnet
subnet-b, vpc-b 10.2.0.0/16) on tcp/5432. `nc -vz 10.2.1.10 5432`
hangs and times out. Both VPCs are in us-east-1.

```text
Transit Gateway tgw-shared:
  - Attachment tgw-attach-a: vpc-a, state Available,
    associated with TGW route table tgw-rtb-default,
    propagation ENABLED on tgw-rtb-default
  - Attachment tgw-attach-b: vpc-b, state Available,
    associated with TGW route table tgw-rtb-default,
    propagation DISABLED on tgw-rtb-default

TGW route table tgw-rtb-default contents:
  - Static route: 10.1.0.0/16 via tgw-attach-a (added by
    propagation from vpc-a's attachment)
  - NO route for 10.2.0.0/16 — vpc-b's CIDR is not propagated
    into tgw-rtb-default

VPC route tables:
  - subnet-a (vpc-a): local 10.1.0.0/16 + tgw-shared →
    10.2.0.0/16 (operator added this manually expecting it
    to work)
  - subnet-b (vpc-b): local 10.2.0.0/16 + tgw-shared →
    10.1.0.0/16

SG sg-db inbound: tcp/5432 from 10.1.0.0/16 (allow).
SG sg-app egress: allow all.

NACLs (both subnets): default (allow all).
```

Both attachments are Available and both VPC route tables have the
TGW route — but tgw-rtb-default has no route for vpc-b's CIDR because
vpc-b's attachment does not propagate into it. TGW propagation is
per-attachment per-route-table, not automatic.
