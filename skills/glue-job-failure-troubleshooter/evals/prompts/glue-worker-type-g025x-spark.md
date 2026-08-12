# Eval prompt: glue-worker-type-g025x-spark

Diagnose the AWS Glue job failure for the following job. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Glue job `etl-spark-g025x` fails immediately with "Container
killed by YARN for exceeding memory limits" on every executor. The job
was recently "cost-optimised" by switching from G.1X to G.025X.

```text
JobName: glue-worker-type-g025x-spark
JobRunId: jr_mno345
WorkerType: G.025X
NumberOfWorkers: 10
Timeout: 60
GlueVersion: glue-4.0
Command.Name: glueetl (Spark ETL job)

The script uses glue_context.create_dynamic_frame.from_catalog
(Spark-based DynamicFrame API).

CloudWatch Logs:
  - "Container killed by YARN for exceeding memory limits"
    on all executors within 2 minutes of job start
  - The job never progresses past the initial data load

G.025X provides 0.0625 DPU per worker (1 GB memory, no Spark
executor). G.025X is designed for Python shell jobs only.
```

G.025X (micro) is for Python shell jobs only — it cannot run Spark.
Any Spark job on G.025X produces chronic OOM. Verify the worker-type
selection and recommend the fix.
