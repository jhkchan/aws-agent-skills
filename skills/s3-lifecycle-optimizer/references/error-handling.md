# Error Handling — s3-lifecycle-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Error handling — CLI and data-source failures


The workflow depends on S3 API, S3 Control API (Storage Lens), and
optional CloudTrail data. Each can fail independently; silent failures
produce misclassifications (especially false `ALREADY_OPTIMAL` on
buckets where Storage Lens is not enabled).

### Storage Lens failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-storage-lens-configuration` returns `NoSuchConfiguration` | API error | Storage Lens is not enabled. Fall back to `list-objects-v2` with `--page-size 1000` for a sample; flag the recommendation as MEDIUM confidence due to absent access-pattern data. Surface "Enable Storage Lens" as a parallel finding. |
| Storage Lens enabled but `ExportVersion` > 7 days stale | `ExportDataFreshness` check | Noncurrent-byte % and storage-class distribution may not reflect recent changes. Re-pull if possible; otherwise flag as MEDIUM confidence. |
| Storage Lens shows 0 noncurrent bytes on a versioned bucket | Cross-check with `list-object-versions --noncurrent-versions` | Iflist shows noncurrent versions but Storage Lens shows 0, the dashboard is misconfigured. Trust the direct API call. |

### S3 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-bucket-lifecycle-configuration` returns `NoSuchLifecycleConfiguration` (404) | HTTP 404 | This is NORMAL — the bucket has no lifecycle. Proceed with full recommendation; do NOT treat as an error. |
| `get-bucket-versioning` returns `{}` (empty) | Response body empty | Versioning was never enabled. Skip the noncurrent-version dimension entirely. |
| `list-multipart-uploads` returns empty `Uploads` array | `len(Uploads) == 0` | No stale multipart uploads. Still emit the `AbortIncompleteMultipartUpload` rule as preventive; do not mark multipart dimension as OPPORTUNITY_FOUND. |
| `put-bucket-lifecycle-configuration` fails with `MalformedXML` | API error | The JSON payload has a schema error. Common causes: `NoncurrentDays` < 1, `Filter` and `Prefix` at the same rule level, or unsupported `StorageClass` value. Validate against the S3 Lifecycle schema and retry. |
| `list-objects-v2` returns `AccessDenied` | API error | The role lacks `s3:ListBucket` on the bucket. Surface as a BLOCKED finding; recommend the operator grant `s3:ListBucket` and `s3:GetLifecycleConfiguration` to the audit role. |
| `list-objects-v2` is paginating > 100 pages on a large bucket | Pagination count | STOP iterating live. Use S3 Inventory (daily export) or Storage Lens aggregate metrics instead. Live iteration of a billion-object bucket can take hours and incur request charges. |

### Object Lock interaction failures

| Failure mode | Detection | Handling |
|---|---|---|
| Lifecycle `ExpirationInDays` shorter than Object Lock retention | Cross-check `get-object-lock-configuration` retention period vs `ExpirationInDays` | The rule is silently a no-op on locked objects. Surface as a CONFIG finding; do not change the verdict based on the (silently ineffective) expiration rule. |
| Object Lock `GOVERNANCE` mode on compliance data | `Mode == GOVERNANCE` for a compliance workload | Surface that any principal with `s3:BypassGovernanceRetention` can shorten retention. Recommend `COMPLIANCE` mode. This is a finding, not a verdict change. |

### Batch Operations failures

| Failure mode | Detection | Handling |
|---|---|---|
| `create-job` fails with `AccessDenied` | API error | The role lacks `s3control:CreateJob`. Batch Operations requires a dedicated role with `s3:ObjectLambda`/`s3:ReplicateObject` permissions. Surface the IAM requirement in the IMPLEMENTATION block. |
| Batch job manifest generation fails | Manifest S3 location not writable | The manifest bucket must be in the same region as the Batch Operations job. Verify region alignment before emitting the IMPLEMENTATION step. |

### Rate-limit and large-batch guidance

For fleet-wide lifecycle audits covering > 100 buckets:

1. **Serialize, do not parallelize** the `put-bucket-lifecycle-configuration`
   calls across buckets in the same region. S3 Control API has a
   sustained rate limit of ~5 lifecycle-configuration puts per second
   per account; parallel puts will throttle.
2. **Page list-buckets by region** using `--region <region>` on each
   call. A global `list-buckets` returns buckets across all regions,
   but lifecycle configuration is region-specific.
3. **For > 1,000 buckets**, split into batches of 50 buckets per
   operator CONFIRM gate. Each batch emits a single consolidated
   CONFIRM; the operator reviews the savings rollup before applying.
4. **Verify propagation** after each batch: lifecycle rules are
   eventually consistent (~24 hours for first execution). Surface this
   in the post-apply verification step.

### put-bucket-lifecycle-configuration failure modes

The single state-changing API call in this skill is
`put-bucket-lifecycle-configuration`. Each failure below has a specific
remediation — never blindly retry without identifying the root cause,
because S3 lifecycle is a single-writer resource and a retry on the same
bucket can collide with another in-flight put.

| Error | Root cause | Specific fix |
|---|---|---|
| `MalformedXML` (most common) | JSON schema error | Validate against the S3 Lifecycle schema. Common causes and fixes: (a) top-level `Prefix` mixed with `Filter` in the same rule — remove `Prefix`, use `Filter: { Prefix: "..." }`; (b) `NoncurrentDays < 1` — set to `>= 1`; (c) unsupported `StorageClass` value — must be one of `STANDARD_IA`, `ONEZONE_IA`, `INTELLIGENT_TIERING`, `GLACIER`, `GLACIER_IR`, `GLACIER_DEEP_ARCHIVE`, `DEEP_ARCHIVE` (the legacy `DEEP_ARCHIVE` alias still works but prefer `GLACIER_DEEP_ARCHIVE`); (d) trailing comma in JSON; (e) `Expiration` block inside a `NoncurrentVersionTransitions` rule — separate current-version and noncurrent rules. |
| `InvalidArgument: Unexpected Parameter 'StorageClass'` | Wrong key name for the transition type | Use `Transitions[].StorageClass` for CURRENT versions, `NoncurrentVersionTransitions[].NewNoncurrentStorageClass` for NONCURRENT versions. The two keys are not interchangeable. |
| `InvalidArgument: Conflicting conditional operation` | Another lifecycle put is in flight on the same bucket | S3 lifecycle is a single-writer resource. Serialize per-bucket puts; retry after a 5-second backoff. Do NOT parallelize puts on the same bucket even across regions — the lock is per-bucket. |
| `AccessDenied (PutLifecycleConfiguration)` | Caller role lacks `s3:PutLifecycleConfiguration` on the bucket | Add the permission to the bucket policy OR the caller's identity-based IAM. The bucket-owner default does NOT include lifecycle permissions — they must be explicit. Also verify there is no `Deny` statement with `s3:PutLifecycleConfiguration`. |
| `InvalidRequest: Lifecycle configuration filtering is limited to N rules` | Bucket exceeds the rule count cap (1,000 legacy, 1,500 with new filtering model post Aug 2023) | Consolidate rules using broader `Filter` patterns. Replace one-rule-per-prefix with tag-based filters: `Filter: { Tag: { Key: "archive_eligible", Value: "true" } }`. Split very large buckets by prefix into separate buckets if the cap cannot be avoided. |
| `InvalidStorageClass` | Rule references a storage class not supported in the bucket's region (e.g., Glacier Deep Archive unavailable in a new region at GA time) | Check supported storage classes via `aws pricing get-products --service-code AmazonS3 --filters ...`. Use `GLACIER` (Flexible Retrieval) as the fallback — it has the widest regional availability. |
| `OperationAborted: A conflicting conditional operation is currently in progress` | Same as above — another writer holds the lock | Same fix: serialize, backoff 5s, retry. Surface as TRANSIENT in the output block. |
| Throttling: `SlowDown` on a fleet audit (>100 buckets) | S3 Control API sustained rate limit (~5 lifecycle puts/sec/account) | Switch to serial execution with 200ms inter-call delay. For >1,000 buckets, batch 50 per CONFIRM gate (see Rate-limit guidance above). |
| `NoSuchBucket` mid-batch | Fleet audit iterated while a bucket was being deleted in parallel | Skip the bucket and re-queue. Do NOT fail the batch. Surface as TRANSIENT in the per-bucket output. |

**Recovery after a bad put:** if a `MalformedXML` or wrong-rule put
partially applies (rare — usually the put is atomic), use the JSON
backup from the pre-flight to restore the prior configuration via a
follow-up `put-bucket-lifecycle-configuration` call, then run the
Rollback procedure below.

---

## Rollback procedure (beyond JSON backup)


The pre-flight captures a JSON backup of the current lifecycle config.
Rollback is a three-step procedure — the JSON backup alone is
insufficient because lifecycle rules are eventually consistent and
objects may have already transitioned.

1. **Restore the prior configuration:**
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket <name> \
     --lifecycle-configuration file://<name>-lifecycle-backup-<timestamp>.json
   ```
   This stops FUTURE transitions but does not revert objects that have
   already moved to a cheaper tier.

2. **Identify objects that transitioned during the bad window:**
   ```bash
   # Find objects that transitioned to the target storage class
   # between the bad-put timestamp and the rollback timestamp.
   aws s3api list-objects-v2 --bucket <name> \
     --query "Contents[?StorageClass=='STANDARD_IA']" \
     --output json > transitioned-objects.json
   ```
   For large buckets, use S3 Inventory (daily export) filtered by
   storage-class column instead of `list-objects-v2`.

3. **Restore the storage class of affected objects via S3 Batch
   Operations:**
   ```bash
   aws s3control create-job --account-id <acct> \
     --operation '{"S3CopyObject": {"TargetStorageClass": "STANDARD",
       "ReplaceMetadata": {"ContentType": "application/octet-stream"}}}' \
     --manifest-location s3://<manifest-bucket>/manifest.csv \
     --report-spec '{"ReportFormat":"Report_20170828","Bucket":"s3://<report-bucket>","Enabled":true,"ReportScope":"AllTasks"}' \
     --role-arn arn:aws:iam::<acct>:role/<batch-role> \
     --client-request-token $(uuidgen)
   ```
   This copies each object back to Standard. The copy operation incurs
   request and data-transfer charges — include them in the rollback
   cost estimate.

4. **Verify Storage Lens metrics stabilize** within 24-48 hours post-
   rollback. The noncurrent-byte % and storage-class distribution
   should return to pre-bad-put levels.

**Cost of rollback:** a bad lifecycle put on a 100 TB bucket that
triggers a mass Standard → Standard-IA transition costs ~$50-150 in
request fees (1 PUT per object on transition) plus ~$1,000-2,000 in
Batch Operations copy-back fees. Surface this in the CONFIRM gate
before applying any lifecycle change on a large bucket.
