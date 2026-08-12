# Eval prompt: glue-bookmark-partition-key-mismatch

Diagnose the AWS Glue job issue for the following job. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Glue job `etl-hourly-events` succeeds but reprocesses all
data on every run despite `--job-bookmark-option=job-bookmark-enable`.
CloudWatch Logs show "Processing 2,400,000 records" on every run; the
source table grows by ~100,000 records per hour, so a bookmarked run
should process ~100,000, not 2.4M.

```text
JobName: glue-bookmark-partition-key-mismatch
JobRunId: jr_def456
WorkerType: G.2X
NumberOfWorkers: 10
Timeout: 60
GlueVersion: glue-4.0

--job-bookmark-option: job-bookmark-enable (confirmed via
  get-job-run Arguments)

Script history:
  - 2026-08-01: partition_keys=["event_date"]
  - 2026-08-05 (3 days ago): partition_keys changed to
    ["event_date","event_hour"]

get-job-bookmark output:
  - bookmark state references only "event_date" (old schema)

Data Catalog table exists; partitions loaded; no JDBC connection;
worker type is G.2X (not a memory issue).
```

Glue bookmark state tracks the last-processed partition value. If the
`partition_keys` argument in `create_dynamic_frame.from_catalog`
changes, the bookmark cannot compare and the job reprocesses
everything. Verify the bookmark state mismatch and recommend the fix.
