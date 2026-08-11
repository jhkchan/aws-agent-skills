# End-to-end usage scenario: dms-task-troubleshooter

A walkthrough showing the skill diagnosing a DMS CDC task failure
where the PostgreSQL source has `wal_level=replica`, contrasted with a
memory-pressure case where the replication instance is the bottleneck.

## Input (user prompt)

> My DMS task TASK001 (postgres -> postgres, full-load-and-cdc) failed
> immediately on start. The logs say "logical decoding requires
> wal_level >= logical." The source is RDS PostgreSQL 15.

```json
{
  "Task": "arn:aws:dms:us-east-1:111111111111:task:TASK001",
  "Source": "postgres (RDS PostgreSQL 15)",
  "Target": "postgres (Aurora PostgreSQL 15)",
  "MigrationType": "full-load-and-cdc",
  "TaskStatus": "failed",
  "TaskLogs": {"ERROR": "logical decoding requires wal_level >= logical"},
  "SourceWalLevel": "replica"
}
```

## Skill output

```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK001 (source: postgres,
        target: postgres, instance: dms.r5.large)
VERDICT: ROOT_CAUSE_FOUND
REASON: The PostgreSQL source has wal_level=replica, which does not
  support logical replication. Task started in CDC mode and failed
  immediately with "logical decoding requires wal_level >= logical."
LAYER: SOURCE_BINARY_LOGGING
EVIDENCE:
  - Symptom: task status failed within 10s of start.
  - Probe: task logs: "logical decoding requires wal_level >= logical."
  - Probe (source): select setting from pg_settings where
    name='wal_level'; returns: replica.
  - Passing: source SG allows DMS SG on 5432; pglogical installed;
    DMS user has REPLICATION attribute.
REMEDIATION:
  1. aws rds modify-db-parameter-group --db-parameter-group-name
     <pg-name> --parameters ParameterName=wal_level,
     ApplyMethod=pending-reboot,ParameterValue=logical
  2. aws rds reboot-db-instance --db-instance-identifier <pg-id>
  3. Verify wal_level=logical, then: aws dms start-replication-task
     --replication-task-arn <task-arn> --start-replication-task-type
     start-replication
CONFIRM: "About to set wal_level=logical on <pg-id> and reboot.
  Brief connection drop. Proceed? (yes/no)"
```

## Contrast — MEMORY_PRESSURE case (3 tasks on dms.r5.large)

If the operator reports "all 3 DMS tasks are slow at the same time,"
the diagnosis shifts from a per-task source issue to an instance-
level capacity issue:

```text
TARGET: instance rep-inst-001 (dms.r5.large) running TASK004,
        TASK005, TASK006
VERDICT: ROOT_CAUSE_FOUND
REASON: dms.r5.large (8GB RAM) running 3 CDC tasks. FreeableMemory
  dropped to 200MB, SwapUsage climbed to 2GB, causing thrashing and
  CDC disk spill.
LAYER: MEMORY_PRESSURE
EVIDENCE:
  - Symptom: CDCLatencyTarget climbing on all 3 tasks.
  - Probe: CloudWatch FreeableMemory: avg 200MB, min 50MB.
  - Probe: SwapUsage: avg 2GB, climbing. CDCChangesDiskSource non-zero.
  - Passing: source binlog retention sufficient; SG rules OK; target
    constraints OK.
REMEDIATION:
  1. aws dms modify-replication-instance --replication-instance-arn
     <inst-arn> --replication-instance-class dms.r5.xlarge
     --apply-immediately
  2. Or move 1-2 tasks to a separate instance to reduce contention.
  3. Verify: FreeableMemory > 2GB; SwapUsage drops to zero.
CONFIRM: "About to upgrade <inst-id> dms.r5.large -> dms.r5.xlarge.
  Brief task interruption. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Pulls task logs before diagnosing.** A generic assistant reads
   `LastFailureMessage` ("Task was suspended") and guesses. The skill
   runs `filter-log-events` and finds the engine-specific error
   ("logical decoding requires wal_level >= logical").

2. **Verifies the source parameter.** A generic assistant says "enable
   logical replication." The skill queries `pg_settings` to confirm
   `wal_level=replica` and emits the exact RDS parameter group +
   reboot command.

3. **Distinguishes source vs target latency.** A generic assistant
   says "latency is high." The skill separates `CDCLatencySource`
   (source can't keep up) from `CDCLatencyTarget` (target can't keep
   up) and routes to the correct layer.

4. **Checks instance capacity before per-task metrics.** A generic
   assistant diagnoses each task individually. The skill checks
   instance-level `FreeableMemory` and `SwapUsage` first when multiple
   tasks degrade simultaneously.

5. **RDS MySQL binlog_retention default.** A generic assistant misses
   the `binlog_retention_hours=0` default on RDS MySQL. The skill
   checks this as the #1 silent CDC stall cause.

6. **FK constraint load order.** A generic assistant says "remove the
   constraint." The skill says "disable FK checks during load
   (`session_replication_role=replica`) or order parent before child
   tables" — the correct fix that preserves the schema.

7. **Logging level awareness.** A generic assistant reads empty logs
   and gives up. The skill detects `Logging=ESSENTIAL` (default),
   tells the operator to set `DETAILED`, and verifies the
   `dms-cloudwatch-logs-role` IAM role.

## Slash-command invocation

```
/aws:troubleshoot-dms-task
```

Or via the orchestrator:

```
/aws:pipeline
You: "DMS task TASK001 is failing"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: dms-task-troubleshooter]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "DMS task TASK001 failed with wal_level error"
# [Phase: Troubleshoot | Skills routed: dms-task-troubleshooter]
```

## Live-account follow-up (optional, requires AWS CLI)

After diagnosis:

```bash
# Pull task logs
aws logs filter-log-events \
  --log-group-name dms-task-TASK001 \
  --filter-pattern "ERROR" \
  --start-time $(date -u -v-1H +%s)000 \
  --profile default

# Check source wal_level
aws rds describe-db-parameters \
  --db-parameter-group-name <pg-name> \
  --query 'Parameters[?ParameterName==`wal_level`]' \
  --profile default

# Apply the fix
aws rds modify-db-parameter-group \
  --db-parameter-group-name <pg-name> \
  --parameters ParameterName=wal_level,ParameterValue=logical,ApplyMethod=pending-reboot \
  --profile default

aws rds reboot-db-instance --db-instance-identifier <pg-id> \
  --profile default

# After reboot, restart the DMS task
aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:us-east-1:111111111111:task:TASK001 \
  --start-replication-task-type start-replication \
  --profile default

# Monitor CDC latency after restart
aws cloudwatch get-metric-statistics --namespace AWS/DMS \
  --metric-name CDCLatencySource \
  --dimensions Name=ReplicationTaskIdentifier,Value=TASK001 \
  --start-time $(date -u -v-30M +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --profile default
```
