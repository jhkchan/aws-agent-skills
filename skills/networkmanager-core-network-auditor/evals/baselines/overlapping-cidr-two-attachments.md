# Baseline (no-skill) response: overlapping-cidr-two-attachments

This file captures what a generic assistant produces WITHOUT the
networkmanager-core-network-auditor skill loaded.

---

This core network has two VPC attachments with overlapping IP ranges.
The prod segment attachment advertises 10.0.0.0/16 while the
non-prod segment attachment advertises 10.0.1.0/24. Since 10.0.1.0/24
is inside 10.0.0.0/16, these ranges overlap, which could cause routing
problems — traffic to addresses in the overlap range might go to
either VPC.

The resource policy and segment policies look properly scoped. Both
attachments are in ATTACHED status.

You should change one of the VPC CIDR ranges so they do not overlap.
Alternatively, you could restrict which subnets are advertised to
avoid the overlap.
