# Baseline (no-skill) response: target-tracking-metric-selection

This file captures what a generic assistant produces WITHOUT the
ecs-cluster-autoscaling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, dual-metric policy,
memory target value rationale, OOM correlation analysis, CONFIRM gate).

---

Your Java services are running out of memory. The CPU utilization is
only 35% so your CPU-based auto-scaling never triggers, but memory is
at 92% and you're getting OOM killed tasks every day.

You should switch your target tracking metric from CPU to memory. This
way the auto-scaler will trigger scale-out when memory gets high.

To update the scaling policy:

```
aws application-autoscaling put-scaling-policy --policy-name jvm-memory-scaling --policy-type TargetTrackingScaling --resource-id service/ecs-target-tracking-metric-selection/api-service --scalable-dimension ecs:service:DesiredCount --service-namespace ecs --target-tracking-scaling-policy-configuration TargetValue=75.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageMemoryUtilization}
```

This should stop the OOM kills by scaling out before memory gets too high.
