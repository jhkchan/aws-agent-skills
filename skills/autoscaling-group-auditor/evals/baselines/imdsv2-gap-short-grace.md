# Baseline (no-skill) response: imdsv2-gap-short-grace

This file captures what a generic assistant produces WITHOUT the
autoscaling-group-auditor skill loaded.

---

This ASG has a launch template with IMDSv2 set to optional instead of
required. You should require IMDSv2 for better security.

The health check grace period is only 30 seconds, which seems short. The
health check type is ELB with a target group attached, which is good. The
mixed instances policy looks well configured with 3 instance types and a
good mix of On-Demand and Spot.

Capacity rebalance is enabled which is good for Spot instances.
