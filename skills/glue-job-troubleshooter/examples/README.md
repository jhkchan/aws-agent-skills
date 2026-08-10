# Example usage: glue-job-troubleshooter

A walkthrough showing the skill diagnosing a Glue job failure that
presents as "No ErrorReason" in the control plane — surfacing the
real Python exception from CloudWatch Logs, ruling out the six other
categories with passing probes, and emitting a one-shot re-run after
re-crawl + script guard.

## Input (user prompt)

> Our nightly-sales-aggregation Glue job failed last night at run
> jr_abc123def456. The console just says "No ErrorReason" and I can't
> tell what happened. Can you diagnose it?

```text
JobName: nightly-sales-aggregation
RunId: jr_abc123def456
Region: us-east-1
GlueVersion: 4.0
WorkerType: G.1X
NumberOfWorkers: 5
Timeout: 60

get-job-run output:
  State: FAILED
  ExecutionTime: 42
  ErrorMessage: "No ErrorReason"

CloudWatch Logs filter (filter-pattern "Traceback"):
  Traceback (most recent call last):
    File "tmp/script.py", line 47, in <module>
      df = df.withColumn('revenue', col('price') * col('qty'))
    AttributeError: 'NoneType' object has no attribute '_jvc'

Source: Glue Data Catalog table analytics_prod.sales_raw.
Last crawler run: 6 hours ago. Table row count in S3: 0.
```

## Skill output

```text
TARGET: nightly-sales-aggregation/jr_abc123def456
VERDICT: ROOT_CAUSE_FOUND
REASON: CloudWatch Logs for the run contain an AttributeError on
  line 47 of the script — from_catalog returned None because the
  source table analytics_prod.sales_raw is empty (0 rows after the
  last crawl). ExecutionTime was 42s. Glue's control plane surfaced
  "No ErrorReason" because the high-level state only captures the
  wrapper failure, not the Python traceback.
CATEGORY: SCRIPT_EXCEPTION
EVIDENCE:
  - State=FAILED, ExecutionTime=42, ErrorMessage="No ErrorReason"
    (high-level state only — confirms the pre-flight gotcha that
    ErrorMessage is often empty even when the script threw)
  - Failing probe:
    aws logs filter-log-events --log-group-name /aws-glue/jobs/output
      --log-stream-name jr_abc123def456 --filter-pattern "Traceback"
    → AttributeError: 'NoneType' object has no attribute '_jvc'
      at line 47 (df.withColumn('revenue', col('price') * col('qty')))
  - Source probe: get-table analytics_prod.sales_raw → row count 0
    after the last crawl 6 hours ago (the upstream ingestion job
    failed silently and wrote nothing)
  - Passing probes:
    - ExecutionTime=42 < Timeout=60 → not TIMEOUT_DPU / TIMEOUT_SKEW
    - No 'Connection refused' / 'VPC' in logs → not JDBC_VPC
    - No 'Container killed by YARN' → not SPARK_OOM
    - get-job-bookmark shows Attempt=5 advancing normally → not
      BOOKMARK_STALL
    - Table exists in catalog (verified with admin role) → not
      CATALOG_MISSING (the read returned None, not EntityNotFound)
    - No 'ResolveChoice' / 'Cannot coerce' → not DYNAMICFRAME_*
REMEDIATION:
  1. Investigate the upstream ingestion job — it should have written
     rows to analytics_prod.sales_raw. The crawler ran 6 hours ago
     on an empty prefix. Do NOT re-run the aggregation job until the
     source has data; re-running produces the same OOM-as-None pattern.
  2. After upstream is healthy, re-crawl to refresh the row count:
     aws glue start-crawler --name sales-raw-crawler
     aws glue get-crawler --name sales-raw-crawler  # wait for State=READY
  3. Add a None guard in the script before line 47:
     if df is None or df.rdd.isEmpty():
         logger.warning("source empty; skipping transform")
         sys.exit(0)  # or return an empty DynamicFrame downstream
     df = df.withColumn("revenue", col("price") * col("qty"))
  4. Re-run with bookmark option=enable to skip previously processed
     partitions (no double-counting if upstream replays data):
     aws glue start-job-run --job-name nightly-sales-aggregation \
       --arguments '{"--job-bookmark-option":"enable"}'
  5. Verify the next run succeeds and the row count is > 0:
     aws glue get-table --database-name analytics_prod \
       --name sales_raw --output json | jq '.Table.StorageDescriptor'
CONFIRM: Before re-running the job, confirm the upstream ingestion
  is healthy. Re-running before the source has data will reproduce
  the same failure.
```

## What the skill caught that a generic assistant misses

1. **CloudWatch Logs as the source of truth, not ErrorMessage.** A
   generic assistant sees "No ErrorReason" and either guesses or asks
   the operator to enable logging. The skill immediately pulls
   `/aws-glue/jobs/output` filtered to `Traceback`, surfaces the
   AttributeError, and pinpoints line 47. Without this step, the
   diagnosis cannot proceed.

2. **Empty-source root cause vs null-reference symptom.** A generic
   assistant says "your DataFrame is None, add a null check." The
   skill traces one level deeper: `from_catalog` returns None because
   the table is empty, the table is empty because the upstream
   ingestion job failed, and the crawler dutifully registered the
   empty prefix. The fix is upstream-first; the script guard is a
   defence-in-depth, not the primary fix.

3. **Passing probes for all six other categories.** A generic
   assistant stops at "Python exception." The skill explicitly rules
   out TIMEOUT_* (ExecutionTime < Timeout), JDBC_VPC (no connection
   error string), SPARK_OOM (no YARN kill), BOOKMARK_STALL (bookmark
   advancing), CATALOG_MISSING (table exists), and DYNAMICFRAME_* (no
   ResolveChoice error). The operator gets a single category, not six
   candidates.

4. **Bookmark-aware re-run.** A generic assistant re-runs the job
   without the `--job-bookmark-option` flag, risking double-counting
   if upstream replays data. The skill sets `enable` explicitly and
   calls out the double-count risk.

5. **CONFIRM gate before re-run.** A generic assistant fires
   `start-job-run` immediately. The skill pauses for operator
   confirmation that upstream ingestion is healthy, preventing a
   repeat of the same failure.

## Slash-command invocation

```
/aws:troubleshoot-glue-job
```

Or via the orchestrator:

```
/aws:pipeline
You: "Glue job failed last night — what went wrong?"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: glue-job-troubleshooter]` and
hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the next run:

```bash
# Confirm the new run succeeds
aws glue get-job-runs --job-name nightly-sales-aggregation \
  --max-results 1 --query 'JobRuns[0].{State:State,ExecTime:ExecutionTime}' \
  --output table

# Confirm the row count is non-zero in the catalog
aws glue get-table --database-name analytics_prod \
  --name sales_raw --output json | \
  jq '.Table.StorageDescriptor.Columns | length'

# Watch the next run's logs live
aws logs tail /aws-glue/jobs/output \
  --log-stream-name-prefix jr_ \
  --follow
```

If the next run fails again with the same AttributeError, the upstream
ingestion is still broken — route to the ingestion job's diagnosis
before re-trying the aggregation.

## Fleet-wide extension

For an Organizations fleet of N failing Glue jobs:

1. Pull `get-job-runs` across all jobs with `State=FAILED` in the last
   24 hours.
2. Group by ErrorMessage signature (Traceback / VPC / EntityNotFound /
   YARN kill / No ErrorReason).
3. For each group, run the category-specific probe in parallel.
4. Slice into batches of at most 3 jobs; emit per-job REMEDIATION and
   a single CONFIRM per batch; verify each batch before proceeding.
5. For the "No ErrorReason" group, the CloudWatch Logs pull is the
   gating probe — never emit a verdict without it.
