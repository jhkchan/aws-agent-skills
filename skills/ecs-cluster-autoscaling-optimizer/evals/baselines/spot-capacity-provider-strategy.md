# Baseline (no-skill) response: spot-capacity-provider-strategy

This file captures what a generic assistant produces WITHOUT the
ecs-cluster-autoscaling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, base+weight strategy,
spot discount math, CONFIRM gate, capacity provider creation commands).

---

Since your services are all stateless REST APIs with no long-lived
connections, you could save money by using spot instances. Spot
instances are much cheaper than on-demand (usually about 70% less).

You can create a spot capacity provider and add it to your cluster:

```
aws ecs create-capacity-provider --name spot-cp --auto-scaling-group-provider autoScalingGroupArn=<your-spot-asg>
```

Then update your services to use the spot capacity provider. Since your
tasks complete in under 500 ms, spot interruption shouldn't cause
problems.

This should reduce your monthly EC2 costs significantly.
