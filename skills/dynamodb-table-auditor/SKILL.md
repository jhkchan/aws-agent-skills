---
name: dynamodb-table-auditor
description: >-
  Audits DynamoDB table configurations for encryption-at-rest (KMS), point-in-
  time recovery (PITR), capacity mode (on-demand vs provisioned with
  autoscaling), TTL configuration, backup posture, and GSI/LSI quota risk.
  Emits a deterministic verdict (UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH |
  CONFIG_GAP | OK) per table with enumerated findings and CLI remediation. Use
  when reviewing a DynamoDB table before production deployment, validating
  backup/encryption compliance, checking capacity mode suitability, or auditing
  table hardening posture.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline table-config classification.
  Live-account audits use aws dynamodb describe-table, describe-continuous-
  backups, describe-time-to-live, and aws application-autoscaling describe-
  scaling-policies (AWS CLI v2, SSO or key-based credentials).
keywords:
  - DynamoDB
  - table auditor
  - SSE
  - KMS encryption
  - PITR
  - point-in-time recovery
  - continuous backups
  - capacity mode
  - provisioned
  - on-demand
  - PAY_PER_REQUEST
  - autoscaling
  - TTL
  - time to live
  - GSI
  - LSI
  - deletion protection
  - backup
  - DynamoDB Streams
  - billing mode
  - DynamoDB compliance
tags: [dynamodb, databases, encryption, backup, capacity, compliance, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Databases
  verdict_shape: "UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a DynamoDB table before production deployment, checking encryption
    compliance, validating PITR enablement, auditing capacity mode suitability,
    evaluating GSI/LSI quota risk, or hardening table configuration posture.
  activation_triggers:
    - "audit this DynamoDB table"
    - "is my DynamoDB table encrypted"
    - "check PITR on DynamoDB"
    - "DynamoDB capacity mode"
    - "DynamoDB backup posture"
    - "is deletion protection enabled"
    - "GSI quota DynamoDB"
    - "harden DynamoDB table"
  invocation_schema: >-
    Input: either (a) a DynamoDB table configuration (describe-table +
    describe-continuous-backups + describe-time-to-live + autoscaling policies),
    OR (b) a table name/ARN for live-account audit. Output: deterministic
    TABLE/VERDICT/REASON/FINDINGS/REMEDIATION block per table, where
    VERDICT ∈ {UNENCRYPTED, NO_PITR, CAPACITY_MISMATCH, CONFIG_GAP, OK, ERROR}.
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

These behaviors are easy to misjudge without operational DynamoDB experience.
Each changes the verdict if ignored:

- **DynamoDB ALWAYS encrypts at rest — "UNENCRYPTED" means no customer KMS
  control, not plaintext.** The default SSEType AES256 uses an AWS-owned key
  with no CloudTrail Decrypt events, no key policy, no rotation visibility. For
  compliance (PCI-DSS req 3.4, HIPAA §164.312(a)(2)(iv), SOC2 CC6.1), this is a
  finding. Do NOT tell the operator "your data is plaintext" — it is not. Tell
  them they have no audit trail or control over the encryption key.

- **PITR and AWS Backup are different recovery mechanisms.** PITR
  (ContinuousBackupsStatus: ENABLED) provides a 35-day continuous replay — you
  can restore to any second within the window. AWS Backup takes scheduled
  snapshots at intervals you define. A table with AWS Backup but no PITR cannot
  recover data written and then accidentally deleted between snapshots. They
  are complementary, not substitutive.

- **GSI throttling cascades to the base table.** A GSI with insufficient RCUs
  causes `ProvisionedThroughputExceededException` on writes to the BASE TABLE —
  even if the base table has ample capacity. DynamoDB enforces GSI consistency
  by throttling base-table writes when any GSI falls behind. A PROVISIONED
  table with autoscaling on the base table but NOT on a GSI is a
  CAPACITY_MISMATCH — the GSI is the throttle origin.

- **LSI 10 GB per-partition limit is a silent failure.** An LSI has a hard 10
  GB-per-partition size limit. When exceeded, writes to items in that partition
  are silently rejected with no CloudWatch alarm (unless you build one). The
  base table has no analogous limit. Flag LSI presence as a CONFIG_GAP on
  growing tables — the operator must monitor per-partition index size.

- **LSI can ONLY be created at table creation time.** You cannot add an LSI to
  an existing table — this is a hard API constraint. If a table has zero LSIs
  and the workload needs a new alternate key, the operator must create a new
  table and migrate. This makes LSI absence (or insufficiency) an architectural
  concern, not an operational fix.

- **GSI quota: 20 per table (soft limit), LSI: 5 per table (HARD limit).** The
  20-GSI soft limit can be raised via a support ticket. The 5-LSI hard limit
  cannot be increased — it is enforced at the API level. A table at 18 GSIs is
  approaching the soft ceiling and should be flagged as CONFIG_GAP.

- **TTL is not real-time deletion.** TTL items are deleted by a background
  scanner within **48 hours** of the expiry timestamp. Items remain readable
  and queryable until physically deleted. For GDPR / data-retention compliance,
  you cannot rely on TTL for immediate data deletion — it is a cost-optimization
  feature, not a compliance enforcement mechanism.

- **On-demand burst capacity is finite.** On-demand mode allocates burst
  capacity based on the trailing 30 minutes of traffic (the "burst bucket"). A
  cold-start spike from zero traffic can still throttle if the burst bucket is
  empty. On-demand is NOT "instant unlimited" — it is "instant for recent
  traffic levels."

- **Provisioned autoscaling has a 3-5 minute reaction lag.** Target-tracking
  autoscaling uses a CloudWatch alarm with a 2-minute evaluation period plus a
  warm-up window. For sub-minute traffic spikes, PROVISIONED + autoscaling
  will throttle before scaling completes. On-demand is the correct choice for
  unpredictable burst patterns.

- **SSE-KMS with a customer CMK adds a KMS dependency cascade.** Every
  DynamoDB operation with SSE-KMS involves a KMS Decrypt call (cached for ~5
  minutes via data-key reuse). If KMS throttles or the key is disabled, all
  DynamoDB operations on the table fail. AWS-managed keys (`alias/aws/dynamodb`)
  have higher service quotas and DynamoDB manages the lifecycle internally — but
  give you no policy control. This is the trade-off the operator must
  understand.

- **PITR restore creates a NEW table, not a rewind.** `RestoreTableToPointInTime`
  creates a new table — it cannot overwrite the original. The restored table
  inherits schema and indexes from the source but gets DEFAULT capacity settings
  (you must reconfigure capacity after restore). Plan for application cutover:
  update endpoints, validate data, then delete the old table.

- **BillingMode switch has a cooldown.** You can switch between PROVISIONED and
  PAY_PER_REQUEST, but DynamoDB enforces a cooldown (~minutes) between switches.
  Frequent switching for cost optimization does not work — DynamoDB prevents
  capacity-gaming. Choose a mode based on traffic profile, not per-request cost.

- **DeletionProtectionEnabled is the last line of defense.** When true, the
  table cannot be deleted via `delete-table` — the API returns
  `ResourceInUseException`. This protects against accidental deletion and
  ransomware scenarios. Added in November 2023 — many legacy tables predate it.

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

The MANDATORY CONFIRMATION GATE is defined at the top of this document and
applies to every action below. Beyond the gate, these DynamoDB-specific
preconditions must hold before invoking the CLI:

- **Capture current table config before enabling SSE-KMS.** Enabling SSE on a
  table that previously had AES256 re-encrypts all existing data — this is a
  background migration that takes time proportional to table size. For large
  tables, monitor the migration via `describe-table` (SSEDescription.Status
  transitions DISABLED → ENABLING → ENABLED).

- **Verify the CMK exists and is enabled** before referencing it in
  `update-table`. A disabled or pending-deletion key causes the update to fail
  or leaves the table in an inaccessible state. Check with:
  `aws kms describe-key --key-id <cmk-id> --output json`.

- **Before switching from PROVISIONED to PAY_PER_REQUEST**, warn the operator
  about cost implications. On-demand for a steady high-throughput workload
  costs 3-5x provisioned with autoscaling. Verify the traffic profile justifies
  the switch.

- **Before enabling PITR**, warn about storage cost. PITR consumes additional
  storage proportional to the change rate over 35 days. For write-heavy tables,
  this can be significant. The compliance/recovery benefit typically outweighs
  the cost, but the operator should be informed.

- Prefer additive/non-destructive changes (enable SSE, enable PITR, enable
  deletion protection) over destructive ones (delete GSI, switch billing mode).
  Additive changes are reversible; destructive ones may break workloads.

## Remediation guidance

### For UNENCRYPTED — SSE disabled (Step 1)

1. Enable SSE-KMS with a customer-managed CMK:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --sse-specification Enabled=true,SSEType=KMS,\
KMSMasterKeyId=arn:aws:kms:us-east-1:111111111111:key/<cmk-id> \
     --profile <p>
   ```
2. Monitor the encryption migration: SSEDescription.Status transitions
   DISABLED → ENABLING → ENABLED. The table remains available during migration.
3. Verify: `aws dynamodb describe-table --table-name <table> --output json |
   jq '.Table.SSEDescription'`.

### For NO_PITR — continuous backups disabled (Step 2)

1. Enable PITR:
   ```bash
   aws dynamodb update-continuous-backups --table-name <table> \
     --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
     --profile <p>
   ```
2. Verify:
   ```bash
   aws dynamodb describe-continuous-backups --table-name <table> --profile <p>
   ```
3. Document the 35-day recovery window for the operator. Note that PITR restore
   creates a NEW table — plan for application cutover.

### For CAPACITY_MISMATCH — provisioned without autoscaling (Step 3)

1. Register scalable targets for the table:
   ```bash
   aws application-autoscaling register-scalable-target \
     --service-namespace dynamodb \
     --resource-id table/<table> \
     --scalable-dimension dynamodb:table:ReadCapacityUnits \
     --min-capacity 5 --max-capacity 1000 \
     --profile <p>
   aws application-autoscaling register-scalable-target \
     --service-namespace dynamodb \
     --resource-id table/<table> \
     --scalable-dimension dynamodb:table:WriteCapacityUnits \
     --min-capacity 5 --max-capacity 1000 \
     --profile <p>
   ```
2. Attach target-tracking policies:
   ```bash
   aws application-autoscaling put-scaling-policy \
     --policy-name <table>-read-autoscaling \
     --service-namespace dynamodb \
     --resource-id table/<table> \
     --scalable-dimension dynamodb:table:ReadCapacityUnits \
     --policy-type TargetTrackingScaling \
     --target-tracking-scaling-policy-configuration \
       '{"TargetValue":70.0,"PredefinedMetricSpecification":\
{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}' \
     --profile <p>
   ```
3. Repeat for EVERY GSI:
   `--resource-id table/<table>/index/<gsi-name>` with
   `--scalable-dimension dynamodb:index:ReadCapacityUnits` (and Write). A GSI
   without autoscaling is the most commonly missed cascade vector.
4. Alternatively, switch to on-demand if traffic is unpredictable:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --billing-mode PAY_PER_REQUEST --profile <p>
   ```

### For CONFIG_GAP — AWS-managed KMS key

1. Switch to a customer-managed CMK:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --sse-specification Enabled=true,SSEType=KMS,\
KMSMasterKeyArn=arn:aws:kms:us-east-1:111111111111:key/<cmk-id> \
     --profile <p>
   ```

### For CONFIG_GAP — TTL disabled

1. Enable TTL on an attribute:
   ```bash
   aws dynamodb update-time-to-live --table-name <table> \
     --time-to-live-specification Enabled=true,AttributeName=ttl \
     --profile <p>
   ```
2. Verify existing items have the TTL attribute set (epoch seconds). Items
   without the attribute are never expired.

### For CONFIG_GAP — deletion protection off

1. Enable deletion protection:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --deletion-protection-enabled --profile <p>
   ```

### For CONFIG_GAP — no DynamoDB Streams

1. Enable streams:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
     --profile <p>
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend verifying Global Table replicas independently (each replica has
   independent capacity, PITR, and KMS settings).
3. Recommend adding AWS Backup as a complementary layer to PITR for long-term
   retention (PITR caps at 35 days; AWS Backup provides weekly/monthly archives).

## Deep reference: DynamoDB capacity and recovery internals

### On-demand burst capacity

On-demand mode maintains a burst capacity bucket sized to the trailing
30-minute traffic average × 5 (approximately). A table that sustains 1,000
RCU/sec builds a burst bucket of ~5,000 RCU/sec for short spikes. A cold-start
table (zero recent traffic) has an empty burst bucket — the first spike may
throttle while DynamoDB warms up. This is why on-demand is NOT recommended for
traffic patterns with prolonged zero-then-spike cycles (e.g., a batch job that
runs once per hour).

### Provisioned autoscaling timing

Target-tracking autoscaling evaluates a CloudWatch alarm every 1 minute with a
2-minute evaluation period. When the alarm fires (utilization > target for 2
consecutive minutes), autoscaling issues a scale-out. The new capacity takes
effect within seconds of the API call, but the alarm → evaluation → action
pipeline takes 3-5 minutes. For traffic spikes that ramp faster than 3 minutes,
PROVISIONED + autoscaling will throttle before scaling completes.

### PITR restore mechanics

`RestoreTableToPointInTime` creates a new table from the source table's
continuous backup. Key constraints:

- The restored table name must be unique (cannot overwrite the source).
- The restored table gets DEFAULT capacity settings — not the source's settings.
  You must reconfigure capacity (or switch to on-demand) after restore completes.
- The restore is asynchronous — large tables take minutes to hours depending
  on size. The table is not available until `TableStatus` transitions from
  `RESTORING` to `ACTIVE`.
- Indexes (GSI/LSI) from the source are recreated on the restored table.

### GSI write-capacity model

A GSI in PROVISIONED mode has its own RCU/WCU allocation, separate from the
base table. DynamoDB asynchronously replicates base-table writes to the GSI
using the GSI's WCU. If the GSI's WCU is insufficient, the replication falls
behind, and DynamoDB throttles base-table writes to prevent unbounded GSI lag.
This is why GSI autoscaling is not optional in PROVISIONED mode — it is the
only way to prevent cascade throttling under variable write load.

### SSE-KMS data-key caching

When SSE-KMS is enabled, DynamoDB generates a data key per partition via KMS
`GenerateDataKey` and caches it for approximately 5 minutes. Within the cache
window, no KMS API call is needed. After the cache expires, DynamoDB calls KMS
again. This means:

- KMS API rate limits apply: a table with thousands of active partitions can
  generate significant KMS traffic. Customer-managed CMKs share the account's
  KMS rate quota; AWS-managed keys (`aws/dynamodb`) have a dedicated quota.
- KMS key disablement takes 5 minutes to take effect on DynamoDB (the cache
  window). Plan for this delay when rotating or disabling keys.

## Domain

AWS CloudOps / DynamoDB Table Hardening & Compliance.
