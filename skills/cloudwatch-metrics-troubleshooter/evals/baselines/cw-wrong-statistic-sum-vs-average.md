# Baseline (no-skill) response: cw-wrong-statistic-sum-vs-average

This file captures what a generic assistant produces WITHOUT the
cloudwatch-metrics-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, category-aware
walk, specific remediation).

---

Your metric values look too high because you're using the wrong
statistic. You're querying `Sum`, which adds up all the latency values
across every request in the minute. With about 100 requests per
minute, the Sum will be roughly 100x the per-request average.

Switch to `Average` instead of `Sum`. That will give you the mean
latency per request, which is what you actually want.

If you want throughput instead, use `SampleCount`. If you want the
total time spent, keep `Sum`.
