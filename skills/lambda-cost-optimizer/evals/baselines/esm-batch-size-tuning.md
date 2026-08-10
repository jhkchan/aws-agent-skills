# Baseline (no-skill) response: esm-batch-size-tuning

This file captures what a generic assistant produces WITHOUT the
lambda-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, invocation-count math, partial-
batch-failure verification, CONFIRM gate).

---

Your SQS-triggered Lambda is processing 730 million invocations per
month with the default batch size of 10. That's a lot of invocations!
Since you're processing about 1 million messages per hour, you could
reduce the invocation count significantly by increasing the batch size.

If you increase the batch size from 10 to, say, 100 or even 500, each
invocation would process more messages, which means fewer total
invocations. Since your DB upserts are amortized (batch of 50 takes 350
ms instead of 600 ms), this should be more efficient overall.

You can update the event source mapping with:

```
aws lambda update-event-source-mapping --uuid <uuid> --batch-size 500
```

This should reduce your Lambda request costs substantially. Just make
sure your function can handle the larger batch without hitting memory or
timeout limits.
