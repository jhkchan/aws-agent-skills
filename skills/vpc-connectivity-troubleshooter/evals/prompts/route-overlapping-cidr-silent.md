# Eval prompt: route-overlapping-cidr-silent

Diagnose the VPC connectivity failure for the following source-destination
pair. Walk the OSI-aligned diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `i-app` (private IP 10.0.1.10, subnet subnet-app in vpc-a,
CIDR 10.0.0.0/16) cannot reach `i-db` (private IP 10.0.2.10, subnet
subnet-db in vpc-b, CIDR 10.0.0.0/16) on tcp/5432. `nc -vz 10.0.2.10
5432` hangs and times out. Both VPCs are in us-east-1.

```text
Peering: pcx-aaa between vpc-a and vpc-b, status Active.

Route tables:
  - subnet-app (vpc-a): local 10.0.0.0/16 + pcx-aaa →
    10.0.0.0/16 (note: same destination as local route; AWS silently
    prefers local route over peering route for overlapping CIDRs)
  - subnet-db (vpc-b): local 10.0.0.0/16 + pcx-aaa →
    10.0.0.0/16

SG sg-db inbound: tcp/5432 from 10.0.0.0/16 (allow).
SG sg-app egress: allow all.

NACLs (both subnets): default (allow all in and out).

VPC CIDRs:
  - vpc-a: 10.0.0.0/16
  - vpc-b: 10.0.0.0/16
```

All the SG, NACL, and route-table checks "pass" — but packets never
deliver. The VPC CIDR overlap is the silent failure. AWS refuses to
route traffic for a CIDR that exists on both sides of a peering
connection.
