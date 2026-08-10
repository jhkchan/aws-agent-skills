---
description: Diagnoses AWS Glue ETL job failures through a seven-category diagnostic tree — Python script exceptions, job timeout (DPU capacity, long-running transforms), JDBC connection errors (VPC security group, subnet, NACL), bookmark errors (not advancing, reprocessing data, layout drift), Data Catalog errors (table / partition not found, stale crawler), Spark errors (executor OOM, stage failures, data skew), and DynamicFrame errors (schema mismatch, type coercion). Reads get-job-run ErrorMessage and ExecutionTime, CloudWatch logs (/aws-glue/jobs/), Spark UI exported to S3, and get-job-bookmark state. Emits ROOT_CAUSE_FOUND with the failing probe and positive evidence, NEED_MORE_INFO when a probe requires operator input, or ESCALATE for AWS-side incidents.
nl_triggers:
  - "Glue job failed"
  - "Glue job timeout"
  - "Glue bookmark not advancing"
  - "Glue reprocessing data"
  - "Glue JDBC connection error"
  - "Glue Spark OOM"
  - "Glue stage failure"
  - "Glue table not found"
  - "Glue partition not found"
  - "DynamicFrame schema mismatch"
  - "DynamicFrame ResolveChoice error"
  - "Glue DPU capacity"
  - "Glue job RUNNING too long"
  - "Glue version 2.0 vs 3.0 vs 4.0"
  - "diagnose Glue ETL failure"
  - "Spark UI Glue"
  - "Glue job stuck"
  - "Glue Python shell job error"
  - "Glue crawler did not register partitions"
  - "Glue ENI connection error"
routes_to: glue-job-troubleshooter
---

# /aws:troubleshoot-glue-job

Activate the `glue-job-troubleshooter` skill and diagnose an AWS Glue
ETL job failure through the seven-category diagnostic tree.

## What it does

Reads a job-run metadata record (`get-job-run` — state, ErrorMessage,
ExecutionTime), the CloudWatch Logs excerpt for the failing run, the
Spark UI event log exported to S3, and the bookmark state
(`get-job-bookmark`), then walks the seven-category diagnostic tree to
a root cause with positive evidence:

1. **Pre-flight** — data sufficiency gate. If CloudWatch Logs missing,
   Spark UI not enabled, or run still RUNNING, emit NEED_MORE_INFO with
   the specific data gap.
2. **Symptom entry** — map the ErrorMessage / ExecutionTime signature
   to a category:
   - Traceback → Step 1 (SCRIPT_EXCEPTION).
   - `ExecutionTime == Timeout`, no traceback → Step 2 (TIMEOUT_*).
   - `Connection refused` / `VPC` → Step 3 (JDBC_VPC).
   - `EntityNotFoundException` → Step 5 (CATALOG_*).
   - `OutOfMemoryError` / `YARN` → Step 6 (SPARK_OOM).
   - `ResolveChoice` / `Cannot coerce` → Step 7 (DYNAMICFRAME_*).
3. **Category-specific probe** — for each candidate category, run the
   probe (CloudWatch filter, security-group inspection, Spark UI
   inspection, bookmark inspection, Data Catalog lookup).
4. **Verdict** — ROOT_CAUSE_FOUND (failing probe confirmed the cause),
   NEED_MORE_INFO (probe requires operator input), or ESCALATE
   (AWS-side Glue incident via AWS Health).

Emits a deterministic diagnostic block per target:

```text
TARGET: <job-name>/<run-id>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failing category and probe>
CATEGORY: SCRIPT_EXCEPTION | TIMEOUT_DPU | TIMEOUT_SKEW |
          JDBC_VPC | JDBC_CRED | BOOKMARK_STALL | CATALOG_MISSING |
          CATALOG_PARTITION | SPARK_OOM | SPARK_STAGE |
          DYNAMICFRAME_SCHEMA | DYNAMICFRAME_TYPE | UNKNOWN
EVIDENCE:
  - <observed symptom>
  - <failing probe — command and confirming output>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command>
```

## When to invoke

Paste a job-run record, ErrorMessage, or CloudWatch excerpt and ask
any of:

- "Glue job failed last night — what went wrong?"
- "Glue job is RUNNING past its SLA"
- "job is reprocessing data the bookmark should skip"
- "Glue JDBC connection times out to RDS"
- "Spark executor OOM in stage 7"
- "table not found in Data Catalog"
- "ResolveChoice conflict on DynamicFrame"
- "diagnose this Glue failure"

A bare `JobName` + any failure verb ("job failed", "job timeout",
"job stuck") also routes here via the orchestrator.

## Inputs

- **Job-run metadata:** JobName, RunId, State, ErrorMessage,
  ExecutionTime, Timeout, GlueVersion, WorkerType, NumberOfWorkers.
- **CloudWatch Logs excerpt:** the failing run's log stream from
  `/aws-glue/jobs/output` filtered to `ERROR` / `Traceback`.
- **Spark UI:** event log downloaded from
  `--spark-event-logs-path` S3 prefix (required for skew / OOM / stage
  failure categories).
- **Bookmark state:** `get-job-bookmark` for the run (required for
  reprocessing complaints).
- **Network config:** Glue connection (subnet, SG), database SG,
  subnet route table (required for JDBC failures).
- **Data Catalog:** database / table / partition inventory (required
  for table-not-found and partition-not-found categories).

## Outputs

- One diagnostic block per job run.
- CATEGORY from the enumerated set.
- Evidence section with the failing probe AND passing probes (categories
  ruled out) — never a verdict without positive evidence.
- Specific remediation: script fix, security-group rule, bookmark reset,
  crawler run, Spark conf change, or AWS Support escalation.
- A CONFIRM gate before any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Troubleshoot specialist for Glue ETL jobs).
- `/aws:audit-glue-crawler-job` for crawler configuration posture audits
  (this skill diagnoses job runs, not crawler health).
- `/aws:troubleshoot-rds-connectivity` when the Glue failure is downstream
  RDS-side (Glue's JDBC layer is fine; the DB itself is unreachable).
- `/aws:troubleshoot-vpc-connectivity` for VPC peering / TGW routing
  problems blocking the Glue ENI to the database.
