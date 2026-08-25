---
name: s3-batch-operations-operator
description: Operates S3 Batch Operations at scale — job creation across operation types (copy, replace tag, restore from Glacier, replicate, invoke Lambda, put ACL, put object lock retention, put legal hold), manifest formats (S3 inventory report or CSV), completion reports, job priority and rate control (RequestsPerSecond), IAM permissions (batchoperations:* plus operation-specific grants), Lambda invoke for custom per-object processing, bulk storage class transition, bulk ACL fix, bulk replication backfill, bulk decrypt + re-encrypt with new KMS key, S3 Tables Batch Operations, and large-job handling for billion-object manifests. Runs deterministic pre-checks (manifest readability, report bucket writability, IAM chain, KMS decrypt/encrypt, Lambda invoke, rate-control) behind a CONFIRM gate and emits READY, BLOCKED, or COMPLETED per job. Use when running bulk object transformations, restoring Glacier archives at scale, backfilling replication, rotating KMS keys, or invoking a custom Lambda across billions of objects.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws s3control create-job, describe-job, update-job-priority, update-job-status, aws s3api list-bucket-inventory-configurations, get-bucket-location, get-bucket-versioning, aws lambda get-policy, aws iam list-attached-role-policies / list-role-policies, aws kms describe-key / get-key-policy, and aws logs filter-log-events (AWS CLI...
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
  when_to_use: Creating an S3 Batch Operations job (copy, replace tag, restore from Glacier, replicate, invoke Lambda, put ACL, put object lock retention, put object lock legal hold), diagnosing a failed or stalled job, cancelling a runaway job, adjusting job priority or rate control, backfilling replication across existing objects, bulk-transitioning storage class, bulk-rotating KMS keys via decrypt + re-encrypt, invoking a custom Lambda across a manifest of objects, or planning a billion- object batch run with safe rate limits.
  activation_triggers: S3 Batch Operations, batch copy objects, bulk restore Glacier, bulk replace tags, batch invoke Lambda, bulk replication backfill, bulk KMS re-encrypt, bulk storage class transition, put object lock retention batch, batch operations manifest, S3 inventory manifest, CSV manifest, completion report, RequestsPerSecond batch, cancel batch job, update job priority, S3 Tables batch operations, billion objects batch
  invocation_schema: 'Input: either (a) a job specification (operation type, source bucket, manifest format and location, report bucket, IAM role ARN, operation- specific parameters, priority, rate control) for plan classification, OR (b) a JobId for live-account diagnose or cancel operations. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per job, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3 Batch Operations, create-job, manifest, S3 inventory report, CSV manifest, completion report, job priority, RequestsPerSecond, rate control, copy operation, replace tag, restore from Glacier, replicate operation, invoke Lambda, put ACL, object lock retention, object lock legal hold, bulk storage class transition, bulk ACL fix, bulk replication backfill, bulk KMS re-encrypt, S3 Tables, billion objects, batchoperations, s3:GetObject, s3:PutObject
  tags: aws, s3, s3control, storage, batch, bulk, glacier, kms, lambda, object-lock, replication, operate
---

# S3 Batch Operations Operator

## What this skill does

Executes S3 Batch Operations jobs correctly and safely at any scale. Runs
deterministic pre-checks before any state-changing CLI (manifest format
and readability, report bucket writability, IAM role permission chain
including operation-specific grants, KMS decrypt/encrypt path for
SSE-KMS objects, Lambda invoke permission for Lambda operations,
rate-control validity, manifest object-count estimate), executes the
`create-job` behind a CONFIRM gate, and verifies the result by polling
`describe-job` until `Status: Complete`, reading the completion report,
and reconciling `Failed` count against an acceptable threshold. Every
job plan names the operation-specific IAM grants; every diagnose-job
surfaces the failure-mode table so the operator knows whether the root
cause is permissions, manifest format, throttling, or a per-object error.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why a batch job is a manifest + role + report + rate-control quad, the false-green trap | Understanding the safety model |
| **§ Pre-flight** | Job spec gate — manifest versioning, report bucket region, role ARN | Before executing any CLI |
| **§ Process** | Per-operation planning: create-job, diagnose-job, cancel-job, update-priority | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY/NOTES template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that silently fail jobs or skip objects | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, IAM role policy, KMS key policy, manifest validation | Defense-in-depth |
| **§ Expert heuristic** | Batch Operations is async and per-object failures are silent — never trust `Active` alone | Avoiding the false-green trap |

## STRICT output contract

EVERY response MUST end with a single fenced text block in this exact
shape (the operator's downstream tooling greps for it). No deviations:

```text
OPERATION: <create-job | diagnose-job | cancel-job | update-priority>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <manifest-bucket/path> (operation: <type>, role: <arn-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated, or "(none — pre-checks failed)">
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description> | (pending execution)
  - [FAIL] <verification description> — <reason>
NOTES: <rate-control, monitoring, caveats>
```

Rules of the contract:

- VERDICT is exactly one of `READY`, `BLOCKED`, `COMPLETED`. No other
  values. `READY` means pre-checks passed and a CONFIRM gate is
  pending; `BLOCKED` means at least one pre-check failed — do NOT emit
  STEPS that mutate state; `COMPLETED` means post-verification passed
  after the job finished.
- If PRE_CHECKS has any `[FAIL]`, VERDICT MUST be `BLOCKED` and STEPS
  MUST be `(none — pre-checks failed)`.
- If VERDICT is `READY`, STEPS[1] MUST be the CONFIRM prompt and
  STEPS[2] MUST be the actual `create-job` CLI.
- If VERDICT is `COMPLETED`, POST_VERIFY MUST contain at least one
  `[PASS]` and no `[FAIL]`.
- Never wrap the block in JSON, never abbreviate the field names,
  never omit a section. If a section is empty, write `(none)`.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (manifest unreadable, report bucket not writable, role missing `batchoperations:*` or operation-specific grants, KMS decrypt denied for SSE-KMS source, Lambda resource policy missing `batchoperations.amazonaws.com` principal, rate-control invalid, manifest contains zero objects, destination bucket missing for copy) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact `create-job` CLI with all flags populated, wait for operator yes |
| `COMPLETED` | Job reached `Status: Complete` AND post-verification passed (`Failed` count within threshold, completion report readable, sample objects verified) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Manifest format and readability.** Manifest is a versioned S3
   inventory report (with `manifest.json` + `manifest.checksum`) OR a
   CSV file (`bucket,key` per line, versioned CSV requires a third
   column). The role can read the manifest object(s).
2. **Report bucket configured and writable.** `ReportBucket` is in the
   same Region as the Batch Operations job. Role has `s3:PutObject` on
   the report prefix.
3. **IAM role permission chain.** Role has `batchoperations:*` on the
   job ARN (or `*`), plus read on the manifest bucket and write on the
   target bucket(s). Operation-specific grants (see table below).
4. **KMS decrypt path on source.** For SSE-KMS objects, the role has
   `kms:Decrypt` on the source key ARN AND the source key policy
   grants the role.
5. **KMS encrypt path on destination.** For copy or re-encrypt
   operations, the role has `kms:Encrypt` on the destination key ARN
   AND the destination key policy grants the role.
6. **Lambda invoke permission.** For invoke operations, the Lambda's
   resource-based policy allows `batchoperations.amazonaws.com` to
   `lambda:InvokeFunction`, scoped to the job role ARN.
7. **Rate-control validity.** `RequestsPerSecond` (if set) is in
   [1, 2500]. `CompletionWindow` (if set) is between 1 hour and 1 year.
8. **Object-count estimate.** Manifest object count produces an ETA
   within the configured `CompletionWindow`. For billion+ object
   manifests, verify the rate limit produces a sub-window ETA.

**Cost/time baselines (2026):**

- Per-object processing time: 0.5-2 seconds typical (operation-
  dependent; Glacier restore and Lambda invoke are slower).
- Default rate: S3 Batch Operations auto-scales within the account's
  S3 request budget; explicit `RequestsPerSecond` caps it.
- Job setup latency: 1-5 minutes from `create-job` to `Active`.
- Completion report: written within minutes of job `Complete`.
- Cost: per-request charges (PUT/GET/restore) plus a Batch Operations
  per-object processing fee (see S3 pricing).

## Mindset

**One-line takeaway:** `Status: Active` on a Batch Operations job is a
scheduling claim, not a delivery claim. A job is only "done" when
`Status: Complete`, the completion report shows the expected success
count, and a sample of objects verifies the operation actually applied.
Driven by three S3 Batch Operations realities:

- **A batch job is a manifest + role + report + rate-control quad.**
  The manifest enumerates objects; the role grants the operation;
  the report records results; the rate-control prevents runaway costs.
  A single broken link makes the entire job fail or silently skip —
  the job shows `Active` on dashboards while objects are untouched.
- **Per-object failures are silent.** A job can complete with tens of
  thousands of `Failed` entries while `Status: Complete` looks green.
  Operators who do not read the completion report discover the failure
  weeks later when downstream effects surface.
- **Large jobs (billion+ objects) need explicit rate-control.** Without
  `RequestsPerSecond`, the job can saturate the source or destination
  bucket's request budget, crowd out application traffic, and exhaust
  KMS request quotas (especially for decrypt+re-encrypt). Always set a
  rate limit for jobs over 100 million objects.

## Pre-flight: job spec gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-bucket-inventory-configurations` paginates at
100. `describe-job` returns the full job descriptor in one call. CSV
manifests have no native pagination — estimate the object count from
the file size (each line averages 80-120 bytes for `bucket,key`).

**Live-account pre-flight (skip if offline plan audit):**
The eight live-account pre-flight probes (manifest head-object, report-bucket region, versioning capture, role policy chain, KMS key state, destination KMS, Lambda policy, describe-job): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Job spec is not valid JSON
or is missing required fields — cannot plan.` and `REMEDIATION:
Re-validate the spec against the operation schema in references/
operation-iam-matrix.md and re-plan.`

| Job spec attribute | Effect on operation |
|---|---|
| `Manifest.Spec.Format: S3InventoryReport` | Requires `manifest.json` + `manifest.checksum`. Versioned inventory required for version-aware operations. |
| `Manifest.Spec.Format: CSV` | Each line is `bucket,key` (unversioned) or `bucket,key,versionId` (versioned). No header row. |
| `Operation` mismatch with manifest versioning | A versioned operation (e.g., object lock retention) on an unversioned manifest BLOCKS. |
| `Report.Bucket` not in job Region | BLOCKED. Batch Operations requires the report bucket in the same Region as the job. |
| `Role` missing `iam:PassRole` on the caller side | `create-job` itself fails with `AccessDenied`. Caller needs `iam:PassRole` on the role ARN. |
| `RequestsPerSecond` outside [1, 2500] | BLOCKED. |
| `Priority` outside [-2147483648, 2147483647] | BLOCKED. Higher value = higher priority. |
| Manifest containing zero objects | BLOCKED. |
| `ToggleEnabled: false` | Job created in `Suspended` state; will not run until `update-job-status` sets `Ready`. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Batch Operations behaviors

These behaviors are easy to misjudge without operational experience.
Each changes a plan if ignored:
The 12 non-obvious behaviors (two-sided role, versioned-inventory requirement, no CSV header row, fixed Lambda payload, two-stage Glacier restore, ServerSideCopy re-encrypt, full-tagset replace, global priority, CompletionWindow hint, report scope, S3 Tables operations, transient throttling): [references/advanced-patterns.md](references/advanced-patterns.md).


### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Manifest exists and is readable by the role.
2. Manifest format matches the operation's versioning requirement.
3. Report bucket exists in the same Region as the planned job.
4. Caller has `s3control:CreateJob` AND `iam:PassRole` on the role.
5. Role has `batchoperations:*` (or scoped equivalent).
6. Role has read on the manifest bucket (`s3:GetObject` on the
   manifest prefix).
7. Role has `s3:PutObject` on the report bucket prefix.
8. `RequestsPerSecond` (if set) is in [1, 2500].
9. `Priority` is within the int32 range.
10. Manifest object count is non-zero.

**Operation-specific pre-checks:**

| Operation | Additional checks |
|---|---|
| **Copy** | Destination bucket exists; role has `s3:PutObject` on destination; for SSE-KMS source, role has `kms:Decrypt`; for SSE-KMS destination, role has `kms:Encrypt` + destination key policy grants role. |
| **ReplaceTag** | Role has `s3:PutObjectTagging` and `s3:DeleteObjectTagging` on the target. New tagset does not exceed 10 keys / 256 chars per value. |
| **Restore** | Source objects are in GLACIER / GLACIER_IR / DEEP_ARCHIVE. Role has `s3:RestoreObject`. `Days` and `GlacierJobTier` (Standard/Bulk) are set. |
| **Replicate** | Source bucket has replication configured; destination rule exists. Role has `s3:ReplicateObject`, `s3:ReplicateDelete`. |
| **Invoke** | Lambda `State: Active`. Lambda resource-based policy allows `batchoperations.amazonaws.com` to `lambda:InvokeFunction`. Lambda reserved concurrency >= `RequestsPerSecond`. Lambda timeout >= 60s (Batch retries on timeout, but a 3s timeout is almost always wrong). |
| **PutACL** | Role has `s3:PutObjectAcl` on the target. Canned ACL or access-control policy is valid. |
| **PutObjectLockRetention** | Target bucket has Object Lock enabled. Role has `s3:PutObjectRetention`. `Mode` is `GOVERNANCE` or `COMPLIANCE`. `RetainUntilDate` is in the future. |
| **PutObjectLockLegalHold** | Target bucket has Object Lock enabled. Role has `s3:PutObjectLegalHold`. `Status` is `ON` or `OFF`. |

**Job failure-mode table (use during diagnose-job):**
The nine-row failure-mode table mapping `describe-job` symptoms and completion-report failure codes to root causes and fixes: [references/error-handling.md](references/error-handling.md).

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact `aws s3control create-job` CLI with the JSON operation
  spec inline or referenced from a file.
- The expected duration (based on manifest size and rate limit).
- The expected side-effects (object count processed, KMS request
  volume, Lambda invocation count).
- The CONFIRM gate prompt.
- The monitoring commands (`describe-job` polling cadence, CloudWatch
  metrics to watch).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before `create-job`,
  `update-job-status`, `update-job-priority`, or any state-changing
  CLI, emit: `CONFIRM: About to <operation> on job <id-or-"new"> in
  account <account> region <region>. This will <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.
- Capture pre-state: if modifying an existing job,
  `aws s3control describe-job --account-id <account> --job-id <id>
  --output json > /tmp/<id>-pre-$(date +%s).json`.
- For new jobs: write the operation spec to a local JSON file and
  pass via `--operation`. Capture the returned `JobId`.
- Poll `describe-job` every 60 seconds (or longer for billion-object
  jobs) until `Status` transitions away from `Active`.

### Step 4: Post-verification — COMPLETED

After the job finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `describe-job --job-id <id>` — confirm `Status: Complete`.
2. Read `ProgressSummary` — `NumberOfTasksSucceeded` matches the
   expected count; `NumberOfTasksFailed` is within the acceptable
   threshold (typically 0; for billion-object jobs, < 0.01%).
3. Read the completion report (`Report.Bucket`). For `FailedTasksOnly`
   scope, confirm the report is non-empty only if there were failures.
4. Sample 5 objects from the manifest — verify the operation applied
   (e.g., for copy, `head-object` on destination; for KMS re-encrypt,
   verify `SSEKMSKeyId` matches the new key; for tag replace, verify
   `get-object-tagging` matches the new tagset).
5. For Glacier restore: sample 5 objects — verify `Restore` header
   shows `ongoing-request="false"` (or, for bulk tier, that the
   request is queued).
6. For Lambda invoke: check CloudWatch Logs for the Lambda — no
   errors above the expected threshold.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. A failed verification typically means
the job completed with unexpected failures; route to diagnose-job.

## Output format (per operation)

See § STRICT output contract above. The block MUST appear exactly in
that shape at the end of the response.

### Worked example — create-job (bulk KMS re-encrypt)

```text
OPERATION: create-job
VERDICT: READY
TARGET: s3://prod-inventory/2026-08-01/manifest.json
        (operation: copy with new SSE-KMS key, role:
         arn:aws:iam::111111111111:role/S3BatchOpsRole)
PRE_CHECKS:
  - [PASS] Manifest readable, format S3InventoryReport V2 (versioned)
  - [PASS] Report bucket prod-batch-reports in us-east-1 (matches job)
  - [PASS] Caller has s3control:CreateJob + iam:PassRole on
    arn:aws:iam::111111111111:role/S3BatchOpsRole
  - [PASS] Role has batchoperations:*, s3:GetObject on prod-inventory,
    s3:PutObject on prod-batch-reports
  - [PASS] Role has s3:GetObject + s3:PutObject on prod-data
  - [PASS] Role has kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/old-key
  - [PASS] Role has kms:Encrypt on arn:aws:kms:us-east-1:111111111111:key/new-key
  - [PASS] New KMS key policy grants role Encrypt
  - [PASS] RequestsPerSecond: 500 (in [1, 2500])
  - [PASS] Manifest object count: 12,400,000 — ETA ~6.9h at 500 RPS
    (within CompletionWindow: 24h)
STEPS:
  1. CONFIRM: About to create a Batch Operations copy+re-encrypt job
     on 12,400,000 objects in bucket prod-data (account
     111111111111, region us-east-1), overwriting in place with new
     SSE-KMS key arn:aws:kms:us-east-1:111111111111:key/new-key, at
     500 RPS. Estimated cost: ~$248 (PUT+GET+SSE-KMS). Proceed?
     (yes/no)
  2. aws s3control create-job \
       --account-id 111111111111 \
       --region us-east-1 \
       --priority 50 \
       --role-arn arn:aws:iam::111111111111:role/S3BatchOpsRole \
       --operation '{"S3InitiateRestoreObject": null}' \
       --manifest '{"Spec":{"Format":"S3InventoryReport","Fields":["Bucket","Key","VersionId"]},"Location":{"ObjectArn":"arn:aws:s3:::prod-inventory/2026-08-01/manifest.json","ETag":"<etag>"}}' \
       --report '{"Bucket":"arn:aws:s3:::prod-batch-reports","Prefix":"kms-reencrypt-2026-08/","Format":"Report_CSV_20180820","ReportScope":"FailedTasksOnly"}' \
       --client-request-token "$(uuidgen)"
     (replace --operation with the actual copy-with-new-encryption JSON)
  3. Poll: aws s3control describe-job --account-id 111111111111
     --job-id <returned-id> --query 'Status'
     (every 5 minutes for a 7-hour job)
POST_VERIFY:
  - (pending execution)
NOTES:
  - Bulk KMS re-encrypt is a server-side copy with new SSE-KMS
    metadata, overwriting in place. Set NewObjectMetadata.SSEKMSKeyId
    to the new key in the operation JSON. Source ~12.4M Decrypt +
    destination ~12.4M Encrypt requests. Verify KMS quota first.
  - Use FailedTasksOnly report scope to avoid a multi-GB report.
  - CloudWatch alarm on KMS Throttles during the job window.
```

### Worked example — diagnose-job (BLOCKED with remediation)

Full diagnose-job BLOCKED example (Lambda reserved-concurrency root cause, remediation options, re-run of failed objects): [references/worked-examples.md](references/worked-examples.md).

### Worked example — create-job (Glacier bulk restore, COMPLETED)

Full Glacier bulk-restore COMPLETED example (two-stage restore verification): [references/worked-examples.md](references/worked-examples.md).

## Anti-Patterns — NEVER

- NEVER create a Batch Operations job without verifying the IAM role
  has the operation-specific grants. `batchoperations:*` is the job-
  control plane permission; the actual object operations need
  `s3:GetObject`, `s3:PutObject`, `s3:RestoreObject`,
  `s3:PutObjectTagging`, `s3:PutObjectRetention`, or
  `s3:PutObjectAcl` depending on the operation type. Missing grants
  produce a job that completes with 100% failure.

- NEVER include a header row in a CSV manifest. The first line is
  parsed as an object. A header `bucket,key` produces a `NoSuchKey`
  failure for object `key` in bucket `bucket`. Use S3 inventory
  format if you want structured metadata.

- NEVER assume `Status: Complete` means all objects were successfully
  processed. Read the completion report and reconcile
  `NumberOfTasksFailed` against an acceptable threshold. For large
  jobs, use `FailedTasksOnly` report scope and treat any non-empty
  report as a follow-up item.

- NEVER run a billion-object job without an explicit
  `RequestsPerSecond`. Default auto-scaling can saturate the source
  bucket, KMS quota, or Lambda concurrency, producing throttling
  cascades that exhaust the retry budget.

- NEVER assume Glacier restore is finished when the Batch Operations
  job is `Complete`. The job submits restore requests; the actual
  restore is asynchronous on the Glacier side. Poll `head-object
  --restore` for `ongoing-request="false"` before downstream use.

- NEVER pass a role ARN at `create-job` without verifying the caller
  has `iam:PassRole` on that ARN. The `create-job` API itself fails
  with `AccessDenied` before any object processing.

- NEVER set all jobs to `Priority: 2147483647`. Priority is a relative
  scheduling signal within the account + Region. Inflating every job
  to max nullifies the priority system and produces contention.

- NEVER use the `Task` report scope for billion-object jobs. The
  completion report will be a multi-GB CSV. Use `FailedTasksOnly` and
  read the `ProgressSummary` for the success count.

- NEVER attempt a `PutObjectLockRetention` operation on a bucket
  without Object Lock enabled. The operation fails per-object with
  `InvalidRequest`. Verify `get-object-lock-configuration` before
  creating the job.

- NEVER assume Lambda invocations are idempotent. Batch Operations
  retries with the same `taskId`. If the Lambda has side effects
  (writes to a database, sends a notification), it MUST deduplicate
  on `taskId`.

- NEVER trust `describe-job.ProgressSummary` alone for cost
  verification. Cross-check S3 and KMS CloudWatch request metrics
  during the job window — throttles and retries inflate actual
  request count above the object count.

- NEVER forget the manifest's `ETag` field. For S3 inventory
  manifests, the `manifest.json` object has an ETag that must be
  passed in the `Manifest.Location.ETag` field. Omitting it produces
  a `400 MalformedXML` error from `create-job`.

- NEVER auto-execute a state-changing Batch Operations CLI without
  the CONFIRM gate. Job creation and priority changes can run up
  significant costs and modify objects at scale.

## Pre-flight safety checks (run before any remediation CLI)

All eight pre-flight safety checks (confirmation gate, cost estimation, manifest validation, role trust policy, KMS key state, Lambda state, report bucket region, rate-control sanity): [references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: the silent-completion trap

The silent-completion trap in full (the rule, why it exists, verification-technique table, three-step verification protocol, FAILURE_COUNT/SAMPLE_VERIFIED surfacing, post-deploy detection): [references/advanced-patterns.md](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent AWS features detail (S3 Tables targets, server-side copy re-encrypt, FailedTasksOnly GA, per-job rate control, Glacier IR/Deep Archive tiers, Object Lock operations, cross-region jobs, AWS/S3Operations metrics): [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — Step 0 non-obvious Batch Operations behaviors, pre-flight safety checks, the silent-completion trap, recent AWS features
- [Worked examples](references/worked-examples.md) — diagnose-job BLOCKED and Glacier bulk-restore COMPLETED walkthroughs
- [Error handling](references/error-handling.md) — job failure-mode table (`describe-job` symptom → root cause → fix)
- [Diagnostic commands](references/diagnostic-commands.md) — the eight live-account pre-flight probes

## Domain

AWS CloudOps / S3 Batch Operations, Bulk Object Transformation, and
At-Scale Storage Management.

## AWS documentation

- **S3 Batch Operations User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **Batch Operations operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-operations.html
- **Creating a Batch Operations job** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-create-job.html
- **Batch Operations IAM role** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-iam-role.html
- **S3 inventory configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-inventory.html
- **S3 Tables (Apache Iceberg)** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables.html
- **S3 Control API Reference** — https://docs.aws.amazon.com/AmazonS3/latest/APIReference/control.html
- **S3 Batch Operations pricing** — https://aws.amazon.com/s3/pricing/
