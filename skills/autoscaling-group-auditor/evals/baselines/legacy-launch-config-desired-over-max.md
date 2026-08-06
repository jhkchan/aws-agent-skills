# Baseline (no-skill) response: legacy-launch-config-desired-over-max

This file captures what a generic assistant produces WITHOUT the
autoscaling-group-auditor skill loaded.

---

This ASG is using a launch configuration which is the older way to configure
instances. You should consider migrating to a launch template.

Also, the desired capacity (6) is higher than the max size (4), which doesn't
make sense. The ASG would try to launch 6 instances but the max is capped at 4.

The health check is set to EC2 which is fine for a batch workload.
