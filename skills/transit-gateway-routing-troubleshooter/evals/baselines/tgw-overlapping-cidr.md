# Baseline (no-skill) response: tgw-overlapping-cidr

---

Your traffic to 10.0.1.5 is going to the wrong VPC. The TGW has routes
for both 10.0.0.0/16 (VPC-A) and 10.0.1.0/24 (VPC-B), and the more
specific route wins. You should either change the IP of the target
instance in VPC-A, or update the TGW route table to point 10.0.1.0/24
at VPC-A instead of VPC-B.

Alternatively, you could use a NAT gateway to translate the overlapping
addresses so both VPCs can coexist.
