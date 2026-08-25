# Advanced Patterns — S3 Batch Operations Operator

Load-on-demand deep dives moved verbatim from SKILL.md: Step 0
non-obvious behaviors, pre-flight safety checks, the
silent-completion trap, and recent AWS features.

## Step 0: Expert knowledge — non-obvious Batch Operations behaviors

These behaviors are easy to misjudge without operational experience.
Each changes a plan if ignored:

- **The role is two-sided.** The *caller* invoking `create-job` needs
  `s3control:CreateJob` AND `iam:PassRole` on the role ARN. The *role
  itself* needs the operation-specific grants (read source, write
  target, KMS, Lambda invoke). A missing `iam:PassRole` surfaces as
  `AccessDenied` on `create-job` itself, before any object processing.

- **S3 inventory manifests must be the versioned flavor for version-
  aware operations.** Object Lock retention, legal hold, and version-
  aware copy require `version: "V2"` in the inventory configuration
  AND `ManifestGenerator.OutputSchemaVersion: V2`. An unversioned
  manifest silently picks the latest version, which may not be the
  intended target.

- **CSV manifests have no header row.** The first line is data. A
  header row (`bucket,key`) is parsed as an object named `key` in a
  bucket named `bucket`, producing a `NoSuchKey` failure in the
  completion report.

- **The Lambda invoke payload is fixed.** Batch Operations invokes the
  Lambda once per object with a fixed event structure (`taskId`,
  `s3Key`, `s3VersionArn`, `s3BucketArn`). The Lambda cannot stream
  or batch — concurrency is controlled only by `RequestsPerSecond`.
  Set the Lambda reserved concurrency to at least the rate limit.

- **Glacier restore is a TWO-STAGE operation.** Batch Operations
  submits restore requests; the actual restore happens asynchronously
  on the Glacier side. `Status: Complete` means all restore requests
  were submitted, NOT that all objects are restored. Verify with
  `head-object --restore` on a sample.

- **Bulk KMS re-encrypt is a ServerSideCopy with new encryption.**
  There is no native "re-encrypt" operation. The pattern is a copy
  operation with `NewObjectMetadata` SSE-KMS pointing at the new key,
  replacing the source in place (same key, overwrite) or to a new
  bucket. This means the role needs both `kms:Decrypt` on the old key
  AND `kms:Encrypt` on the new key.

- **Replace-tag replaces the entire tagset, not a single tag.** The
  `ReplaceTags` operation takes a full tag set. A partial replacement
  requires the Lambda operation with custom logic.

- **Job priority is global within the account + Region.** A priority-
  100 job preempts resource allocation from a priority-50 job. Setting
  all jobs to the max value nullifies the priority system.

- **`CompletionWindow` is a hint, not a guarantee.** Batch Operations
  aims to finish within the window but does not abort if it exceeds
  it. For hard deadlines, set a CloudWatch alarm on
  `SecondsElapsed` or use `cancel-job` at a scheduled time.

- **Completion report format depends on the report scope.** `Task`
  scope writes one entry per object (success + failure). `FailedTasks
  Only` scope writes only failures. Always use `FailedTasksOnly` for
  billion-object jobs to avoid a multi-GB report.

- **S3 Tables Batch Operations (2025-2026) targets table namespaces.**
  The operation type `S3Table` runs against S3 Tables (Apache Iceberg)
  rather than standard object buckets. The manifest format differs —
  it enumerates table ARNs, not object keys.

- **Large-job throttling surfaces as `Transient` failures in the
  report.** When the source bucket or KMS key throttles, individual
  objects fail with a transient code and ARE retried automatically
  up to a limit. Persistent throttling exhausts the retry budget and
  the objects end up in `Failed`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before `create-job`,
  `update-job-status`, `update-job-priority`, or `delete-job`,
  emit: `CONFIRM: About to <operation> on job <id-or-"new"> in
  account <account> region <region>. This will <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.

- **Cost estimation.** Before `create-job`, multiply the manifest
  object count by the per-operation S3 request cost (GET + PUT for
  copy, GET + restore for Glacier, GET + Lambda invocation for
  invoke). Surface the estimate in the CONFIRM prompt.

- **Manifest validation.** For CSV manifests, sample the first 5
  lines and confirm each parses as `bucket,key[,versionId]`. For S3
  inventory manifests, confirm both `manifest.json` and
  `manifest.checksum` exist and the format matches the operation's
  versioning requirement.

- **Role trust policy.** Confirm the role's trust policy allows
  `Service: batchoperations.amazonaws.com` to `sts:AssumeRole`.
  Without it, the job cannot assume the role and fails immediately.

- **KMS key state.** For SSE-KMS sources, `describe-key` to confirm
  `Enabled`. For copy / re-encrypt, repeat on the destination key.
  Cross-check the key policy grants the role.

- **Lambda state (invoke operations).** `get-function-configuration`
  to confirm `State: Active`, `Timeout >= 60`. `get-policy` to
  confirm `batchoperations.amazonaws.com` principal. `get-function-
  concurrency` to confirm reserved concurrency >= `RequestsPerSecond`.

- **Report bucket region.** The report bucket MUST be in the same
  Region as the job. Cross-region report writes fail silently.

- **Rate-control sanity check.** For jobs over 100M objects, verify
  `RequestsPerSecond` produces an ETA within `CompletionWindow` and
  stays below the source bucket's documented request budget.

## Expert heuristic: the silent-completion trap

Batch Operations is asynchronous and per-object failures are silent.
The single highest-leverage rule for operating it safely is:

> A job with `Status: Complete` is a SCHEDULING claim, not a SUCCESS
> claim. The only proof of a successful batch operation is a
> completion report showing zero failures (or failures within an
> explicitly-accepted threshold) PLUS a sample of objects verifying
> the operation applied. Treat any dashboard that shows "job: Complete"
> as a signal worth less than reading the report's first failure row.

**Why this rule exists:** S3 Batch Operations processes objects
individually. Each object's success or failure is recorded only in the
completion report. The job's aggregate `Status` transitions to
`Complete` regardless of how many objects failed. A job that processes
zero objects successfully (e.g., wrong IAM role) still shows `Complete`.

**Concrete verification techniques:**

| Technique | Mechanism | What it proves |
|---|---|---|
| Read `ProgressSummary` | `describe-job --query ProgressSummary` | Aggregate success / failure counts |
| Read completion report (FailedTasksOnly) | `s3 cp s3://<report-bucket>/<prefix>/result/<job-id>/... -` | Per-object failure codes |
| Sample 5 objects with `head-object` / `get-object-tagging` | Direct inspection of processed objects | Operation actually applied |
| KMS request CloudWatch metrics during job window | `get-metric-statistics` on Decrypt / Encrypt | Real request volume vs. expected |
| Lambda CloudWatch Logs (invoke operations) | `filter-log-events ERROR` | Per-invocation errors |
| Glacier restore `head-object --restore` | `ongoing-request` flag on a sample | Restore actually materialized |

**Three-step verification protocol (apply on every completed job):**

1. **Aggregate counts:** `describe-job` — `NumberOfTasksSucceeded`
   matches the manifest count; `NumberOfTasksFailed` is within
   threshold (typically 0).
2. **Failure codes:** read the completion report. Group failures by
   `FailureCode`. Any non-zero count needs a follow-up plan.
3. **Sample inspection:** pick 5 random objects from the manifest.
   Verify the operation applied (e.g., for KMS re-encrypt, the
   `SSEKMSKeyId` matches the new key; for tag replace, the tagset
   matches).

**Surface in the output:** for any completed job, include
`FAILURE_COUNT: <count>` and `SAMPLE_VERIFIED: <yes | no>`. If either
is not acceptable, do NOT mark the operation COMPLETED.

**Detection of silent job failure post-deploy:** CloudWatch alarm on
`NumberOfTasksFailed > 0` (Batch Operations emits metrics to
`AWS/S3Operations`), AND a daily audit Lambda that scans the latest
completion reports for non-zero failure counts.

## Recent AWS features (2024-2026)

- **S3 Tables Batch Operations (2025-2026):** Batch Operations now
  supports S3 Tables (Apache Iceberg) as a target. The operation type
  runs against table namespaces rather than object keys. Manifest
  format differs — enumerate table ARNs. Use for table compaction,
  snapshot management, or schema migration across many tables.

- **Server-side copy with new encryption (2024-2025):** The copy
  operation supports `NewObjectMetadata` with a new `SSEKMSKeyId`,
  enabling in-place KMS key rotation without downloading + re-uploading.
  The role needs `kms:Decrypt` on the old key and `kms:Encrypt` on the
  new key.

- **`FailedTasksOnly` report scope GA (2024):** The default report
  scope writes one row per object, producing multi-GB reports for
  billion-object jobs. `FailedTasksOnly` writes only failures,
  reducing cost and improving signal-to-noise.

- **Per-job rate control (2024-2025):** `RequestsPerSecond` in
  `RateCriteria` allows explicit throttling per job. Combined with
  job priority, this enables fair-share scheduling across many
  concurrent jobs in the same account + Region.

- **Glacier Instant Retrieval and Glacier Deep Archive restore tiers
  (2024-2025):** `S3InitiateRestoreObject` now supports
  `Tier: BULK | STANDARD | EXPEDITED` for Glacier IR / Glacier /
  Deep Archive. Verify the source storage class supports the chosen
  tier before creating the job.

- **Object Lock Batch Operations (2024):** `PutObjectRetention` and
  `PutObjectLegalHold` operations GA. Target bucket must have Object
  Lock enabled at creation time (cannot be retrofitted).

- **Cross-Region Batch Operations (2024-2025):** Jobs can target
  buckets in a different Region from the job's Region, but the role
  must be assumable in both Regions and the manifest / report must
  be in the job's Region.

- **CloudWatch Metrics for Batch Operations (2024-2026):** New
  namespace `AWS/S3Operations` emits per-job metrics
  (`NumberOfTasksSucceeded`, `NumberOfTasksFailed`, `BytesTransferred`).
  Use for alarms and dashboards.
