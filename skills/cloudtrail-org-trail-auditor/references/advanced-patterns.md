# Advanced Patterns — cloudtrail-org-trail-auditor

## Step 0: Expert knowledge — non-obvious CloudTrail behaviors

These behaviors change classification if ignored:

- **`IsOrganizationTrail` is the org-coverage flag, not the multi-region flag.**
  An org trail with `IsMultiRegionTrail: false` logs all accounts but only in
  the trail's home region — a lateral-movement attack in `ap-southeast-1`
  leaves zero trace. Both must be `true` for full org + full region coverage.

- **Org trail requires `organizations:EnableAWSServiceAccess` for CloudTrail.**
  If Organizations trusted-service access for CloudTrail is revoked, the trail
  appears active (`IsLogging: true`) but silently logs only the management
  account. Invisible in `describe-trails` — check `aws organizations
  list-aws-service-access-for-organization` for
  `SERVICE_PRINCIPAL: cloudtrail.amazonaws.com`.

- **S3 bucket policy must grant `s3:x-amz-acl: bucket-owner-full-control`.**
  Without this condition, log objects delivered on behalf of member accounts
  are owned by the member account, not the management account. The management
  account can list the objects (it owns the bucket) but cannot read them. The
  bucket policy must also allow `cloudtrail.amazonaws.com` to `s3:GetBucketAcl`,
  `s3:ListBucket`, and `s3:PutObject`.

- **`KmsKeyId` controls SSE-KMS for S3 log delivery, not "CloudTrail event
  encryption."** If `KmsKeyId` is null, S3 defaults to SSE-S3 (AES-256,
  Amazon-managed key). SSE-S3 IS encryption, but it is not customer-controlled
  — a compliance framework requiring customer-managed keys treats null
  `KmsKeyId` as NO_ENCRYPTION. The key must be in the trail's region and its
  policy must grant `cloudtrail.amazonaws.com` the `kms:GenerateDataKey*` and
  `kms:Decrypt` permissions with the CloudTrail trail ARN as encryption
  context (`kms:EncryptionContext:aws:cloudtrail:arn = <trail-arn>`).

- **Log file validation digest files live in a separate S3 prefix.** Digests
  are delivered to `<prefix>/CloudTrail-Digest/`. If an S3 lifecycle rule
  expires objects in the bucket prefix but does NOT exclude the digest
  sub-prefix, the digest chain breaks and `validate-logs` fails. A trail with
  `LogFileValidationEnabled: true` and expired digests provides a false sense
  of integrity.

- **CloudTrail Insights has its own billing dimension** (per management event
  analyzed, on top of the first-free-copy). Some orgs disable it for cost;
  the auditor still flags absence as NO_INSIGHTS — remediation can note the
  cost trade-off.

- **Insights selectors are a separate API call.** `describe-trails` does NOT
  return them — call `get-insight-selectors --trail-name <name>` separately.

- **`IncludeGlobalServiceEvents: false` silently drops IAM, STS, Route 53, and
  CloudFront events.** These global-service events are logged in the trail's
  home region (us-east-1 for org trails). Disabling them removes the entire
  IAM/STS audit trail. This is a CONFIG_GAP finding.

- **CloudWatch Logs retention is a log-group property, not a trail property.**
  A trail pointing to a log group with `retentionInDays: null` ("Never
  expire") has no compliance boundary on log lifetime. Flag as CONFIG_GAP.

- **The 5-trail-per-region quota** is a hard limit. An account with 5 trails
  in a region cannot create another without deleting one. Operational
  constraint — not a security finding, but may explain a missing org trail.

- **Trail ARN contains the management account ID, not the member account.**
  When auditing from a member account, the org trail will NOT appear in
  `describe-trails` — verify from the management account.

- **CloudTrail data events are NOT enabled by default — only management
  events are logged.** A "fully configured" org trail still records zero S3
  `GetObject`/`PutObject`, Lambda `Invoke`, or DynamoDB activity unless an
  event selector adds the data-resource ARNs. `get-event-selectors` is
  required; absence is a coverage gap (note in FINDINGS), not a verdict
  failure.

- **`lookup-events` API returns only the last 90 days and only management
  events.** Auditors using it to verify "did this trail capture X?" get a
  misleadingly empty result for any event older than 90 days or any data
  event. The S3 log files are the authoritative long-term record.

- **Event selectors can silently exclude AWS KMS events.** KMS generates very
  high event volume (Decrypt/Encrypt per S3 GET/PUT under SSE-KMS), so
  legitimate `ExcludeManagementEventSources: kms.amazonaws.com` entries are
  common. This is operationally reasonable but creates a forensics blind spot
  for KMS key abuse. Surface any exclusion in FINDINGS as a WARNING.

- **`describe-trails` (LIST) and `get-trail` (GET) return different fields.**
  `describe-trails` returns a summary list; `get-trail --name <name>` returns
  the full `Trail` object including the full KMS context. For an authoritative
  per-trail audit, prefer `get-trail` — `describe-trails` has been observed to
  omit fields on trails created by CloudFormation stacks that set advanced
  event selectors.

- **First management-event copy is free per region, per account; a second
  management-events trail in the same region incurs per-event billing.** A
  common cost trap: an operator creates a "backup" org trail pointing to a
  different bucket — silent double billing starts immediately. Surface a
  WARNING if the input reveals multiple trails in one region.

- **CloudTrail event delivery latency is typically 3–15 minutes, NOT the
  "hourly" many operators assume.** The hourly window is the file-batching
  cadence, but events for that window can land up to 15 minutes after the API
  call. Operators investigating "did X happen in the last 5 minutes?" cannot
  rely on CloudTrail — use CloudWatch Metrics or EventBridge for near-real-time
  detection. This is also why `IsLogging: true` does not guarantee that
  recently tested events are already in S3.

- **`validate-logs` requires `s3:GetObject` on BOTH the log-file prefix AND
  the digest prefix.** Most scoped-down audit roles grant only the log prefix
  and silently fail validation with a generic "AccessDenied" buried in the
  output. Verify the calling identity's role covers
  `s3://<bucket>/<prefix>/CloudTrail-Digest/*` as well as the log prefix.

- **Org-trail enablement propagation delay.** Flipping
  `--is-organization-trail` on an existing trail takes 5–15 minutes before
  shadow trails appear in member accounts and event delivery from member
  accounts begins. An audit run in that window reports NO member-account
  events even though configuration is correct — note this when classifying
  a recently converted trail.

- **CloudTrail log files use S3 multipart upload.** Subscribers wiring
  EventBridge or S3 event notifications on the log prefix may receive
  `s3:ObjectCreated:*` for the initiate-multipart-upload, not the
  complete-multipart-upload — subscribers see partial or empty objects. SIEM
  integrations should trigger on `CompleteMultipartUpload` only.

## Reference — CloudTrail internals (deep material)

### Org trail creation and member-account visibility

When an org trail is created in the management account, CloudTrail
automatically creates a "shadow" trail in each member account with the same
name. These shadow trails are read-only — member-account users can see the
trail exists but cannot modify it. All logs flow to the management account's
S3 bucket. If Organizations trusted-service access is revoked, the shadow
trails remain visible but stop delivering member-account events.

### Log file validation mechanics

Each hour, CloudTrail delivers log files for the preceding hour's events.
When `LogFileValidationEnabled` is true, it also delivers a digest file
containing SHA-256 hashes of all log files delivered in that hour, plus the
hash of the previous hour's digest (hash chain). `validate-logs` walks the
chain from the start time to the end time, recomputes hashes, and reports
any mismatch. A broken chain (missing or modified digest) invalidates all
subsequent entries.

### Insights detection model

CloudTrail Insights analyzes management-event volumes using statistical
anomaly detection. It establishes a baseline of normal API call rates and
error rates per event source over a rolling window, then flags sustained
deviations (typically 3x+ over baseline for several minutes). It does NOT
analyze individual events for suspiciousness — that is the job of GuardDuty
or Security Hub. Insights detects "unusual volume," not "malicious activity."

## Recent AWS features (2024-2026)

- **CloudTrail Lake (2024-2025):** CloudTrail Lake enables SQL-based querying of event data without S3/Athena. Auditors should verify that CloudTrail Lake is configured as a supplementary query surface, and that its retention period meets compliance requirements — Lake has its own separate retention independent of the S3 trail.
- **Expanded data event coverage (2024-2025):** CloudTrail now records data events for additional resource types including S3 directory buckets, Lambda layers, and CloudFront KeyValueStore. Auditors should verify that data event logging covers these new resource types where applicable.
- **CloudTrail Insights enhancements (2024):** Insights now supports anomaly detection on write management events with improved accuracy. Auditors should re-evaluate whether Insights is enabled on all organization trails — it is often overlooked.
- **Federation with CloudTrail Lake:** Lake now supports cross-account and cross-org event federation. Auditors should verify that the federation configuration includes all member accounts and that no accounts are silently excluded.
