# Baseline (no-skill) response: burst-capacity-exhaustion-spiky

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your DynamoDB table is throttling intermittently. Looking at the numbers,
your average write capacity (4,000 WCU) is below your provisioned
capacity (5,000 WCU), so it seems like you have enough capacity. But
since you are still throttling, there might be something else going on.

The intermittent pattern suggests the traffic is bursty. DynamoDB has a
burst capacity feature that allows short bursts above the provisioned
limit, but it runs out after a few minutes. Once the burst is exhausted,
you get throttled.

You should raise your `WriteCapacityUnits` a bit higher, maybe to 7,000
or 8,000. Or you could smooth out your batch writes so they are more
evenly distributed over time instead of all at once every 2 minutes.

You can also switch to on-demand billing:

```bash
aws dynamodb update-table --table-name events-ingest \
  --billing-mode PAY_PER_REQUEST
```
