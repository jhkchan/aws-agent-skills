# Baseline (no-skill) response: elb-healthcheck-no-targetgroup

This file captures what a generic assistant produces WITHOUT the
autoscaling-group-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, infinite-loop reasoning).

---

This ASG uses ELB health checks but I don't see any target groups or load
balancers attached. That might be a problem since the health check needs a
target to check against.

The launch template looks fine with IMDSv2 required. The capacity settings
seem reasonable (min 2, max 6, desired 4). The grace period of 300 seconds
is standard.

You should probably attach a target group or switch to EC2 health checks
if this ASG doesn't need ELB integration.
