# Baseline (no-skill) response: managed-scaling-migration

This file captures what a generic assistant produces WITHOUT the
ecs-cluster-autoscaling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, managed scaling + spot
+ binpack pairing, host reduction math, CONFIRM gate, drain workflow).

---

Your ECS cluster has a lot of wasted capacity. CPU utilization is only
35% and 8 out of 20 instances have no running tasks. Since you're
using the legacy cluster-autoscaler, it's probably not scaling in fast
enough to remove empty instances.

I'd recommend switching to ECS managed scaling, which is the native
replacement for cluster-autoscaler. You could also consider using spot
instances since your workloads are stateless.

To enable managed scaling:

```
aws ecs update-capacity-provider --name on-demand-cp --auto-scaling-group-provider managedScaling.status=ENABLED
```

You might also want to reduce your ASG MinSize to allow more scale-in.
