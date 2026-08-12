---
name: troubleshoot-glue-job-failure
description: >-
  Slash command for the glue-job-failure-troubleshooter skill.
  Diagnoses AWS Glue job failures: executor YARN OOM (DPU
  insufficient), worker type mismatch (G.025X on Spark, G.1X vs
  G.2X), Data Catalog table not found, S3 source path wrong,
  partitions not loaded (MSCK REPAIR missing), job bookmark corrupted
  (partition-key mismatch), JDBC connection errors (Glue connection /
  security group to RDS/Redshift), DynamicFrame vs RDD performance,
  CloudWatch Logs not enabled, and job timeout (default 2.5h). Emits
  ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA with the failing layer
  and the verifying probe.
skill: glue-job-failure-troubleshooter
family: Analytics
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
---

# /aws:troubleshoot-glue-job-failure

Invoke the `glue-job-failure-troubleshooter` skill to diagnose an AWS
Glue job failure.

## When to use

- A Glue job run transitions to `FAILED` with
  `Container killed by YARN for exceeding memory limits`.
- A Glue job fails with `Table or view not found` or
  `AnalysisException`.
- A Glue job reads 0 records from a Data Catalog table despite S3
  having data (MSCK REPAIR / partition loading issue).
- A Glue job reprocesses all data on every run despite bookmarking
  being enabled (partition-key mismatch).
- A Glue job fails with `Connection timed out` to an RDS / Redshift
  JDBC source (security group or Glue connection issue).
- A Glue job transitions to `TIMEOUT` after the default 2.5 hours.
- CloudWatch Logs for a Glue job run are empty (IAM role missing
  `logs:*` permissions).
- A Spark ETL job on G.025X workers fails with chronic OOM (wrong
  worker type for Spark).

## Invocation

```
/aws:troubleshoot-glue-job-failure <description of the Glue job failure>
```

The skill will:

1. Identify the symptom category (YARN OOM, table not found, S3 path
   wrong, partitions missing, bookmark mismatch, JDBC connection,
   timeout, logs disabled, worker type wrong, Python shell error).
2. Request the mandatory context: JobName, JobRunId, the error message
   from CloudWatch Logs, and the job's WorkerType / NumberOfWorkers.
3. Walk the diagnostic tree in symptom order: DPU/worker type →
   Data Catalog → S3 path → partitions → bookmark → JDBC → timeout →
   logs → Python shell → performance.
4. Apply the G.2X-vs-G.1X worker-type rule before any script-debugging
   advice — this is the most common misdiagnosis.
5. Verify the bookmark state's partition keys match the current script
   before declaring a bookmark issue.
6. Verify both sides of the JDBC security group (Glue connection SG +
   database SG) before declaring a connection issue.
7. Emit the standard VERDICT block with the failing probe and
   remediation command.

## Output shape

```text
TARGET: <job-name (JobRunId)>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <GLUE_ETL_SCRIPT_ERROR | GLUE_DPU_INSUFFICIENT |
        GLUE_PYTHON_SHELL_ERROR | GLUE_DATA_CATALOG_TABLE_NOT_FOUND |
        GLUE_S3_SOURCE_PATH_WRONG | GLUE_PARTITION_NOT_LOADED |
        GLUE_BOOKMARK_CORRUPTED | GLUE_JDBC_CONNECTION_ERROR |
        GLUE_DYNAMIC_FRAME_PERFORMANCE | GLUE_CLOUDWATCH_LOGS_DISABLED |
        GLUE_JOB_TIMEOUT | GLUE_WORKER_TYPE_WRONG | UNKNOWN>
EVIDENCE:
  - <layer>: <failing probe and its output>
REMEDIATION: <specific CLI command + verification command>
```

## Pre-flight

The skill requires the JobName, the JobRunId of the failed run (for
live-account diagnosis), the error message from CloudWatch Logs, and
the job's WorkerType / NumberOfWorkers. If these are not available,
the skill emits `INSUFFICIENT_DATA` with the list of required inputs.

## References

- Skill: `skills/glue-job-failure-troubleshooter/SKILL.md`
- Reference: `skills/glue-job-failure-troubleshooter/references/glue-worker-type-and-dpu-reference.md`
- Reference: `skills/glue-job-failure-troubleshooter/references/glue-bookmark-and-jdbc-reference.md`
- AWS docs: https://docs.aws.amazon.com/glue/latest/dg/
