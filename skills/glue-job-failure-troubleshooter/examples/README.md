# Example usage: glue-job-failure-troubleshooter

A walkthrough showing the skill diagnosing a Glue job failure where
`Container killed by YARN` is caused by insufficient DPU allocation
after dataset growth, demonstrating the symptom-to-layer triage, the
G.1X vs G.2X worker-type decision (G.2X gives 2x executors per
worker), the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
worker-type upgrade remediation.

## Input (user prompt)

> Our daily orders ETL Glue job started failing at 03:17 UTC.
> CloudWatch Logs show "Container killed by YARN for exceeding memory
> limits" on 3 executors. The job runs on G.1X with 10 workers. We've
> been debugging the Spark script for 30 minutes — please help us find
> the actual root cause.

```text
JobName: etl-daily-orders
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

## Skill output

```text
TARGET: etl-daily-orders (JobRunId: jr_abc123)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The job runs on G.1X with 10 workers (10 executors, 10 GB heap
  each). The input dataset grew from 50 GB to 250 GB (5x) since the
  last successful run. CloudWatch Logs show "Container killed by YARN
  for exceeding memory limits" on 3 executors. The same script
  succeeded on 50 GB; the failure is memory sizing, not a script bug.
  G.2X would double the executor count to 20 (2 per worker) and halve
  the per-executor data volume (Step 2a/2b).
LAYER: GLUE_DPU_INSUFFICIENT
EVIDENCE:
  - Symptom: job transitions to FAILED after 23 minutes. CloudWatch
    Logs contain "Container killed by YARN for exceeding memory
    limits. Container [pid=1234] was killed." on 3 executors.
  - Probe: aws glue get-job returns WorkerType=G.1X,
    NumberOfWorkers=10, GlueVersion=glue-4.0.
  - Probe: aws cloudwatch get-metric-statistics on
    glue.executor.memory.maxUsed shows Maximum 9.7 GB (out of 10 GB
    heap) in the 5 minutes before the kill.
  - Passing: the job script has not changed since the last successful
    run; the Data Catalog table exists; partitions are loaded; no JDBC
    connection in play.
REMEDIATION:
  1. Switch the worker type to G.2X (doubles executor parallelism):
     aws glue update-job --job-name etl-daily-orders \
       --job-update '{"WorkerType":"G.2X","NumberOfWorkers":10}'
  2. Optionally increase NumberOfWorkers to 15 if G.2X alone is not
     enough.
  3. Re-run the job and monitor glue.executor.memory.maxUsed; it
     should peak below 5 GB per executor (half the data per executor).
CONFIRM: Before updating the job, emit and await:
  "CONFIRM: About to switch etl-daily-orders from G.1X to G.2X with
   10 workers. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished a DPU sizing problem from a script bug.** A generic
   assistant says "debug the Spark script for memory issues." The skill
   recognises that the script has not changed and the dataset grew 5x
   — the failure is memory sizing, not a code regression.

2. **Identified the G.1X executor-count limit.** The skill knows G.1X
   gives 1 executor per worker (10 GB heap), while G.2X gives 2
   executors per worker (10 GB heap each). The same 10 workers on G.2X
   would produce 20 executors, halving the per-executor data volume.

3. **Ruled out the script with positive evidence.** The skill verifies
   the script has not changed since the last successful run and that
   the Data Catalog table exists with loaded partitions — ruling out
   script errors, catalog issues, and partition issues.

4. **Recommended the worker-type upgrade, not the script fix.** The
   primary remediation is switching from G.1X to G.2X, which doubles
   executor parallelism without any code change. A generic assistant
   suggests optimising the Spark code instead.

## Slash-command invocation

```
/aws:troubleshoot-glue-job-failure
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why etl-daily-orders failed with Container killed by YARN"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: glue-job-failure-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the executor memory and job success:

```bash
# Confirm the job config was updated
aws glue get-job --job-name etl-daily-orders --profile default --output json | \
  jq '.Job.{WorkerType, NumberOfWorkers}'

# Start a new run
aws glue start-job-run --job-name etl-daily-orders --profile default --output json

# Monitor executor memory during the run
aws cloudwatch get-metric-statistics --namespace Glue \
  --metric-name glue.executor.memory.maxUsed \
  --dimensions Name=JobName,Value=etl-daily-orders \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum \
  --profile default --output json
```

Then monitor the job run state for `SUCCEEDED` and confirm that
`glue.executor.memory.maxUsed` Maximum stays below 5 GB (half the
data per executor on G.2X).
