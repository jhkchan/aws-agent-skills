# Baseline (no-skill) response: capacity-provider-spot

This file captures what a generic assistant produces WITHOUT the
ecs-task-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, spot base + on-demand top
strategy, interruption handling verification, CONFIRM gate, binpack
placement recommendation).

---

Your ECS service is running on EC2 with 100% on-demand instances. Since
it's a stateless web frontend that can tolerate interruption, you could
use Spot instances to save 30-70% on compute.

You can create a spot-backed capacity provider and assign it as the
default for your cluster:

```
aws ecs create-capacity-provider --name spot-cap-provider --auto-scaling-group-provider autoScalingGroupArn=<spot-asg-arn> ...
```

Then update the cluster's default capacity provider strategy to use
spot as the base with on-demand fallback. Spot instances are much
cheaper — about $0.029/hr for m5.large spot vs $0.096/hr on-demand.

Make sure your application handles SIGTERM for graceful shutdown when
spot instances are reclaimed.
