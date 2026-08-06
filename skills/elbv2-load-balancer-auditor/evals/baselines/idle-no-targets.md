# Baseline (no-skill) response: idle-no-targets

This file captures what a generic assistant produces WITHOUT the
elbv2-load-balancer-auditor skill loaded.

---

The target group for this load balancer has zero registered targets. This
means the load balancer is accepting traffic but has nowhere to forward it,
so clients will get errors. You should either register targets or consider
deleting this load balancer if it's no longer needed.
