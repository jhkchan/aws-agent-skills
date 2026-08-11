# Baseline (no-skill) response: memory-tuning-for-cold-start

This file captures what a generic assistant produces WITHOUT the
lambda-cold-start-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, Power Tuning latency
citation, latency impact estimate, CONFIRM gate).

---

Your Python function is running at 128 MB which is very low for a
CPU-bound workload. The Power Tuning results show that increasing to
1024 MB would dramatically reduce both init time and handler duration.

Since Lambda gives you more CPU when you increase memory, your
CPU-bound regex and computation will run much faster. At 1024 MB
you'd get about 0.58 vCPU instead of the 0.07 vCPU you have now at
128 MB.

You can increase the memory with:

```
aws lambda update-function-configuration --function-name fn-memory-tuning-for-cold-start --memory-size 1024
```

This will increase your per-invocation cost but the latency
improvement should be significant.
