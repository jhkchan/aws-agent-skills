# Eval prompt: glue-dpu-insufficient-g1x-oom

Diagnose the AWS Glue job failure for the following job. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Glue job `etl-daily-orders` failed at 03:17 UTC. CloudWatch
Logs show "Container killed by YARN for exceeding memory limits" on 3
executors. The job runs on G.1X with 10 workers. The same job
succeeded last week on a 50 GB dataset; the failed run used a 250 GB
dataset (5x growth).

```text
JobName: glue-dpu-insufficient-g1x-oom
JobRunId: jr_abc123
WorkerType: G.1X
NumberOfWorkers: 10
Timeout: 150 (default 2.5h)
GlueVersion: glue-4.0
Command.Name: glueetl
Role: AWSGlueServiceRole-glue-etl (includes AWSGlueServiceRole)

Last successful run: 2026-08-03 (dataset 50 GB)
Failed run dataset: 250 GB (5x growth)

CloudWatch metrics (failed run):
  - glue.executor.memory.maxUsed Maximum: 9.7 GB (out of 10 GB
    heap per executor on G.1X)
  - 3 executors killed by YARN within a 5-minute window

Script has not changed since the last successful run.
```

G.1X gives 1 executor per worker (10 GB heap). G.2X gives 2 executors
per worker (Spark-optimised), doubling executor parallelism for the
same DPU count. Verify the worker-type sizing and recommend the fix.
