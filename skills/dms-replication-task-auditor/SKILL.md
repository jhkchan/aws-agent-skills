---
name: dms-replication-task-auditor
description: Audits AWS DMS replication tasks for SSL/TLS gaps on source and target endpoints, missing CDC and task logging, replication instance exposure (public accessibility, single-AZ, missing KMS), endpoint encryption configuration, and task settings integrity (validation, recovery checkpointing, deletion protection). Emits a deterministic verdict (NO_TLS | NO_LOGGING | CONFIG_GAP | OK) per task with enumerated findings and specific CLI remediation. Use when reviewing DMS replication tasks, checking migration endpoint SSL/TLS, validating CDC logging posture, auditing replication instance configuration, or hardening database migration security before production cutover.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline task/endpoint config classification. Live-account audits use aws dms describe-replication-tasks, describe-endpoints, and describe-replication-instances (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Migration
  verdict_shape: NO_TLS | NO_LOGGING | CONFIG_GAP | OK
  when_to_use: Reviewing a DMS replication task before production cutover, checking endpoint SSL/TLS configuration, validating CDC or task logging posture, auditing replication instance exposure, verifying endpoint encryption, or hardening database migration security.
  activation_triggers: audit this DMS replication task, check DMS endpoint SSL, is my DMS task encrypted, DMS CDC logging, replication instance public, hardening DMS migration, DMS task settings
  invocation_schema: 'Input: either (a) a DMS replication task configuration (task settings + endpoint configs + replication instance metadata), OR (b) a task ARN for live-account audit. Output: deterministic TASK/VERDICT/REASON/FINDINGS/ REMEDIATION block per task, where VERDICT in {NO_TLS, NO_LOGGING, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: DMS, Database Migration Service, replication task, SSL/TLS, CDC, change data capture, replication instance, endpoint encryption, task settings, CloudWatch logging, SslMode, verify-full, PubliclyAccessible, migration security, data-in-transit, deletion protection, task validation
  tags: dms, migration, security, ssl-tls, cdc, replication, endpoint, audit
---

# DMS Replication Task Auditor

## Mindset

**One-line takeaway:** the verdict is always the **first** failing dimension
in priority order — and three DMS-specific traps are in a class of their own:
`SslMode: none` (plaintext data pipe), `EnableLogging: false` (silent task
failures), and `PubliclyAccessible: true` (internet-exposed credential store).

DMS sits between a source and target database — it IS the data pipe for a
migration. Three things make it dangerous when misconfigured:

- **`SslMode: none` means plaintext replication traffic.** DMS reads every
  row from the source and writes it to the target. Without TLS, every column
  value — credentials, PII, financial records — traverses the network in
  plaintext. This is not an add-on — it is the pipe itself.
- **`EnableLogging: false` makes task failures invisible.** DMS emits
  CloudWatch metrics regardless (CDC latency, throughput), but metrics show
  a healthy task while logs reveal FK constraint failures, data truncation,
  and connection drops. An operator monitoring metrics alone sees green
  while data is silently lost.
- **`PubliclyAccessible: true` exposes the replication instance.** The
  instance stores database credentials for both source and target. A public
  instance is an internet-reachable credential store.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Any endpoint `SslMode: none` or missing | **NO_TLS** | Step 1 |
| `TaskSettings` logging disabled or absent | **NO_LOGGING** | Step 2 |
| Endpoint `SslMode: require` (no cert verification) | CONFIG_GAP | Step 1 |
| Instance `PubliclyAccessible: true` | CONFIG_GAP | Step 3 |
| Instance `MultiAZ: false` on CDC/full-load-and-cdc task | CONFIG_GAP | Step 3 |
| Endpoint missing `KmsKeyId` | CONFIG_GAP | Step 4 |
| Task missing validation settings | CONFIG_GAP | Step 4 |
| All dimensions pass | **OK** | Step 5 |

**Verdict priority (first match wins):** NO_TLS > NO_LOGGING > CONFIG_GAP > OK.
All findings are still enumerated regardless of verdict — the verdict
identifies the worst dimension, not the only one.

## Pre-flight: task metadata gate

Before evaluating settings, classify the task itself. Several attributes
short-circuit or redirect the audit.

**Live-account pre-flight (skip for offline config audit):**
1. Verify the caller can run `dms:DescribeReplicationTasks` and
   `dms:DescribeEndpoints` — read-only auditor roles should have these.
   Remediation requires `dms:ModifyReplicationInstance` and
   `dms:ModifyEndpoint` — surface this BEFORE the operator approves.
2. Confirm `TaskSettings` is a **serialized JSON string** in the API response,
   not a parsed object. Parse with `json.loads()` before evaluating
   `EnableLogging`, `LogLevel`, `ValidationSettings`, etc.
3. Snapshot both endpoint configs (`describe-endpoints`) BEFORE any
   modification — endpoint changes are not versioned and there is no undo.
4. **Pagination:** `describe-endpoints` and `describe-replication-tasks`
   return at most 100 records per page. Use `--marker` from the prior
   response to page through. Iterating only the first page silently misses
   the long tail of tasks and endpoints.

| Attribute | Effect on audit |
|---|---|
| `MigrationType: full-load` | Full-load only — CDC position management is N/A. Logging still required. |
| `MigrationType: cdc` | CDC only — CDC position continuity and logging are critical. |
| `MigrationType: full-load-and-cdc` | Both phases — highest risk (CDC inherits all full-load issues). |
| `Status: stopped/failed` | Note as operational risk but still audit config — a stopped task with bad config will fail on restart. |
| Target `EngineName: s3` | S3 target has no `SslMode` — HTTPS is enforced by the SDK. Check SSE in `S3Settings`. Do NOT flag missing SslMode. |

If the task or endpoint config is malformed (invalid JSON, missing required
fields), output:

```text
TASK: <task-id>
VERDICT: ERROR
REASON: Task or endpoint configuration is not valid — cannot classify.
REMEDIATION: Re-fetch with aws dms describe-replication-tasks --filters Name=replication-task-id,Values=<id> --output json.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious DMS behaviors that change classification

Each of these will produce a wrong verdict if ignored:

- **Missing `SslMode` defaults to `none`.** The DMS API does not require
  `SslMode` in the endpoint configuration. When absent, DMS connects without
  SSL — plaintext. The console may display this as blank rather than "none",
  making it easy to overlook. Treat a missing `SslMode` identically to
  `SslMode: none`.

- **`SslMode: require` encrypts but does NOT verify certificates.** The
  connection uses TLS but does not check the server certificate against a
  trusted CA, leaving it vulnerable to man-in-the-middle (MITM) attacks.
  Only `verify-ca` (validates certificate chain) and `verify-full` (validates
  certificate + hostname) provide real TLS security. `require` is a
  CONFIG_GAP — encryption present, certificate trust absent.

- **`KmsKeyId` on a DMS endpoint encrypts stored config, NOT transit data.**
  The KMS key encrypts the endpoint configuration stored by DMS (including
  connection credentials). It does NOT encrypt data flowing between source
  and target. Data-in-transit is controlled solely by `SslMode`. These are
  independent dimensions — do not conflate a KMS-encrypted endpoint with a
  TLS-encrypted connection.

- **S3 target endpoints have no `SslMode`.** S3 targets use HTTPS by default
  (enforced by the AWS SDK). Do NOT flag an S3 target for missing `SslMode` —
  it is expected. The source endpoint is still evaluated normally.

- **DMS CloudWatch metrics are always on; Logs are opt-in.** Even with
  `EnableLogging: false`, DMS emits CloudWatch metrics (CDC latency, task
  throughput, CPU utilization). An operator watching the DMS console sees a
  green task while the logs would reveal foreign-key constraint failures,
  data truncation, and connection drops. Metrics lie; logs tell the truth.

- **`EnableLogging` is nested inside the `TaskSettings` JSON string.** The
  boolean lives at `TaskSettings.Logging.EnableLogging` (or top-level
  `EnableLogging` in older format). A common audit error is checking the
  task's top-level `Status` field — that reflects running/stopped state, not
  log emission.

- **Single-AZ replication instances lose CDC position on instance failure.**
  Without Multi-AZ, a replication instance failure requires re-establishing
  CDC from the last checkpoint in the recovery table. If the source has
  rotated binlogs/transaction logs past the checkpoint, CDC cannot resume —
  a full reload is required. Multi-AZ maintains a hot standby with current
  CDC position.

- **`PubliclyAccessible: true` is the default in some IaC templates.**
  CloudFormation and CDK templates for DMS replication instances may default
  to `PubliclyAccessible: true` when VPC settings are specified without
  explicitly setting it to false. The instance then receives a public IP.
  Always verify this flag — the instance stores database credentials.

- **`TaskSettings` is a JSON string, not a structured object in the API.**
  `describe-replication-tasks` returns `ReplicationTaskSettings` as a
  serialized JSON string. Treating it as already-parsed leads to attribute
  errors. Always `json.loads()` before evaluating nested settings.

- **`verify-ca` vs `verify-full` are not interchangeable.** `verify-ca`
  validates the certificate chain but NOT the hostname. `verify-full`
  validates both. A MITM attack with a valid-but-wrong-domain certificate
  passes `verify-ca` but fails `verify-full`. For database migrations, always
  recommend `verify-full`.

- **`EnableLogging: true` does NOT guarantee logs are written.** DMS requires
  the `dms-cloudwatch-logs-role` service role with `logs:CreateLogGroup`,
  `logs:CreateLogStream`, and `logs:PutLogEvents` to emit CloudWatch Logs. If
  the role is missing or lacks permissions, DMS silently drops logs — the
  task reports running and `EnableLogging: true`, but no log groups appear.
  Always verify the role exists when remediating NO_LOGGING.

- **`verify-full` requires the CA certificate bundle on the instance.** When
  using `SslMode: verify-full` with a self-signed or private-CA database
  certificate, the CA bundle must be imported into the replication instance
  (`--certificate-arn` on the endpoint). Without it, the task enters `STOPPED`
  with a generic connection error that masquerades as a TLS issue.

- **Cross-account endpoint access requires BOTH network and IAM paths.** When
  the source or target database is in a different AWS account, the replication
  instance needs VPC peering or Transit Gateway connectivity AND the database
  security group must allow inbound from the instance's subnet CIDR. A common
  misconfiguration is correct routing but a security group blocking the DMS
  instance — the task fails with a connection timeout that looks like a TLS
  error.

- **`EngineVersion` gates feature support.** DMS replication instance
  `EngineVersion` determines supported features. Versions before 3.4.x do not
  support CDC for MongoDB/DocumentDB; versions before 3.1.x lack Babelfish
  target support. An unsupported engine/version combination produces silent
  CDC lag — the task reports running but no data flows. Verify EngineVersion
  compatibility when auditing CDC tasks on non-standard engines.

- **DMS task IAM role over-privilege is a hidden blast radius.** The IAM role
  assumed by DMS for endpoint access often accumulates broad permissions
  (`dms:*` or `rds-db:*` on `*`). While this does not change the task
  verdict, it widens the credential blast radius if the replication instance
  is compromised. Flag the task IAM role for least-privilege review alongside
  the task config audit.

### Step 1: TLS / SSL evaluation (highest priority — plaintext data pipe)

For each endpoint (source and target, except S3 targets), evaluate `SslMode`:

| SslMode | Classification | Reason |
|---|---|---|
| `none` | **NO_TLS** | Plaintext — all data flows unencrypted between source and target. |
| missing | **NO_TLS** | Defaults to `none` — treated identically to explicit plaintext. |
| `require` | CONFIG_GAP (additive) | TLS present but no certificate verification — MITM possible. |
| `verify-ca` | OK for TLS dimension | Certificate chain validated. |
| `verify-full` | OK for TLS dimension | Certificate + hostname validated — strongest TLS posture. |

**Priority rule:** if ANY endpoint (source or target) has `SslMode: none` or
missing, the task verdict is **NO_TLS** — do not continue to Step 2 unless
enumerating additional findings. The data pipe is plaintext regardless of how
well-configured the other endpoint is.

**S3 target exception:** S3 target endpoints (`EngineName: s3`) do not have
`SslMode` — HTTPS is enforced by the AWS SDK. Do NOT classify the target as
NO_TLS for missing SslMode. The source endpoint is still evaluated.

**Self-managed source on EC2:** If the source is a self-managed database on
EC2, `SslMode: none` means traffic flows over the VPC network. For cross-VPC
or cross-account migrations, this traffic traverses peering or Transit
Gateway — still unencrypted. Flag as NO_TLS regardless of network topology.

### Step 2: Logging evaluation (second priority — silent failures)

Parse `TaskSettings` (JSON string to object) and evaluate the logging
configuration:

| Condition | Classification | Reason |
|---|---|---|
| `EnableLogging: false` | **NO_LOGGING** | No CloudWatch Logs — task failures invisible. |
| `EnableLogging` absent from TaskSettings | **NO_LOGGING** | Same as false — DMS does not enable logging by default. |
| `EnableLogging: true` + `LogLevel: default` | CONFIG_GAP (additive) | Minimal output. Upgrade to `info` or `warning` for audit trail. |
| `EnableLogging: true` + `LogLevel: info/warning` + `LogComponents` populated | OK | Sufficient for audit trail. |

**The metrics-vs-logs trap:** DMS emits CloudWatch metrics regardless of
`EnableLogging`. An operator monitoring `CDCLatencySource` or
`FullLoadThroughputBandwidth` sees normal values while logs would reveal data
loss. `EnableLogging: false` is a silent failure amplifier — the task looks
healthy while data integrity degrades.

### Step 3: Replication instance configuration

Evaluate the replication instance backing the task:

| Condition | Classification | Reason |
|---|---|---|
| `PubliclyAccessible: true` | CONFIG_GAP (additive) | Instance has public IP — internet-reachable credential store. |
| `MultiAZ: false` on `cdc` or `full-load-and-cdc` task | CONFIG_GAP (additive) | No hot standby — CDC position lost on failure requires full reload. |
| `MultiAZ: false` on `full-load`-only task | OK for this dimension | Full-load restarts from scratch — Multi-AZ beneficial but not critical. |
| `KmsKeyId` absent on instance | CONFIG_GAP (additive) | Instance storage unencrypted. |
| `ReplicationInstanceClass: dms.t2.*` / `dms.t3.micro` on CDC task | CONFIG_GAP (additive) | Burstable — CPU credits deplete under sustained CDC, causing latency spikes. |

**Multi-AZ nuance:** In DMS, the Multi-AZ standby maintains CDC replication
position but does NOT serve as an active replica. On failover, DMS
automatically promotes the standby — no operator intervention needed. Without
Multi-AZ, the task enters `STOPPED` state on instance failure and requires
manual restart with potential CDC position loss.

### Step 4: Endpoint encryption and task settings integrity

Evaluate endpoint-level encryption and task-level integrity controls:

| Condition | Classification | Reason |
|---|---|---|
| Endpoint `KmsKeyId` absent | CONFIG_GAP (additive) | Endpoint config (including credentials) stored unencrypted by DMS. |
| `ValidationSettings.EnableValidation: false` or absent | CONFIG_GAP (additive) | No automated data-integrity check — row mismatches undetected. |
| `RecoveryTable` absent on CDC task | CONFIG_GAP (additive) | CDC checkpoint in memory only — lost on reboot, requires full reload. |
| `DeletionProtection: false` or absent | CONFIG_GAP (additive) | Task can be deleted via CLI — loses CDC position and migration state. |

**Validation importance:** DMS task validation compares source and target row
counts and (optionally) data contents after migration. Without it, you have no
automated mechanism to detect silent data loss — a row that fails to replicate
due to a constraint violation appears normal in metrics.

### Step 5: Aggregation — first failing dimension wins (priority order)

```text
if any finding == NO_TLS:       verdict = NO_TLS
elif any finding == NO_LOGGING:  verdict = NO_LOGGING
elif any finding == CONFIG_GAP:  verdict = CONFIG_GAP
else:                            verdict = OK
```

All findings are enumerated in the output regardless of verdict. A task with
NO_TLS may also have logging and config findings — the operator needs the
full picture, not just the worst dimension.

## Output format (per task)

```text
TASK: <replication-task-id or ARN>
VERDICT: NO_TLS | NO_LOGGING | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_TLS] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — NO_TLS with compounding findings

```text
TASK: arn:aws:dms:us-east-1:111111111111:task:prod-migration-task
VERDICT: NO_TLS
REASON: Source endpoint (MySQL) has SslMode none — all replicated data flows
in plaintext between source and target (Step 1). Logging is enabled but task
validation is absent, compounding the risk.
FINDINGS:
  - [NO_TLS] Source endpoint SslMode is none — plaintext data in transit (Step 1)
  - [CONFIG_GAP] ValidationSettings.EnableValidation absent — no data-integrity check (Step 4)
  - [OK] Target endpoint SslMode is verify-full (Step 1)
  - [OK] EnableLogging is true with LogLevel info (Step 2)
REMEDIATION:
  1. NO_TLS — Modify source endpoint SslMode to verify-full:
     aws dms modify-endpoint --endpoint-arn <source-arn> --ssl-mode verify-full.
  2. CONFIG_GAP — Enable task validation:
     aws dms modify-replication-task --replication-task-arn <task-arn>
     --replication-task-settings '{"ValidationSettings":{"EnableValidation":true}}'.
```

## Anti-Patterns — NEVER

- NEVER classify an endpoint with `SslMode: require` as NO_TLS. The connection
  IS encrypted — it just lacks certificate verification. `require` is a
  CONFIG_GAP. Conflating encryption-present with encryption-absent produces
  alert fatigue.

- NEVER flag an S3 target endpoint (`EngineName: s3`) for missing `SslMode`.
  S3 targets use HTTPS by default (AWS SDK enforced). The `SslMode` field is
  not applicable. Flagging it is a false positive.

- NEVER treat `KmsKeyId` on a DMS endpoint as equivalent to data-in-transit
  encryption. The KMS key encrypts the endpoint configuration stored by DMS
  (credentials, connection string), NOT data flowing between databases.
  Only `SslMode` controls transit encryption.

- NEVER assume a DMS task is healthy because CloudWatch metrics show normal
  values. Metrics are always emitted regardless of `EnableLogging`. The
  metrics-vs-logs trap means `CDCLatencySource` can look fine while logs
  reveal data loss. Always check `EnableLogging`, not metrics.

- NEVER overlook `PubliclyAccessible: true` on a replication instance. The
  instance stores database credentials for both source and target. A public
  instance is an internet-reachable credential store.

- NEVER classify `MultiAZ: false` as a finding on a `full-load`-only task.
  Full-load tasks restart from the beginning on failure — Multi-AZ is
  beneficial but not critical. Only flag Multi-AZ absence on `cdc` or
  `full-load-and-cdc` tasks where CDC position continuity matters.

- NEVER evaluate `TaskSettings` without parsing it first. The DMS API returns
  `ReplicationTaskSettings` as a serialized JSON string. Accessing nested
  fields on the raw string produces errors. Always `json.loads()` first.

- NEVER recommend changing `SslMode` to `verify-full` without verifying the
  source database has TLS enabled and a valid certificate. Switching from
  `none` to `verify-full` on a database without TLS configured will break the
  DMS task connection. Verify the certificate chain first.

- NEVER flag a stopped or failed task with a security verdict from its
  `Status` field. `Status: stopped` is an operational state, not a security
  finding. Still audit the configuration — a stopped task with `SslMode: none`
  will replicate in plaintext when restarted.

- NEVER modify a running DMS task's endpoints without stopping the task first.
  `modify-endpoint` on an in-use endpoint may cause unpredictable behavior.
  Always `stop-replication-task` before endpoint modifications, then
  `start-replication-task` after.

- NEVER recommend deleting a DMS task as remediation without confirming the
  migration is complete. Task deletion is irreversible and loses CDC position.
  Prefer modifying settings over recreating tasks.

- NEVER treat `verify-ca` and `verify-full` as equivalent. `verify-ca`
  validates the certificate chain but NOT the hostname — a MITM with a
  valid-but-wrong-domain certificate passes. For database migrations, always
  recommend `verify-full`.

- NEVER assume `EnableLogging: true` guarantees CloudWatch Logs are written.
  The `dms-cloudwatch-logs-role` must exist with `logs:CreateLogGroup`,
  `logs:CreateLogStream`, `logs:PutLogEvents` — without it, DMS silently
  drops logs. Verify the role exists before treating the logging dimension
  as remediated.

- NEVER ignore the replication instance `EngineVersion` when auditing CDC
  tasks on non-standard engines (MongoDB, DocumentDB, Babelfish). Older
  versions silently fail to support CDC for these engines — the task reports
  running but no data flows. Verify EngineVersion compatibility.

- NEVER overlook pagination when auditing multiple tasks or endpoints.
  `describe-replication-tasks` and `describe-endpoints` return at most 100
  per page. Iterating only the first page silently misses the long tail.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (modify-endpoint, modify-replication-task, modify-replication-instance),
  emit:
  `CONFIRM: About to <action> on task/endpoint <id>. This affects
  <consequence>. Proceed? (yes/no)` Do NOT execute until the operator confirms.

- **Stop-before-modify rule.** Before modifying endpoint SSL settings, verify
  the task is stopped. If `Status: running`, emit:
  `WARN: Task <id> is running. Stop before modifying endpoints:
  aws dms stop-replication-task --replication-task-arn <arn>`

- **Endpoint certificate verification.** Before recommending
  `SslMode: verify-full`, verify the source database has TLS enabled:
  `aws dms test-connection --replication-instance-arn <instance-arn>
  --endpoint-arn <endpoint-arn>`. If the test fails with a TLS error, the
  database certificate must be configured first.

- **Backup task settings.** Before modifying `TaskSettings`, capture the
  current configuration:
  `aws dms describe-replication-tasks --filters Name=replication-task-id,Values=<id> --output json > /tmp/<id>-backup.json`
  Task settings changes are not versioned — no undo without a backup.

## Remediation guidance

### For NO_TLS — endpoint SslMode is none or missing

1. Stop the task: `aws dms stop-replication-task --replication-task-arn <arn>`.
2. Verify the source database supports TLS:
   `aws dms test-connection --replication-instance-arn <instance> --endpoint-arn <source>`.
3. Modify the endpoint SSL mode to `verify-full`:
   `aws dms modify-endpoint --endpoint-arn <source-arn> --ssl-mode verify-full`.
4. If the database lacks a valid TLS certificate, configure one first —
   switching to `verify-full` without a certificate breaks the connection.
5. Restart the task:
   `aws dms start-replication-task --replication-task-arn <arn> --start-type start-replication`.

### For NO_LOGGING — EnableLogging is false or absent

1. Parse current `TaskSettings` from `describe-replication-tasks`.
2. Set `EnableLogging: true` and `LogLevel: info` with `LogComponents`
   including `DATA_STRUCTURE`, `COMMON_AGENT`, `SOURCE_UNLOAD`, `TARGET_LOAD`:
   ```bash
   aws dms modify-replication-task --replication-task-arn <arn> \
     --replication-task-settings '{"Logging":{"EnableLogging":true,"LogLevel":"info","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_INFO"},{"Id":"COMMON_AGENT","Severity":"LOGGER_SEVERITY_ONLY_INFO"}]}}'
   ```
3. Verify the task IAM role has `logs:CreateLogGroup`, `logs:CreateLogStream`,
   `logs:PutLogEvents` — without these, DMS cannot write logs even with
   `EnableLogging: true`.

### For CONFIG_GAP — instance, endpoint, or task settings issues

1. **PubliclyAccessible:**
   `aws dms modify-replication-instance --replication-instance-arn <arn> --publicly-accessible false`.
2. **Multi-AZ:**
   `aws dms modify-replication-instance --replication-instance-arn <arn> --multi-az`.
3. **Endpoint KMS:**
   `aws dms modify-endpoint --endpoint-arn <arn> --kms-key-id <key-arn>`.
4. **Validation:**
   `aws dms modify-replication-task --replication-task-arn <arn> --replication-task-settings '{"ValidationSettings":{"EnableValidation":true,"ValidationMode":"ROW_LEVEL"}}'`.
5. **Deletion protection:**
   `aws dms modify-replication-task --replication-task-arn <arn> --deletion-protection`.

### For OK

1. No remediation required.
2. Recommend periodic re-audit after any endpoint or task modification.
3. Recommend a CloudWatch alarm on DMS task log filter patterns for `ERROR`
   and `WARNING` entries during migration.

## Recent AWS features (2024-2026)

- **DMS Serverless (2024):** DMS now offers a serverless deployment option that auto-scales capacity without pre-provisioning replication instances. Auditors should note that serverless DMS changes the audit surface — there is no replication instance to audit (no public-accessibility, single-AZ, or KMS checks on the instance). Instead, auditors should verify DMS Serverless configuration (max DCUs, VPC settings).
- **Enhanced schema conversion (2024-2025):** DMS Schema Conversion (formerly SCT) is now integrated into the DMS console. No new audit-surface fields for the replication task itself.
- **Replication config (2024):** DMS introduced a new `ReplicationConfig` API for serverless replications. Auditors should verify that the replication config has appropriate `ComputeConfig` settings (replication subnet group, VPC security group, KMS key).

## Domain

AWS CloudOps / DMS Migration Security & Data Integrity.

## AWS documentation

- **AWS Database Migration Service User Guide** — https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html
- **DMS Security** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html
- **DMS API Reference** — https://docs.aws.amazon.com/dms/latest/APIReference/
- **DMS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/dms/
- **DMS Serverless** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Serverless.html
