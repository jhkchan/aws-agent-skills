# Baseline (no-skill) response: capacity-mode-switch

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, burst capacity
diagnosis, on-demand cost-premium caveat, throughput impact estimate).

---

Your DynamoDB table is throttling because of unpredictable traffic
spikes that exceed your provisioned capacity. Your auto-scaling is too
slow to react, and your burst capacity gets exhausted during the
sustained spikes.

You should switch to on-demand capacity mode, which will instantly
allocate capacity for any traffic level without throttling:

```
aws dynamodb update-table --table-name tbl-capacity-mode-switch --billing-mode PAY_PER_REQUEST
```

This will eliminate the throttling, but keep in mind that on-demand
mode costs more per request than provisioned mode.
