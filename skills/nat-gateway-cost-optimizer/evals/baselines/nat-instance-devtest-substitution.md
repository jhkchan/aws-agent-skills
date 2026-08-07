# Baseline (no-skill) response: nat-instance-devtest-substitution

This file captures what a generic assistant produces WITHOUT the
nat-gateway-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, NAT Instance cost model,
reliability warning surfacing, S3 Gateway endpoint layering).

---

For a dev environment with 2 TB of NAT traffic, a NAT Instance could save
you money since it's a fixed cost instead of per-GB. You can set up a t3
micro with a NAT AMI and route your traffic through it instead. Also you
should add an S3 Gateway endpoint since that's free. With 1,500 GB of S3
traffic that would save a lot.
