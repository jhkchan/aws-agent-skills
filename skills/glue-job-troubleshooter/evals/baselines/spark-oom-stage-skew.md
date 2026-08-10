# Baseline (no-skill) response: spark-oom-stage-skew

This file captures what a generic assistant produces WITHOUT the
glue-job-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT + CATEGORY, skew-ratio
evidence, salting remediation, anti-pattern: don't raise DPU for skew).

---

Your Glue job ran out of memory. The error "Container killed by YARN
for exceeding memory limits" means an executor OOMed. Try increasing
the NumberOfWorkers or switching from G.1X to G.2X workers, which have
more memory. You can also try lowering `spark.sql.shuffle.partitions`
or adjusting executor memory.

If the issue persists, consider re-partitioning your data.
