# Baseline (no-skill) response: tgw-route-propagation-missing

---

Your traffic between the two VPCs on the Transit Gateway isn't
flowing. Both attachments are Available, but you need to make sure
the TGW route table has routes for both VPCs' CIDRs. Check that
route propagation is enabled on the TGW route table for both
attachments.

It looks like vpc-b's attachment is associated but not propagating,
so the TGW route table has no route for 10.2.0.0/16. You need to
enable propagation for tgw-attach-b on tgw-rtb-default.
