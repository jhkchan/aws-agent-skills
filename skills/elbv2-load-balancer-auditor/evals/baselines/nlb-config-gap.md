# Baseline (no-skill) response: nlb-config-gap

This file captures what a generic assistant produces WITHOUT the
elbv2-load-balancer-auditor skill loaded.

---

This Network Load Balancer has cross-zone load balancing disabled and
deletion protection turned off. Cross-zone load balancing helps distribute
traffic evenly across availability zones. Deletion protection prevents
accidental deletion.

The NLB has a TCP listener with healthy targets and access logs are
enabled.
