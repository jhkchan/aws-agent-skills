# Baseline (no-skill) response: binpack-placement-efficiency

This file captures what a generic assistant produces WITHOUT the
ecs-cluster-autoscaling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, binpack+AZ-spread
pairing, host reduction math, CONFIRM gate).

---

Your cluster is wasting a lot of resources. Each worker task only uses
1 vCPU and 4 GB, but your m5.2xlarge instances have 8 vCPUs and 32 GB.
With spread-by-host placement, you're only using 12.5% of each host's
CPU and 12.5% of its memory.

You should switch to a binpack placement strategy, which will pack
multiple tasks onto each host. This way you could fit 8 tasks per host
instead of 1.

To update the placement strategy:

```
aws ecs update-service --cluster ecs-binpack-placement-efficiency --service worker-service --placement-strategy type=binpack,field=memory
```

This should let you reduce from 15 instances to about 2-3, which would
save a lot of money.
