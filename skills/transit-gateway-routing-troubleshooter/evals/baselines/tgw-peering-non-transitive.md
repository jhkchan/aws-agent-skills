# Baseline (no-skill) response: tgw-peering-non-transitive

---

Your VPC on tgw-a can't reach the VPC on tgw-c. You have peerings from
tgw-a to tgw-b and tgw-b to tgw-c, so traffic should be able to hop
through tgw-b. Check that the route tables on all three TGWs have
routes for the destination CIDRs.

If the routes look right, the peering attachments might not be fully
established. Try verifying the peering states on both sides. You might
also want to check if there's a firewall or security group blocking
the traffic.
