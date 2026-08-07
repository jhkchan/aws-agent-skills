# Baseline (no-skill) response: route-overlapping-cidr-silent

---

Your EC2 instance can't reach the database in the peered VPC. Both
VPCs use 10.0.0.0/16, which might be a problem. AWS doesn't allow
overlapping CIDRs in VPC peering — you'd need to use a Transit Gateway
with network translation or renumber one of the VPCs.

Try setting up a Transit Gateway between the two VPCs instead, or
renumber vpc-b to a different CIDR like 10.99.0.0/16.
