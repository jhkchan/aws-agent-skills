# Baseline (no-skill) response: provisioned-to-ondemand-crossover

This file captures what a generic assistant produces WITHOUT the
dynamodb-capacity-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, crossover math, capacity-
mode recommendation, dollar savings, CONFIRM gate).

---

Your DynamoDB table is provisioned for 5000 RCU and 2000 WCU but you're
only using about 15% of that capacity. Since your traffic is sporadic
(batch processing every 4 hours), you're paying for idle capacity most
of the time.

You should consider switching to on-demand billing mode, which charges
per request instead of per provisioned capacity:

```
aws dynamodb update-table \
  --table-name tbl-provisioned-to-ondemand-crossover \
  --billing-mode PAY_PER_REQUEST
```

This should save you money since you won't be paying for capacity you
don't use.
