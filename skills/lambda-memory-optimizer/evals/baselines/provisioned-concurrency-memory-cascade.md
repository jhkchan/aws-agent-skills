# Baseline (no-skill) response: provisioned-concurrency-memory-cascade

This file captures what a generic assistant produces WITHOUT the
lambda-memory-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, PC idle-bill cascade math,
memory-first right-sizing sequence, latency-SLO preservation check).

---

Your Lambda function has 10 provisioned concurrency at 2048 MB, but the
function is I/O-bound and only uses 240 MB on average. Power Tuning
shows the U-curve minimum is at 512 MB, so you can reduce the memory
without affecting duration.

Reducing from 2048 MB to 512 MB will save on both the per-invocation
compute cost AND the provisioned concurrency idle bill (since PC bills
per GB-second of provisioned capacity).

```
aws lambda update-function-configuration --function-name fn-provisioned-concurrency-memory-cascade --memory-size 512
```

This should cut your Lambda bill by about 75% on the memory dimension
while keeping the same latency.
