# Eval prompt: sg-inbound-dead-cross-vpc-ref

Diagnose the VPC connectivity failure for the following source-destination
pair. Walk the OSI-aligned diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application on `i-app` (private IP 10.0.1.10, subnet
subnet-app, SG sg-app, AZ us-east-1a, VPC vpc-source 10.0.0.0/16)
cannot reach `i-db` (private IP 172.16.1.10, subnet subnet-db, SG sg-db,
AZ us-east-1b, VPC vpc-target 172.16.0.0/16) on tcp/5432. `nc -vz
172.16.1.10 5432` hangs and returns "Connection timed out" after 10
seconds. No error appears in the PostgreSQL log.

```text
Peering: pcx-aaa between vpc-source and vpc-target, status Active.
Both VPCs' route tables have a pcx-aaa route to the other VPC's CIDR.

NACLs (both subnets): default VPC NACL (allow all in and out).

SG sg-db inbound rules:
  - tcp/5432 from sg-app-old (a deleted security group)
  - tcp/5432 from 172.16.0.0/16 (same-VPC admin access)

SG sg-app egress: allow all.
```

Walk OSI order: DNS (skipped — IP used), routing (passes — peering
Active + routes both ways), overlapping CIDRs (passes — non-overlapping
CIDRs), SG destination inbound (the focus), SG source outbound, NACL
both subnets both directions, final `nc -vz`.
