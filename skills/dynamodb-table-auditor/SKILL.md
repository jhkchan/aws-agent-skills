---
name: dynamodb-table-auditor
description: Audits DynamoDB table configurations for encryption-at-rest (KMS), point-in- time recovery (PITR), capacity mode (on-demand vs provisioned with autoscaling), TTL configuration, backup posture, and GSI/LSI quota risk. Emits a deterministic verdict (UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH | CONFIG_GAP | OK) per table with enumerated findings and CLI remediation. Use when reviewing a DynamoDB table before production deployment, validating backup/encryption compliance, checking capacity mode suitability, or auditing table hardening posture.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline table-config classification. Live-account audits use aws dynamodb describe-table, describe-continuous- backups, describe-time-to-live, and aws application-autoscaling describe- scaling-policies (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  verdict_shape: UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH | CONFIG_GAP | OK
  when_to_use: Reviewing a DynamoDB table before production deployment, checking encryption compliance, validating PITR enablement, auditing capacity mode suitability, evaluating GSI/LSI quota risk, or hardening table configuration posture.
  activation_triggers: audit this DynamoDB table, is my DynamoDB table encrypted, check PITR on DynamoDB, DynamoDB capacity mode, DynamoDB backup posture, is deletion protection enabled, GSI quota DynamoDB, harden DynamoDB table
  invocation_schema: 'Input: either (a) a DynamoDB table configuration (describe-table + describe-continuous-backups + describe-time-to-live + autoscaling policies), OR (b) a table name/ARN for live-account audit. Output: deterministic TABLE/VERDICT/REASON/FINDINGS/REMEDIATION block per table, where VERDICT ∈ {UNENCRYPTED, NO_PITR, CAPACITY_MISMATCH, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: DynamoDB, table auditor, SSE, KMS encryption, PITR, point-in-time recovery, continuous backups, capacity mode, provisioned, on-demand, PAY_PER_REQUEST, autoscaling, TTL, time to live, GSI, LSI, deletion protection, backup, DynamoDB Streams, billing mode, DynamoDB compliance
  tags: dynamodb, databases, encryption, backup, capacity, compliance, audit
---

# DynamoDB Table Auditor

## CRITICAL RULE — confirmation gate (read first)

**Every state-changing remediation** (`update-table`, `update-continuous-backups`,
`update-time-to-live`, `delete-table`, `update-table` for billing-mode/SSE/
streams/deletion-protection) is **blocked** until the operator explicitly
confirms. Emit this exact prompt and halt until a `yes` is received:

```text
CONFIRM: About to <action> on table <name>. This affects <consequence>. Proceed? (yes/no)
```

This gate is **non-negotiable** and applies even when the operator supplied the
table name. DynamoDB mutations are asynchronous, partially reversible at best,
and can trigger background re-encryption migrations lasting hours on large
tables. Do not batch-confirm — each action gets its own gate.

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, ordered UNENCRYPTED > NO_PITR > CAPACITY_MISMATCH > CONFIG_GAP > OK.
The most counter-intuitive fact is that "UNENCRYPTED" does not mean plaintext —
every DynamoDB table is encrypted at rest by default. It means the table lacks
customer-controlled KMS encryption, which strips away audit visibility,
CloudTrail Decrypt logging, key-rotation control, and compliance evidence.

DynamoDB is the default durable datastore for serverless workloads. Three
misconceptions dominate DynamoDB misconfiguration:

- **"Default encryption is fine for compliance."** DynamoDB's default
  (SSEType: AES256) uses an **AWS-owned key** — you have zero CloudTrail
  visibility, zero key policy, zero rotation control. PCI-DSS, HIPAA, and SOC2
  require customer-managed encryption with audit traceability.

- **"AWS Backup covers recovery."** AWS Backup (scheduled snapshots) and PITR
  (continuous 35-day replay) are **different mechanisms with different RPOs**.
  A table with AWS Backup but no PITR can only restore to snapshot timestamps —
  not to any second in the last 35 days. Accidental writes/deletes between
  snapshots are unrecoverable without PITR.

- **"On-demand mode is always safe."** On-demand allocates burst capacity based
  on the trailing 30 minutes of traffic. A cold-start spike from zero can still
  throttle if the burst bucket is empty — and for steady high-throughput
  workloads, on-demand costs 3-5x provisioned with autoscaling.

## Invocation schema — input shape

The skill accepts either a table name/ARN for live-account audit OR a complete
config bundle. The canonical input shape (preferred for offline classification):

```json
{
  "table_name": "<name>",
  "table_arn": "arn:aws:dynamodb:<region>:<acct>:table/<name>",
  "describe_table": { "TableStatus": "ACTIVE", "BillingModeSummary": {},
                      "SSEDescription": {}, "GlobalSecondaryIndexes": [],
                      "LocalSecondaryIndexes": [], "DeletionProtectionEnabled": false,
                      "StreamSpecification": {}, "TableSizeBytes": 0 },
  "describe_continuous_backups": { "ContinuousBackupsStatus": "ENABLED|DISABLED",
                                   "PointInTimeRecoveryDescription": {} },
  "describe_time_to_live": { "TimeToLiveDescription": { "TimeToLiveStatus": "ENABLED|DISABLED" } },
  "scaling_policies": []
}
```

Required fields for classification: `TableStatus`, `SSEDescription`,
`BillingModeSummary`, `ContinuousBackupsStatus`. Missing `TableName` or
`TableStatus` short-circuits to `VERDICT: ERROR`.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `SSEDescription.Status: DISABLED` or `SSEType: AES256` or SSE absent | **UNENCRYPTED** | Step 1 |
| `ContinuousBackupsStatus: DISABLED` or absent | **NO_PITR** | Step 2 |
| `BillingMode: PROVISIONED` + no autoscaling on table or any GSI | **CAPACITY_MISMATCH** | Step 3 |
| `SSEType: KMS` with `alias/aws/dynamodb` (AWS-managed key) | additive **CONFIG_GAP** | Step 4 |
| TTL disabled or absent | additive **CONFIG_GAP** | Step 4 |
| `DeletionProtectionEnabled: false` on production table | additive **CONFIG_GAP** | Step 4 |
| GSI count >= 15 (approaching 20 soft quota) | additive **CONFIG_GAP** | Step 4 |
| No DynamoDB Streams configured | additive **CONFIG_GAP** | Step 4 |
| All dimensions pass (customer CMK, PITR on, capacity OK, TTL on, protection on) | **OK** | Step 5 |

## Pre-flight: table metadata gate

Before classifying, verify the table exists and is in an operable state.
Several table attributes **short-circuit** the audit.

| Attribute | Value | Effect on audit |
|---|---|---|
| `TableStatus` | `CREATING` | Table is not yet active — capacity and backup settings may not be settled. Emit ERROR. |
| `TableStatus` | `DELETING` | Table is being deleted — audit is moot. Emit ERROR. |
| `TableStatus` | `ARCHIVED` | Table is archived (Standard-InfrequentAccess class). Capacity mode is N/A. Skip Step 3. |
| `SSEDescription.InaccessibleEncryptionDateTime` | present | The KMS key is inaccessible — all read/write operations are failing. This is an active outage. Emit ERROR and flag as incident. |
| `Replicas` | present | **Global Table.** Each replica has INDEPENDENT capacity settings and INDEPENDENT PITR/backup config. Audit each replica separately — a clean primary does NOT imply replicas are clean. |

**If the table configuration JSON is malformed** (invalid JSON, missing
`TableName` or `TableStatus`, truncated output, or `describe-table` returned
an error), output the deterministic ERROR block and STOP — do not attempt to
infer missing fields from neighboring resources:

```text
TABLE: <table-name-or-unknown>
VERDICT: ERROR
REASON: Table configuration is not valid JSON or is missing required fields (<field>) — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws dynamodb describe-table --table-name <name> --output json` and re-audit.
```

Common malformed-input causes: `--output text` instead of `--output json`
(produces tab-delimited non-JSON); truncated large responses paginated by
`describe-table`; cross-region calls returning empty when the table is in a
different region than the AWS CLI default. Verify region matches the table
ARN before re-auditing.

## Process — Classification logic (evaluate all dimensions, aggregate worst)

### Step 0: Expert knowledge — non-obvious DynamoDB behaviors

All thirteen Step 0 expert behaviors (always-encrypted semantics, PITR vs AWS Backup, GSI cascade throttling, LSI 10 GB limit, LSI creation-time-only, GSI/LSI quotas, TTL 48-hour lag, on-demand burst bucket, autoscaling lag, KMS dependency cascade, PITR-restore-new-table, billing-mode cooldown, deletion protection) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when classifying edge-case configurations.

### Step 1: Encryption (KMS) evaluation — UNENCRYPTED check

Evaluate the `SSEDescription` block from `describe-table`:

- **`Status: DISABLED` OR `SSEType: AES256` OR SSEDescription absent** →
  **UNENCRYPTED**. The table uses DynamoDB's default AWS-owned-key encryption
  with no customer KMS visibility. This is the worst verdict — halt and emit.
  Record all other dimensions as findings but the verdict is UNENCRYPTED.

- **`SSEType: KMS` + `KMSMasterKeyArn` containing `alias/aws/dynamodb`** →
  AWS-managed KMS key. KMS encryption IS present (better than AES256), but the
  key is managed by DynamoDB — no customer policy, no customer rotation
  control, limited CloudTrail visibility. Record as an additive CONFIG_GAP
  sub-finding (Step 4). Do NOT classify as UNENCRYPTED.

- **`SSEType: KMS` + `KMSMasterKeyArn` pointing to a customer-managed CMK** →
  OK for this dimension. Full CloudTrail visibility, customer-controlled
  rotation, customer-controlled policy.

**Global Table replicas:** each replica uses the same KMS key ARN as the
primary (the key must exist in each replica region). Verify the key exists in
every replica region — a missing key in a replica region causes
`InaccessibleEncryptionDateTime` (active outage).

### Step 2: PITR (Point-in-Time Recovery) evaluation — NO_PITR check

Evaluate `ContinuousBackupsDescription` from `describe-continuous-backups`:

- **`ContinuousBackupsStatus: DISABLED` or block absent** → **NO_PITR**. The
  table has no continuous recovery — accidental writes or deletes are
  unrecoverable. AWS Backup snapshots do NOT substitute (different RPO).

- **`ContinuousBackupsStatus: ENABLED` + `PointInTimeRecoveryDescription
  .PointInTimeRecoveryStatus: ENABLED`** → OK. `EarliestRestorableDateTime`
  and `LatestRestorableDateTime` define the recovery window (up to 35 days).

- **`ContinuousBackupsStatus: ENABLED` but
  `PointInTimeRecoveryDescription` absent** → still OK — DynamoDB treats
  ENABLED continuous backups as PITR-enabled.

### Step 3: Capacity mode evaluation — CAPACITY_MISMATCH check

Evaluate `BillingModeSummary` from `describe-table` + autoscaling policies
from `application-autoscaling`:

- **`BillingMode: PAY_PER_REQUEST` (on-demand)** → OK for this dimension.
  On-demand handles traffic without capacity planning. Note the burst-bucket
  caveat (Step 0) as operational guidance but NOT a verdict driver.

- **`BillingMode: PROVISIONED` + autoscaling on table AND all GSIs** → OK.
  Target-tracking autoscaling on both the table and every GSI is the correct
  provisioned posture.

- **`BillingMode: PROVISIONED` + NO autoscaling policy on the table** →
  **CAPACITY_MISMATCH**. Fixed throughput with no autoscaling will throttle on
  traffic spikes. The table is one burst away from `ProvisionedThroughputExceededException`.

- **`BillingMode: PROVISIONED` + autoscaling on table but NOT on a GSI** →
  **CAPACITY_MISMATCH**. The GSI is the throttle origin — writes to the base
  table will be throttled when the GSI cannot keep up (Step 0 cascade rule).
  This is the most commonly missed capacity misconfiguration.

- **`BillingMode: PROVISIONED` + autoscaling with `MinCapacity: 1` and
  `MaxCapacity: 1`** → **CAPACITY_MISMATCH** (degenerate autoscaling — the
  scaling range is zero, providing no autoscaling effect).

### Step 4: Config-gap accumulation — CONFIG_GAP findings

Evaluate supplementary configuration dimensions. These are additive findings —
if any exist and no higher-priority verdict (Steps 1-3) triggered, the verdict
is CONFIG_GAP:

| Check | Condition | Finding |
|---|---|---|
| **AWS-managed KMS key** | `SSEType: KMS` with `alias/aws/dynamodb` | CONFIG_GAP: no customer key policy, limited CloudTrail |
| **TTL disabled** | `TimeToLiveDescription.TimeToLiveStatus: DISABLED` or absent | CONFIG_GAP: no automatic item expiry — cost and compliance risk |
| **Deletion protection off** | `DeletionProtectionEnabled: false` or absent | CONFIG_GAP: table can be deleted accidentally or by ransomware |
| **GSI quota proximity** | GSI count >= 15 (of 20 soft limit) | CONFIG_GAP: approaching GSI ceiling — plan consolidation |
| **No DynamoDB Streams** | `StreamSpecification` absent or `StreamEnabled: false` | CONFIG_GAP: no CDC pipeline for audit/analytics/recovery |
| **LSI on growing table** | LSI count > 0 AND `TableSizeBytes` growing | CONFIG_GAP: 10 GB per-partition LSI limit risk |

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum-priority** finding across all steps, where
UNENCRYPTED > NO_PITR > CAPACITY_MISMATCH > CONFIG_GAP > OK:

```text
verdict = priority_max(encryption, pitr, capacity, config_gaps)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per table)

```text
TABLE: <table-name>
VERDICT: UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [UNENCRYPTED|NO_PITR|CAPACITY_MISMATCH|CONFIG_GAP|OK] <finding (Step N)>
REMEDIATION: <specific CLI action per finding, or "None required" if OK>
```

### Worked example — UNENCRYPTED with NO_PITR

```text
TABLE: unencrypted-and-no-pitr-worst-first
VERDICT: UNENCRYPTED
REASON: SSEDescription shows SSEType AES256 with Status DISABLED — table uses
AWS-owned-key encryption with no customer KMS visibility (Step 1). PITR is also
disabled, but UNENCRYPTED takes priority as the worst verdict.
FINDINGS:
  - [UNENCRYPTED] SSE disabled (SSEType: AES256) — no customer-controlled KMS
    encryption; zero CloudTrail Decrypt visibility, zero key policy (Step 1)
  - [NO_PITR] ContinuousBackupsStatus: DISABLED — no 35-day recovery window (Step 2)
REMEDIATION:
  1. Enable SSE-KMS with a customer-managed CMK:
     aws dynamodb update-table --table-name unencrypted-and-no-pitr-worst-first \
       --sse-specification Enabled=true,SSEType=KMS,\
KMSMasterKeyId=arn:aws:kms:us-east-1:111111111111:key/<cmk-id>
  2. Enable PITR:
     aws dynamodb update-continuous-backups \
       --table-name unencrypted-and-no-pitr-worst-first \
       --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

## Anti-Patterns — NEVER

- NEVER say a DynamoDB table is "not encrypted" or "stores data in plaintext."
  Every DynamoDB table is encrypted at rest. The verdict UNENCRYPTED means "no
  customer-controlled KMS encryption" — the distinction matters for compliance
  evidence and for operator trust.

- NEVER treat AWS Backup as a substitute for PITR. AWS Backup takes scheduled
  snapshots; PITR provides continuous 35-day replay. A table with AWS Backup
  but no PITR still loses data written between snapshots. They are
  complementary, not interchangeable.

- NEVER classify `SSEType: KMS` with `alias/aws/dynamodb` as UNENCRYPTED. KMS
  encryption IS present — the table has SSE enabled. The AWS-managed key is a
  CONFIG_GAP (no customer policy), not an UNENCRYPTED verdict. Conflating them
  inflates severity and erodes operator trust.

- NEVER assume on-demand billing mode eliminates all capacity risk. On-demand
  has a finite burst bucket derived from the trailing 30 minutes. A cold-start
  spike from zero can still throttle. Flag this as operational guidance, but do
  NOT classify on-demand as CAPACITY_MISMATCH — it is OK for this dimension.

- NEVER recommend adding an LSI to an existing table. LSIs can ONLY be created
  at table creation time — this is a hard API constraint. The correct guidance
  is to create a new table with the LSI and migrate data, or use a GSI (which
  CAN be added post-creation).

- NEVER rely on TTL for immediate data deletion or GDPR compliance. TTL items
  persist for up to 48 hours after expiry. TTL is a cost-optimization feature,
  not a compliance enforcement mechanism. For immediate deletion, the
  application must explicitly delete items.

- NEVER forget to check GSI autoscaling separately from the base table. GSI
  throttling cascades to the base table — a table with autoscaling but a GSI
  without autoscaling is CAPACITY_MISMATCH. The base-table autoscaling policy
  does NOT cover GSIs.

- NEVER audit only the primary of a Global Table. Each replica has independent
  capacity settings, independent PITR config, and independent KMS key
  availability. A clean primary does NOT imply replicas are clean. Audit every
  replica separately.

- NEVER treat the 5-LSI limit as soft. The LSI quota (5 per table) is a HARD
  limit enforced at the API level — it cannot be increased. The GSI quota
  (20 per table) is a soft limit that can be raised via support ticket. Do not
  conflate the two.

- NEVER recommend switching billing mode for per-request cost optimization.
  DynamoDB enforces a cooldown between mode switches. Choose a mode based on
  sustained traffic profile (steady = provisioned + autoscaling; bursty =
  on-demand), not per-request cost deltas.

- NEVER assume `DeletionProtectionEnabled: false` is fine for dev/staging
  tables without flagging it. Even non-production tables can contain sensitive
  data or serve as DR sources. Always flag it as CONFIG_GAP and let the
  operator decide whether to suppress.

- NEVER ignore `dynamodb:*` IAM policies with no resource ARN constraint. An
  inline policy granting `dynamodb:*` on `*` lets the principal read/scan every
  table in the account — including system tables and tables the principal
  should never touch. Flag as a CONFIG_GAP sub-finding when the operator
  shares the table's resource policy. The narrowest scope is
  `dynamodb:GetItem|PutItem|UpdateItem|DeleteItem|Query|Scan` on the specific
  table ARN with a `StringEquals` condition on `dynamodb:TableName`.

- NEVER assume a CMK key policy is correct just because the DynamoDB update
  succeeded. SSE-KMS requires the key policy to grant `kms:GenerateDataKey`
  and `kms:Decrypt` to `dynamodb.<region>.amazonaws.com` AND to the calling
  principal. A CMK whose policy was tightened later (e.g., restricted to a
  single role) silently breaks cross-service access — DynamoDB returns
  `KMSAccessDeniedException` on the next data-key refresh (~5 min cache TTL).
  Always verify `aws kms get-key-policy` after CMK rotation.

- NEVER enable DynamoDB Streams as a default "hardening" step on tables whose
  workload does not consume CDC. Streams incur write-amplification cost and
  attach an implicit 24-hour retention window. Flag absence of streams as
  CONFIG_GAP only when the operator's stated architecture uses CDC (Lambda
  triggers, OpenSearch sync, Kinesis replay). For tables with no downstream
  consumer, omit streams from the verdict — `StreamEnabled: false` is the
  correct posture, not a defect.

## Pre-flight safety checks (run before any remediation CLI)

Pre-remediation safety checks (SSE migration monitoring, CMK enabled check, mode-switch cost warning, PITR cost warning, additive-first preference) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any remediation CLI.

## Remediation guidance

All remediation CLI sequences (UNENCRYPTED SSE-KMS, NO_PITR, CAPACITY_MISMATCH autoscaling per table and per GSI, CONFIG_GAP CMK/TTL/deletion-protection/streams, OK recommendations) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when emitting REMEDIATION steps.

## Deep reference: DynamoDB capacity and recovery internals

Capacity and recovery internals (on-demand burst bucket sizing, autoscaling 3-5 minute timing, PITR restore mechanics, GSI write-capacity model, SSE-KMS data-key caching) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when explaining a verdict's underlying mechanics.

## Recent AWS features (2024-2026)

Recent AWS features 2024-2026 (table classes, incremental S3 export, Amazon Q integration, Global Tables v2 metrics) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a 2024-2026 feature affects the audit.

## References (load on demand)

- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Step 0 expert behaviors, capacity/recovery internals, and recent AWS features (2024-2026) moved from SKILL.md
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — pre-remediation safety checks and all remediation CLI sequences moved from SKILL.md

## Domain

AWS CloudOps / DynamoDB Table Hardening & Compliance.

## AWS documentation

- **Amazon DynamoDB Developer Guide** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- **DynamoDB Security** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/security.html
- **DynamoDB API Reference** — https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/
- **DynamoDB AWS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/dynamodb/
- **DynamoDB table classes** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ddn-table-classes.html
