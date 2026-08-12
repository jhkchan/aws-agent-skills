# Baseline (no-skill) response: tgw-static-route-overrides-propagated

---

Your VPC-A can't reach VPC-B through the transit gateway. Since both
VPCs are attached to the TGW and the VPC route tables look correct,
the issue is probably in the TGW route table. Check that there's a
route for 10.20.0.0/16 pointing at the VPC-B attachment.

If the route exists, maybe the attachment isn't in the right state, or
there's a security group blocking the traffic. You could also try
deleting and re-adding the VPC-B attachment.
