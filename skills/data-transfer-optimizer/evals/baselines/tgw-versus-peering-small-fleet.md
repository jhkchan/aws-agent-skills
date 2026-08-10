# Baseline (no-skill) response: tgw-versus-peering-small-fleet

---

You're spending $309/month on Transit Gateway for just 3 VPCs.
VPC peering is free for intra-region traffic. You should consider
switching to peering connections between the VPCs to eliminate the
TGW charges.

You'd need to set up 3 peering connections (A-B, A-C, B-C) and
update the route tables.
