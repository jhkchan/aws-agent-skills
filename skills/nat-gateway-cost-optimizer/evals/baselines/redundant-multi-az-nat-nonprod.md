# Baseline (no-skill) response: redundant-multi-az-nat-nonprod

This file captures what a generic assistant produces WITHOUT the
nat-gateway-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, cross-AZ cost modelling,
environment-aware topology).

---

For a staging environment you probably don't need two NAT Gateways. You can
delete one to save about $33/month on the base charge. Your traffic is low
at 80 GB so a single gateway should be fine. You might also want to add an
S3 endpoint if you have S3 traffic.
