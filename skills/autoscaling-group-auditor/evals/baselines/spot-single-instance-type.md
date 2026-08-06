# Baseline (no-skill) response: spot-single-instance-type

This file captures what a generic assistant produces WITHOUT the
autoscaling-group-auditor skill loaded.

---

This ASG uses a mixed instances policy with Spot instances. It's only using
c5.large as the instance type with 0% On-Demand, meaning all instances are
Spot. The allocation strategy is capacity-optimized which is good.

Capacity rebalance is not enabled, which you might want to turn on for Spot
instances.

The launch template has IMDSv2 required which is good practice.
