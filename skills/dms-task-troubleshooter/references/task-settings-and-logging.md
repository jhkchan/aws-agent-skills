# Task Settings and Logging Reference

Load this reference when diagnosing DMS task settings issues, especially
missing CloudWatch Logs, insufficient parallelism, or LOB truncation.

## Logging levels

| `Logging.EnableLogIO` | `Logging.LogLevel` | What you get |
|---|---|---|
| `true` (default) | `LOGGER_MIN_SEVERITY_LOG_LEVEL_ERROR` (`ESSENTIAL`) | Minimal logging — only errors. Often insufficient for diagnosis. |
| `true` | `LOGGER_MIN_SEVERITY_LOG_LEVEL_DEBUG` (`DETAILED`) | Full diagnostic logging — SQL statements, per-table progress, CDC events. REQUIRED for troubleshooting. |

**To enable DETAILED logging:**

```bash
aws dms modify-replication-task \
  --replication-task-arn <task-arn> \
  --replication-task-identifier <task-id> \
  --task-data '{"Logging": {"EnableLogging": true, "LogComponents": [{"Id": "TRANSFORMATION", "Severity": "LOGGER_SEVERITY_DEFAULT"}, {"Id": "SOURCE_UNLOAD", "Severity": "LOGGER_SEVERITY_DEFAULT"}, {"Id": "TARGET_LOAD", "Severity": "LOGGER_SEVERITY_DEFAULT"}, {"Id": "SOURCE_CAPTURE", "Severity": "LOGGER_SEVERITY_DEFAULT"}, {"Id": "TARGET_APPLY", "Severity": "LOGGER_SEVERITY_DEFAULT"}]}}'
```

Or via the console: Task > Settings > Logging > Enable DETAILED.

**The CloudWatch log group** for a DMS task is `dms-task-<task-id>`.
Verify it exists:

```bash
aws logs describe-log-groups --log-group-name-prefix dms-task-<task-id>
```

If the log group is missing, the `dms-cloudwatch-logs-role` IAM role
may be absent or misconfigured. Check:

```bash
aws iam get-role --role-name dms-cloudwatch-logs-role
# Trust policy must include "dms.amazonaws.com"
# Permissions must include logs:CreateLogGroup, logs:CreateLogStream,
# logs:PutLogEvents
```

## Key task settings for diagnosis

### `TargetTablePrepMode`

| Value | Behavior | When to use |
|---|---|---|
| `DO_NOTHING` (default) | DMS does not modify the target table. Data is inserted into the existing schema. | Use when the target schema is pre-created with correct types/constraints. |
| `DROP_AND_CREATE` | DMS drops and recreates target tables (loses constraints, indexes). | Use for initial load only — FK constraints are dropped. |
| `TRUNCATE_BEFORE_LOAD` | DMS truncates target tables before loading (keeps schema/constraints). | Use for reloads — FK constraints remain active. |

For FK constraint violations during full load, use `TRUNCATE_BEFORE_LOAD`
with FK checks disabled on the target session.

### `MaxFileSize`

Default 102400 KB (100MB). Controls the maximum size of the files DMS
writes to disk when spilling. Reducing this can lower per-task memory
footprint on memory-constrained instances. Increasing it can improve
throughput on large instances.

### `LobMaxSize` and LOB modes

| Mode | Setting | Behavior |
|---|---|---|
| `LIMITED` (default) | `LobMaxSize=32` (32KB) | LOBs under 32KB are inlined; larger LOBs are truncated or cause failures. |
| `FULL` | `LobMaxSize=0` (unlimited) | All LOBs migrated regardless of size. Slower — each LOB is a separate round-trip. |
| `INLINE` | `LobMaxSize=<N>` + `InlineLob` | LOBs under N are inlined; larger LOBs use full mode. |

For LOB-heavy migrations, set `LobMaxSize=0` for correctness, accepting
slower throughput.

### Parallelism settings

| Setting | Default | Effect |
|---|---|---|
| `ParallelLoadThreads` | 0 (disabled) | Number of threads for full-load parallelism per table. Increase for faster full loads. |
| `ParallelLoadBufferSize` | 0 | Buffer size for parallel load threads. |
| `ParallelApplyThreads` | 0 (disabled) | Number of threads for CDC apply parallelism. Increase for faster CDC apply when target is the bottleneck (high CDCLatencyTarget). |
| `ParallelApplyBufferSize` | 100 | Buffer size for parallel apply threads. |

For high `CDCLatencyTarget`, increase `ParallelApplyThreads` to 4 or 8
(matching the target vCPU count). Monitor target write latency.

### CDC-specific settings

| Setting | Default | Effect |
|---|---|---|
| `CDCStartPosition` | n/a | Start CDC from a specific binlog/WAL position. Use for point-in-time recovery. |
| `CDCStopPosition` | n/a | Stop CDC at a specific position. Use for controlled cutover. |
| `FailTaskWhenCleanTaskResourceFailure` | false | If true, task fails when it cannot clean up resources (slots, temp files). |

## Validation settings

```json
{
  "Validation": {
    "EnableValidation": true,
    "ValidationMode": "ROW_LEVEL",
    "ValidationTableLoadStartTime": "2024-01-01T00:00:00Z"
  }
}
```

Validation compares source and target data after migration:

- **Row-level validation:** Compares row counts per table.
- **Full validation:** Compares actual column values (checksum).

Validation failures appear in the `awsdms_validation` schema on the
target database (tables `awsdms_validation.vpc_*`) and in task logs.

## IAM roles reference

| Role | Trust policy | Permissions | Purpose |
|---|---|---|---|
| `dms-vpc-role` | `dms.amazonaws.com` | `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`, `ec2:AttachNetworkInterface`, `ec2:DetachNetworkInterface` | DMS creates ENIs in the customer VPC to reach source/target endpoints. |
| `dms-cloudwatch-logs-role` | `dms.amazonaws.com` | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams` | DMS writes task logs to CloudWatch Logs. |

If either role is missing or misconfigured:
- `dms-vpc-role`: `test-connection` fails with network errors; the task
  cannot reach the source or target endpoint.
- `dms-cloudwatch-logs-role`: task logs are absent from CloudWatch Logs;
  diagnosis is impossible.

Recreate via the AWS console (DMS > Replication instances > create —
prompts to create the roles) or via IAM.
