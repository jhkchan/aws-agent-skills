# Baseline (no-skill) response: msk-serverless-break-even

This file captures what a generic assistant produces WITHOUT the
msk-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, Serverless per-partition-hour
break-even math, 50 MB/s threshold rule, anti-pattern: don't recommend
Serverless for high-throughput steady workloads).

---

Your MSK cluster has pretty low throughput at 10 MB/s and goes idle
overnight. You might want to look at MSK Serverless, which charges based
on usage instead of fixed broker cost. It could be cheaper for your
workload. Check the Serverless pricing page to compare.
