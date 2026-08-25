---
name: s3-glacier-restore-operator
description: Operates S3 Glacier restore workflows — initiates object restores from Flexible Retrieval tiers (Expedited 1-5 min, Standard 3-5 hr, Bulk 5-12 hr) and from Deep Archive (12-48 hr; Bulk 12 hr), provisions Expedited capacity to guarantee throughput, manages in-place restore vs copy-to-other-tier strategies, performs bulk restores via S3 Batch Operations (manifest + role + report), checks restore status via head-object Restore field and restore-object waiters, integrates with lifecycle policies (Transition + NoncurrentVersionTransition), and operates latest features (S3 Glacier Instant Retrieval for ms-latency access on cold data, Deep Archive bulk restore cost-tier). Emits a deterministic execution plan with pre-checks, CONFIRM gate, and post-verification. Use when restoring a single object, a prefix, or a manifest of thousands of objects from Glacier; provisioning Expedited capacity; running a DR restore drill; or diagnosing a stalled restore job.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live-account operations use aws s3api restore-object, head-object, get-object, list-objects-v2, aws s3api wait object-restored, aws s3control create-job (Batch Operations), describe-job, get-job-tagging, and aws s3api put-bucket-lifecycle-configuration (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Restoring a single object, prefix, or manifest of objects from S3 Glacier Flexible Retrieval, Glacier Deep Archive, or Glacier Instant Retrieval; choosing between Expedited / Standard / Bulk tiers; provisioning Expedited capacity for guaranteed throughput; running a DR restore drill with an RTO target; orchestrating a bulk restore via S3 Batch Operations; checking restore status via head-object Restore field; reconciling restore in place vs copy-to-different-tier; integrating restores with lifecycle policies; or diagnosing a stalled restore job.
  activation_triggers: restore object from Glacier, S3 Glacier restore, expedited retrieval, standard retrieval, bulk retrieval, Deep Archive restore, Glacier Instant Retrieval, provisioned capacity, bulk restore via Batch Operations, manifest restore, restore drill, DR restore from Glacier, head-object Restore field, stalled restore job, lifecycle policy integration, copy to different storage class
  invocation_schema: 'Input shape (one of): (a) a restore specification including the bucket, key (or prefix, or manifest), source storage class (Glacier Flexible Retrieval | Glacier Deep Archive | Glacier Instant Retrieval), retrieval tier (Expedited | Standard | Bulk), target destination (in-place | copy-to-bucket | copy-to-tier), and RTO budget; (b) a partial spec for interactive refinement (e.g., "restore this prefix from Glacier, urgent"); (c) an existing job ID for status check or diagnosis. Output shape: { OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, STATE, NOTES } where VERDICT ∈ { READY, BLOCKED, COMPLETED, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3 Glacier, S3 Glacier Flexible Retrieval, S3 Glacier Deep Archive, S3 Glacier Instant Retrieval, restore-object, Expedited retrieval, Standard retrieval, Bulk retrieval, provisioned capacity, S3 Batch Operations, bulk restore, restore in place, copy to different tier, head-object Restore field, RestoreObject, lifecycle policy, Transition, NoncurrentVersionTransition, DR restore drill, manifest restore, Glacier Instant Retrieval, Deep Archive bulk restore
  tags: s3, storage, operate, glacier, restore, deep-archive, instant-retrieval, batch-operations, lifecycle, expedited, provisioned-capacity
---

# S3 Glacier Restore Operator

## Mindset

**One-line takeaway:** a Glacier restore is NOT a download — it is a
**state transition** that lifts an object from a frozen archive tier
back into Standard (or another hot tier) for a configurable number
of days. The object does not move on its own; you request the
restore, wait the tier-specific duration, then the temporary restored
copy is readable until the restore window expires, after which the
object falls back to archive. The restore window is a lease, not a
promotion — permanent promotion requires an explicit copy or
lifecycle-policy change.

Three facts make Glacier restore operations different from "just
calling GetObject":

- **Retrieval tier determines the SLA, not the storage class.** The
  source storage class (Glacier Flexible Retrieval, Deep Archive,
  Glacier Instant Retrieval) constrains which tiers are available;
  the chosen tier controls the wait. Expedited = 1-5 min (Flexible
  only, requires capacity). Standard = 3-5 hr (Flexible). Bulk =
  5-12 hr (Flexible) or 12 hr (Deep Archive). Deep Archive does NOT
  support Expedited or Standard. Mismatching tier and source class
  is the #1 cause of restore failures.

- **Glacier Instant Retrieval does NOT require a restore.** Objects
  in the Glacier Instant Retrieval (GIR) storage class are directly
  accessible via GetObject with single-digit-ms latency for
  infrequent access. Calling `restore-object` on a GIR object is a
  no-op (or an error depending on bucket config). The single most
  common misclassification is treating GIR like Flexible Retrieval.

- **Restore in place is a temporary lease.** `restore-object` with
  `Days=N` makes the object readable for N days, then it reverts to
  archive. For permanent migration out of Glacier, copy the object
  to the target storage class explicitly
  (`copy-object` with `StorageClass` override) or update the bucket
  lifecycle policy. Drift between operator expectations ("we restored
  it, it's done") and the lease model is the #1 DR-drill failure.

## Quick navigation

| Section | Purpose |
|---|---|
| Pre-flight gate | Validate object state, IAM perms, capacity |
| Quick reference — restore tiers | Tier SLA matrix at a glance |
| Tier selection decision tree | Match RTO to tier |
| Step-by-step process | Pre-checks → restore → verify → cleanup |
| Bulk restore via Batch Operations | Manifest-driven workflows |
| STRICT output contract | Required VERDICT block schema |
| NEVER (top 5) | Highest-blast-radius mistakes |
| Expert heuristic | Field craft for ambiguous cases |
| Edge-case handling | Stalls, expirations, versioning |
| Remediation | Recover from mis-tiered or stalled restores |

## Quick reference — restore tiers and SLAs

| Source storage class | Available tiers | Tier SLA | Cost marker |
|---|---|---|---|
| Glacier Instant Retrieval (GIR) | (none — direct GetObject) | ms latency | retrieve free (pay per-GB retrieved already) |
| Glacier Flexible Retrieval | Expedited | 1-5 min | highest |
| Glacier Flexible Retrieval | Standard | 3-5 hr | medium |
| Glacier Flexible Retrieval | Bulk | 5-12 hr | lowest |
| Glacier Deep Archive | Standard | 12 hr | medium |
| Glacier Deep Archive | Bulk | 48 hr | lowest |

Notes:
- **Expedited requires capacity.** Without provisioned capacity,
  Expedited requests can be queued or rejected during demand peaks.
  Provision 1+ capacity units per region for guaranteed Expedited.
- **Deep Archive Standard is the FAST tier for Deep Archive** (12
  hr). Bulk is 48 hr. Deep Archive does NOT support Expedited.
- **Bulk is cheapest, slowest.** Use for non-urgent batch restores
  (compliance export, monthly reporting).
- **GIR restore is a misnomer** — GIR is directly readable. Calls
  to `restore-object` on GIR are unnecessary.

## Pre-flight: restore specification gate

Run before producing the execution plan. Several requirements **block
the operation** — proceeding produces silent failures or unnecessary
Expedited spend.

**Live-account pre-flight checks (skip if doing offline plan
authoring):**
1. Verify object storage class via `head-object`:
   `aws s3api head-object --bucket <bucket> --key <key> --query 'StorageClass'`
   — confirms whether the object is actually archived (Glacier
   Flexible Retrieval, Deep Archive) or already directly accessible
   (Standard, Intelligent-Tiering, GIR, One-Zone IA).
2. Verify the object is in `ArchiveStatus: ARCHIVE_ACCESS` or
   `DEEP_ARCHIVE_ACCESS` (otherwise no restore needed).
3. Verify IAM permissions for `s3:RestoreObject`, `s3:GetObject`,
   `s3:HeadObject`, and (for copy-to-tier) `s3:PutObject` /
   `s3:CopyObject` / `s3:AbortMultipartUpload`.
4. For Expedited, verify provisioned capacity:
   `aws s3control describe-job` is not the right call — use
   `aws s3api list-buckets` and consult billing for current capacity
   units (currently no direct CLI for capacity check; verify via
   console or billing).
5. For S3 Batch Operations, verify the manifest bucket, the
   IAM role with `s3:RestoreObject` plus `iam:PassRole`, and the
   report bucket all exist.
6. For a DR drill, capture the current timestamp and the RTO target
   for post-verification.

| Attribute | Value | Effect on plan |
|---|---|---|
| StorageClass | Glacier Instant Retrieval | NO RESTORE NEEDED — direct GetObject works. |
| StorageClass | Glacier Flexible Retrieval | Tier choice: Expedited / Standard / Bulk. |
| StorageClass | Glacier Deep Archive | Tier choice: Standard (12hr) / Bulk (48hr). NO Expedited. |
| ArchiveStatus | ARCHIVE_ACCESS | Restore required. |
| ArchiveStatus | DEEP_ARCHIVE_ACCESS | Restore required (Deep Archive). |
| Restore field present | ongoing-request="false", expiry-date=<date> | Already restored; skip new restore. |
| Restore field present | ongoing-request="true" | Restore in progress; do NOT re-issue (resets wait clock). |
| Target | in-place | RestoreObject with Days=N. |
| Target | copy-to-bucket | RestoreObject then CopyObject. |
| Target | copy-to-tier (promotion) | CopyObject with StorageClass override (no restore-object needed if source is GIR). |
| Manifest size | >1000 objects | Use S3 Batch Operations, not inline loop. |

**If the spec is incomplete** (missing bucket, key/manifest, tier
selection, or target destination), output:

```text
OPERATION: <restore-object | bulk-restore | check-status | diagnose>
VERDICT: BLOCKED
TARGET: <bucket/key or unknown>
REASON: Restore specification is missing required fields (<list>).
Cannot produce an execution plan without <field> — the resulting
restore would either fail or incur unnecessary Expedited spend.
REQUIRED:
  - bucket
  - key | prefix | manifest
  - source_storage_class (Glacier Flexible Retrieval | Deep Archive |
                           Glacier Instant Retrieval)
  - tier (Expedited | Standard | Bulk)
  - target (in-place | copy-to-bucket | copy-to-tier)
  - days (for in-place restore; lease duration)
```

## Tier selection decision tree

| RTO budget | Source class | Recommended tier | Cost marker |
|---|---|---|---|
| < 5 min | Flexible Retrieval | Expedited (+ provisioned capacity) | highest |
| < 5 min | Deep Archive | NOT POSSIBLE — Deep Archive cannot be Expedited | n/a |
| < 5 min | Glacier Instant Retrieval | direct GetObject (no restore) | free |
| < 6 hr | Flexible Retrieval | Standard | medium |
| < 6 hr | Deep Archive | Standard (12 hr — EXCEEDS RTO; renegotiate) | medium |
| < 12 hr | Flexible Retrieval | Standard or Bulk | medium/low |
| < 12 hr | Deep Archive | Standard (12 hr) | medium |
| < 48 hr | Deep Archive | Bulk (48 hr) | lowest |
| < 12 hr | Flexible Retrieval | Bulk (5-12 hr) | lowest |

**Expert heuristic:** if the RTO cannot accommodate the tier's
maximum SLA, BLOCK the operation. A 12-hour SLA tier is NOT a
6-hour SLA tier; restoring and hoping is a guaranteed DR-drill
failure.

## Process — Pre-checks → restore → verify (in order)

### Step 0: Expert heuristic — field craft for ambiguous cases

- **If the user does not know the source storage class → call
  `head-object` first.** Never request a restore without confirming
  StorageClass and ArchiveStatus. Restoring a GIR object is a no-op;
  restoring a Standard object returns an error; restoring an
  already-restored object resets the wait clock.

- **If the restore seems "stuck" → check `head-object` Restore
  field, not the Job ID.** Restore-object does NOT return a Job ID
  (unlike Batch Operations). The only status source is the Restore
  field on the object's metadata:
  `ongoing-request="true"` (in progress) or `ongoing-request="false"`
  with `expiry-date` (complete).

- **If Batch Operations job is `Active` for hours → check the
  manifest, not the job.** The job reports Active while the manifest
  is being processed. Failures are in the job report (CompletionReport
  bucket), not the job status. A common foot-gun: the manifest
  contains keys that no longer exist; the job marks them Failed but
  stays Active until full manifest iteration.

- **If Expedited requests are being rejected → provision capacity.**
  On-demand Expedited is best-effort and can be rejected during
  demand peaks. Provisioned capacity guarantees 3 retrieval
  requests/min or 150 MB/min per unit. Pre-provision for DR drills.

- **If the user wants a "permanent restore" → recommend copy-to-tier,
  not Days=N.** Days=N is a lease; the object reverts to archive
  when the window expires. For permanent promotion out of archive,
  copy the restored object to a hot storage class (Standard or
  Intelligent-Tiering) or update the lifecycle policy.

### Step 1: Confirm source storage class and restore state

```bash
aws s3api head-object --bucket <bucket> --key <key> \
  --query '{StorageClass: StorageClass, ArchiveStatus: ArchiveStatus, Restore: Restore}'
```

Interpretation:
- `StorageClass: GLACIER` (Flexible Retrieval, formerly GLACIER),
  `DEEP_ARCHIVE`, or `GLACIER_IR`.
- `ArchiveStatus: ARCHIVE_ACCESS` or `DEEP_ARCHIVE_ACCESS` → restore
  is required.
- `Restore: { ongoing-request: false, expiry-date: <date> }` →
  already restored; expires on `<date>`.
- `Restore: { ongoing-request: true }` → restore in progress.

### Step 2: Select the tier (per the decision tree)

Match RTO to tier. Mismatches are the most common failure mode.

### Step 3: Restore in place (single object)

```bash
aws s3api restore-object \
  --bucket prod-archive-bucket \
  --key quarterly-report-2025-Q1.parquet \
  --restore-request '{"Days": 7, "GlacierJobParameters": {"Tier": "Expedited"}}'
```

For Bulk on Flexible Retrieval:
```bash
--restore-request '{"Days": 30, "GlacierJobParameters": {"Tier": "Bulk"}}'
```

For Deep Archive (Standard tier, 12hr):
```bash
--restore-request '{"Days": 30, "GlacierJobParameters": {"Tier": "Standard"}}'
```

Note: Deep Archive supports only `Standard` (12hr) and `Bulk` (48hr).
Expedited on Deep Archive returns an error.

### Step 4: Wait for restore completion

```bash
aws s3api wait object-restored --bucket prod-archive-bucket \
  --key quarterly-report-2025-Q1.parquet
```

The waiter polls `head-object` until `Restore.ongoing-request=false`.
For Bulk + Deep Archive, this can be 48 hours — set expectations.

### Step 5: Read the restored object (or copy to a different tier)

```bash
# Read in place
aws s3api get-object --bucket prod-archive-bucket \
  --key quarterly-report-2025-Q1.parquet /tmp/restored.parquet

# Or copy to a hot tier for permanent promotion
aws s3api copy-object --bucket prod-hot-bucket \
  --key quarterly-report-2025-Q1.parquet \
  --copy-source prod-archive-bucket/quarterly-report-2025-Q1.parquet \
  --storage-class STANDARD
```

### Step 6: Verify post-restore state

```bash
aws s3api head-object --bucket prod-archive-bucket \
  --key quarterly-report-2025-Q1.parquet \
  --query 'Restore'
# Expected: ongoing-request=false, expiry-date populated
```

For copy-to-tier:
```bash
aws s3api head-object --bucket prod-hot-bucket \
  --key quarterly-report-2025-Q1.parquet \
  --query 'StorageClass'
# Expected: STANDARD
```

### Step 7: Document the lease expiration

Capture the `expiry-date` in the operation notes. Operators who
assume a restore is permanent are surprised when access disappears
on day N+1.

## Bulk restore via S3 Batch Operations

For manifests of >1000 objects, use S3 Batch Operations instead of
inline loops. The manifest, IAM role, and report bucket must exist
before job creation.

### Step B1: Author the manifest

```csv
bucket,key
prod-archive-bucket,reports/2025/Q1.parquet
prod-archive-bucket,reports/2025/Q2.parquet
...
```

Upload to a manifest bucket:
```bash
aws s3 cp manifest.csv s3://batch-ops-manifests/restore-2025-Q1.csv
```

### Step B2: Author the IAM role

The role needs `s3:RestoreObject` on the target bucket(s),
`s3:GetObject` on the manifest bucket, and `iam:PassRole` on the
caller:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:RestoreObject", "s3:GetObject"],
     "Resource": ["arn:aws:s3:::prod-archive-bucket/*"]},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:GetBucketLocation"],
     "Resource": ["arn:aws:s3:::batch-ops-manifests/*"]},
    {"Effect": "Allow", "Action": ["s3:PutObject"],
     "Resource": ["arn:aws:s3:::batch-ops-reports/*"]}
  ]
}
```

### Step B3: Create the Batch Operations job

```bash
aws s3control create-job \
  --account-id 111111111111 --priority 1 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchRestoreRole \
  --operation '{"S3RestoreObject": {"Days": 7, "GlacierJobParameters": {"Tier": "Bulk"}}}' \
  --manifest '{"Spec": {"Format": "S3BatchOperations_CSV_20180820"}, "Location": {"ObjectArn": "arn:aws:s3:::batch-ops-manifests/restore-2025-Q1.csv", "ETag": "<etag>"}}' \
  --report "{\"Bucket\":\"arn:aws:s3:::batch-ops-reports\",\"Prefix\":\"restore-2025-Q1/\",\"Format\":\"Report_CSV_20180820\",\"ReportScope\":\"AllTasks\",\"Enabled\":true}" \
  --description "Bulk restore Q1 reports from Glacier Flexible Retrieval (Bulk tier)"
```

The returned `JobId` is the only restore workflow handle that
returns a Job ID.

### Step B4: Monitor and review

```bash
aws s3control describe-job --account-id 111111111111 --job-id <JobId> \
  --query 'Job.{Status:Status,Progress:ProgressSummary}'
# Expected terminal: Complete | Cancelled | Failed | Paused
```

The completion report (CSV in the report bucket) lists each task
with `TaskStatus` (Succeeded | Failed | NoSuchKey) and failure
codes — use it to drive re-run decisions.

## Restore in place vs copy to different tier

| Decision | Use case |
|---|---|
| Restore in place (Days=N) | Temporary access — audit, investigation, one-off query. Object reverts to archive after N days. |
| Copy to bucket | Move restored data to a working bucket while keeping the archive intact. |
| Copy to tier (promotion) | Permanent migration out of archive — change storage class on the copy. Update lifecycle policy to prevent re-archival. |
| Lifecycle policy update | Bulk promotion — modify the lifecycle rule that archived the object in the first place. |

**Permanent promotion requires either a copy or a lifecycle-policy
change.** Restore-object alone never changes the object's storage
class permanently.

## Lifecycle integration

If the bucket has a lifecycle rule that transitions objects to
Glacier, restored objects are still subject to that rule — they may
re-archive after the lifecycle trigger fires. To prevent re-archival
of permanently-promoted objects:

1. Update the lifecycle rule with a filter (prefix/tag) that
   excludes the promoted objects.
2. Or copy the promoted objects to a different bucket without the
   archive rule.

```bash
# Lifecycle rule to disable archiving for promoted prefix
aws s3api put-bucket-lifecycle-configuration \
  --bucket prod-archive-bucket \
  --lifecycle-configuration file://lifecycle-with-filter.json
```

```json
{
  "Rules": [
    {
      "ID": "archive-after-90d",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]
    }
  ]
}
```

Objects under `promoted/` are NOT subject to this rule and stay in
Standard.

## Output format — STRICT output contract

The output MUST follow this exact schema. Every field is required;
do not omit fields or add undocumented ones.

```text
OPERATION: <restore-object | bulk-restore | check-status | diagnose | copy-to-tier>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <bucket/key or job-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <restore progress, job status, expiry date>
NOTES: <lease caveat, tier rationale, lifecycle interaction, RTO reconciliation>
```

### Worked example — single Expedited restore

```text
OPERATION: restore-object
VERDICT: READY
TARGET: prod-archive-bucket/quarterly-report-2025-Q1.parquet
PRE_CHECKS:
  - [PASS] head-object StorageClass: GLACIER (Flexible Retrieval)
  - [PASS] ArchiveStatus: ARCHIVE_ACCESS (restore required)
  - [PASS] Restore field absent (no in-progress restore)
  - [PASS] Caller IAM role holds s3:RestoreObject, s3:GetObject
  - [PASS] Provisioned capacity: 1 unit (guarantees Expedited)
  - [PASS] RTO 5 min accommodated by Expedited (1-5 min SLA)
STEPS:
  1. CONFIRM: About to restore-object prod-archive-bucket/
     quarterly-report-2025-Q1.parquet via Expedited tier (1-5 min
     SLA). Restore window: 7 days. Provisioned capacity: 1 unit.
     Proceed? (yes/no)
  2. aws s3api restore-object --bucket prod-archive-bucket
     --key quarterly-report-2025-Q1.parquet
     --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Expedited"}}'
  3. aws s3api wait object-restored --bucket prod-archive-bucket
     --key quarterly-report-2025-Q1.parquet
POST_VERIFY:
  - [PASS] head-object Restore.ongoing-request: false
  - [PASS] head-object Restore.expiry-date populated
STATE: restored — lease expires 2026-08-17T00:00:00Z
NOTES:
  - Restore is a temporary lease. Object reverts to Glacier Flexible
    Retrieval on expiry-date. For permanent promotion, copy to
    STANDARD via copy-object.
```

### Worked example — Batch Operations bulk restore

```text
OPERATION: bulk-restore
VERDICT: COMPLETED
TARGET: batch-ops job 1234abcd-...
PRE_CHECKS:
  - [PASS] Manifest uploaded to batch-ops-manifests (10000 keys)
  - [PASS] IAM role S3BatchRestoreRole has s3:RestoreObject on
    prod-archive-bucket
  - [PASS] Report bucket batch-ops-reports exists
  - [PASS] All manifest keys verified in head-object sampling
STEPS:
  1. aws s3control create-job (Bulk tier, Days=30)
  2. aws s3control describe-job --job-id 1234abcd-...
POST_VERIFY:
  - [PASS] Job Status: Complete
  - [PASS] ProgressSummary.TotalTasks: 10000
  - [PASS] ProgressSummary.NumberSucceeded: 9998
  - [WARN] ProgressSummary.NumberFailed: 2 (NoSuchKey — see report)
STATE: complete — 9998 objects restored, 2 NoSuchKey failures in
       s3://batch-ops-reports/restore-2025-Q1/
NOTES:
  - Bulk tier SLA: 5-12 hr. Actual elapsed: 8.2 hr.
  - Re-run failed tasks with a filtered manifest if needed.
  - All restored objects revert to archive after 30 days.
```

## Verification commands

```bash
# Single object restore status
aws s3api head-object --bucket <bucket> --key <key> --query 'Restore'

# Wait for restore completion (single object)
aws s3api wait object-restored --bucket <bucket> --key <key>

# Batch Operations job status
aws s3control describe-job --account-id <account> --job-id <job-id> \
  --query 'Job.{Status:Status,Progress:ProgressSummary}'

# List Batch Operations jobs in an account
aws s3control list-jobs --account-id <account> --operation S3RestoreObject

# Verify object is readable after restore
aws s3api get-object --bucket <bucket> --key <key> /tmp/test.out && echo OK

# Verify lifecycle rule will not re-archive promoted objects
aws s3api get-bucket-lifecycle-configuration --bucket <bucket>
```

## Anti-Patterns — NEVER (top 5)

- **NEVER call `restore-object` on a Glacier Instant Retrieval (GIR)
  object.** GIR objects are directly readable via GetObject with
  single-digit-ms latency. A restore call is a no-op (or an error
  depending on bucket config). Always check `StorageClass` via
  `head-object` before requesting a restore.

- **NEVER request Expedited tier on a Deep Archive object.** Deep
  Archive supports only Standard (12 hr) and Bulk (48 hr). Expedited
  requests on Deep Archive return an error. The fastest Deep
  Archive restore is 12 hours — never promise faster.

- **NEVER assume `restore-object` returns a Job ID.** Only S3 Batch
  Operations returns a Job ID. Single-object restores have no Job
  ID; the only status source is the Restore field on the object's
  metadata (`head-object`). Operators tracking a non-existent Job ID
  waste hours searching for status.

- **NEVER issue a second `restore-object` while one is in progress.**
  Re-issuing resets the wait clock and can change the tier mid-flight.
  Always check `head-object Restore.ongoing-request` first — if
  `true`, wait for completion before issuing any new restore request.

- **NEVER assume a restore is permanent.** Restore-object with
  `Days=N` is a lease. The object reverts to archive on day N+1.
  Permanent promotion requires a copy-object to a hot storage class
  OR a lifecycle-policy update. DR drills that assume a restored
  object stays restored fail when access disappears.

## Additional NEVER

- NEVER use on-demand Expedited for DR drills without provisioned
  capacity. On-demand is best-effort and is rejected during demand
  peaks — exactly when DR drills happen. Pre-provision capacity.
- NEVER request Bulk when the RTO requires <12 hr. Bulk SLA is
  5-12 hr (Flexible) or 48 hr (Deep Archive). Use Standard or
  Expedited instead.
- NEVER update a lifecycle policy without checking which objects
  will be affected. A broad `Transition` rule can re-archive
  promoted objects, undoing the restore.
- NEVER delete the manifest or report bucket mid-job. Batch
  Operations reads the manifest continuously; the report is the
  only audit trail for `NoSuchKey` failures.
- NEVER treat `ongoing-request: false` as success — it only means
  the restore is no longer in progress. Always verify `expiry-date`
  is populated and the object is readable via `get-object`.
- NEVER run Batch Operations with the management account's
  credentials. Use a scoped IAM role (`s3:RestoreObject`,
  `s3:GetObject`, `iam:PassRole` on the job role ARN).

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`restore-object`, `create-job`,
  `put-bucket-lifecycle-configuration`), the operator MUST emit:
  `CONFIRM: About to restore <bucket>/<key> via <tier> (SLA: <min
  to max>). Restore window: <N> days. Estimated cost: <$X>. Object
  reverts to <storage class> on expiry. Proceed? (yes/no)`

- **Tier-vs-source-class compatibility.** Expedited only on
  Flexible Retrieval. Standard on Flexible (3-5hr) and Deep Archive
  (12hr). Bulk on Flexible (5-12hr) and Deep Archive (48hr). GIR
  requires no restore.

- **RTO reconciliation.** The maximum SLA for the chosen tier MUST
  fit within the user's RTO budget. If not, BLOCK and renegotiate.

- **Capacity check for Expedited.** Verify provisioned capacity
  exists before promising an Expedited SLA. On-demand is
  best-effort.

- **Cost estimate.** Emit before any restore:
  - Expedited retrieval: ~$0.03 per GB (highest)
  - Standard retrieval: ~$0.01 per GB (Flexible), ~$0.02 per GB
    (Deep Archive)
  - Bulk retrieval: ~$0.0025 per GB (Flexible), ~$0.0025 per GB
    (Deep Archive)
  - Provisioned capacity: $100 per unit per month in the region
  - Batch Operations: $0.25 per million tasks

- **Lease expiration awareness.** Capture `expiry-date` in
  post-verification. Operators who assume permanence are surprised
  when access disappears.

## Edge-case handling

- **Restore seems stuck.** Check `head-object Restore.ongoing-request`.
  If `true`, the restore is still in progress (Deep Archive Bulk can
  take 48 hours). If `false` but access fails, the restore failed
  silently — open an AWS support case.
- **Restore expires before user accesses the object.** Re-issue
  `restore-object` with a longer `Days` value, or copy to Standard
  before expiration. Update the procedure to use a longer lease.
- **Batch Operations job `Active` for hours with no progress.**
  Check the manifest ETag, the IAM role permissions, and rate
  limiting on the source bucket. The report CSV shows per-task
  failures.
- **Restoring a versioned object.** Specify `--version-id` on
  `restore-object` and `head-object`. Without it, the operation
  targets the current version, which may not be the archived one.
- **Restoring a Delete Marker.** Delete markers cannot be restored.
  Remove the delete marker first, then restore the underlying object.
- **Promotion via lifecycle.** If a lifecycle rule is the source of
  archiving, update or filter the rule to prevent re-archival of
  promoted objects. Otherwise the promotion is temporary.
- **GIR treated as Flexible Retrieval.** GIR is directly readable;
  restore-object is unnecessary. Re-classify and proceed with
  GetObject.
- **Cross-region restore.** Restores happen in the source bucket's
  region. For cross-region DR, copy the restored object to the
  destination region after restore completes.

## Remediation guidance

**Ordering principle:** verify source class first, then tier-vs-source
compatibility, then provision capacity for Expedited, then issue the
restore, then wait, then verify.

### For BLOCKED — GIR object passed for restore

1. Re-classify: GIR is directly readable.
2. Issue `aws s3api get-object` — no restore needed.
3. Update the procedure doc to call out GIR as a non-archive tier.

### For BLOCKED — Deep Archive with Expedited tier

1. Re-tier to Standard (12 hr) or Bulk (48 hr).
2. Reconcile RTO: Deep Archive cannot restore faster than 12 hr.
3. If faster restore is required, change the source storage class at
   the lifecycle-policy level.

### For stalled Batch Operations job

1. Check `describe-job` for `FailureReason`.
2. Check the report bucket CSV for `NoSuchKey` entries.
3. Re-run failed tasks with a filtered manifest.

### For unexpected re-archival after promotion

1. Check `get-bucket-lifecycle-configuration` for rules that match
   the promoted prefix or tags.
2. Update the rule filter to exclude promoted objects.
3. Re-copy the affected objects to Standard.

## Recent AWS features (2024-2026)

- **S3 Glacier Instant Retrieval (GIR) — broadly adopted 2023-2024:**
  the lowest-cost storage class with single-digit-ms latency for
  infrequent access. Directly readable via GetObject — no restore
  required. Replaces Standard-IA for cold-but-queryable data.
- **Deep Archive Bulk restore cost-tier (2024):** the Bulk tier for
  Deep Archive is the lowest-cost retrieval option (48 hr SLA,
  ~$0.0025 per GB). Use for compliance exports with no RTO pressure.
- **S3 Batch Operations enhanced reporting (2024-2025):** the
  completion report now includes per-task CloudWatch metrics
  (BytesRestored, Duration) for tighter observability of bulk
  restores.
- **S3 Storage Lens restore dashboards (2024-2025):** Storage Lens
  now surfaces restore-operation counts and elapsed-time percentiles
  per bucket — useful for tuning lifecycle policies and predicting
  restore cost.

- **Lifecycle rule validation (2024-2025):** `put-bucket-lifecycle-configuration`
  now performs stricter validation, including non-overlapping rule
  detection — catches re-archival conflicts that previously caused
  silent object churn.
- **S3 Batch Operations tag-based manifests (2025):** Batch Operations
  supports S3 Resource Tags as a manifest source in addition to CSV
  — useful for tag-driven restore workflows.
- **Intelligent-Tiering Archive configurations (2025):**
  Intelligent-Tiering exposes configurable archive-access tiers
  (Flexible vs Deep Archive) per object — restores follow the same
  tier SLAs as native Glacier classes.

## AWS documentation

- **S3 Glacier Developer Guide** — https://docs.aws.amazon.com/AmazonS3/latest/dev/glacier-restore.html
- **RestoreObject API** — https://docs.aws.amazon.com/AmazonS3/latest/API/API_RestoreObject.html
- **S3 Storage Classes** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html
- **Glacier Instant Retrieval** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-glacier
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **Batch Operations restore** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-restore-object.html
- **Lifecycle configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **Provisioned capacity** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects-retrieval-options.html
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html
- **Pricing — S3** — https://aws.amazon.com/s3/pricing/
