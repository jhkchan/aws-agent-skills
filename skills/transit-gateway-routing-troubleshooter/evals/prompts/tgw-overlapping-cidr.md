# Eval prompt: tgw-overlapping-cidr

Diagnose the Transit Gateway routing failure for the following topology.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: EC2 i-target (10.0.1.5) in VPC-A (10.0.0.0/16) is unreachable
from VPC-C (10.30.0.0/16) through TGW. Ping returns a reply from a
DIFFERENT host (a database in VPC-B that happens to use the same IP).
VPC-B's CIDR is 10.0.1.0/24, which overlaps with VPC-A's broader
10.0.0.0/16.

```text
TGW: tgw-aaa
Attachment A: tgw-attach-vpc-a (VPC vpc-a, CIDR 10.0.0.0/16)
Attachment B: tgw-attach-vpc-b (VPC vpc-b, CIDR 10.0.1.0/24)
Attachment C: tgw-attach-vpc-c (VPC vpc-c, CIDR 10.30.0.0/16)

TGW route table tgw-rtb-default:
  - 10.0.0.0/16 → tgw-attach-vpc-a (propagated, active)
  - 10.0.1.0/24 → tgw-attach-vpc-b (propagated, active)
  - 10.30.0.0/16 → tgw-attach-vpc-c (propagated, active)

VPC-C route table: 10.0.0.0/16 → tgw-aaa, 10.0.1.0/24 → tgw-aaa

i-target (10.0.1.5) lives in VPC-A's subnet, but the TGW longest-prefix
match sends 10.0.1.0/24 traffic to VPC-B.

No static routes in the TGW route table. All attachments are associated
with tgw-rtb-default.
```

TGW route table priority uses longest-prefix match: the more specific
10.0.1.0/24 route (VPC-B) shadows the broader 10.0.0.0/16 route (VPC-A)
for the overlapping subnet. Verify the CIDR overlap and recommend the
fix.
