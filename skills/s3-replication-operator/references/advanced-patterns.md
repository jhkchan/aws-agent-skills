# Advanced Patterns — s3-replication-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Cost/time baselines (2026)

**Cost/time baselines (2026):**

- New object replication latency (no RTC): typically 5-15 seconds for
  small objects; up to several minutes during bursts.
- With RTC: P99 <= 15 minutes, billed at a per-1,000-objects rate on
  top of standard request costs.
- Batch replication for existing objects: 1-5 seconds per object via
  S3 Batch Operations; manifest generation is the bottleneck (use S3
  Inventory).
- Delete-marker replication: same latency as object replication when
  enabled (it is OFF by default for backward compatibility).

---

## Mindset — replication is a four-link chain

**One-line takeaway:** `Status: Enabled` on a replication rule is a
*claim*, not proof. An object is only "replicated" once it appears in
the destination bucket with the same version ID, and `PendingReplication`
drains to zero (or stable). Driven by three S3 realities:

- **Replication is a four-link chain.** The rule points at a
  destination; the destination must accept the PUT; the IAM role must
  read source + write destination + decrypt source KMS + encrypt
  destination KMS; for cross-account the destination bucket policy
  must explicitly grant the source role. A single broken link makes
  the entire chain fail silently — the rule shows `Enabled` on
  dashboards while no objects arrive.
- **Delete-marker replication is OFF by default.** Many operators
  assume deletes are replicated when they see object replication
  working. They are not. Delete markers (and tag updates after Nov
  2022) require explicit `Filter` elements under `DeleteMarkerReplication`
  and `DeleteReplication` — verify the rule's
  `DeleteMarkerReplication.Status` is `Enabled` if you expect deletes
  to propagate.
- **Cross-account replication has THREE policy surfaces.** The IAM role
  (identity-based), the destination bucket policy (resource-based), AND
  the destination KMS key policy. Missing any one of the three fails
  with a misleading `AccessDenied` that surfaces only in S3 Server
  Access Logs or CloudTrail `CompleteMultipartUpload`/`PutObject`
  events on the destination.

---

### Step 0: Expert knowledge — non-obvious S3 replication behaviors

These behaviors are easy to misjudge without operational replication
experience. Each changes a plan if ignored:

- **Existing objects are NOT replicated by a new rule.** A new
  `ReplicationConfiguration` rule only replicates objects PUT *after*
  the rule is applied. To replicate existing objects, use S3 Batch
  Operations with the `S3ReplicateObject` operation. This is the #1
  misclassification: the operator sees `Status: Enabled` and assumes
  the historical objects are being copied. They are not.

- **Replica modification sync (Nov 2022+) replicates metadata updates.**
  Before this feature, only the initial PUT replicated. Tag updates,
  ACL changes, and metadata changes on the source were NOT propagated.
  To enable, the rule MUST include `SourceSelectionCriteria {
  ReplicaModifications { Status: Enabled } }`. Without this, source
  tag edits diverge silently from the replica.

- **Delete-marker replication is OFF by default and configured
  separately.** Object replication does NOT imply delete replication.
  The rule needs `DeleteMarkerReplication: { Status: Enabled }`. To
  replicate hard deletes (version-id DELETE), the rule needs
  `DeleteReplication: { Status: Enabled }` (separate from delete
  markers). Most operators only need delete-marker replication.

- **Cross-account replication requires a destination bucket policy.**
  The IAM role's identity-based policy is necessary but NOT sufficient.
  The destination bucket policy MUST allow the source account's role
  ARN to `s3:ReplicateObject`,
  `s3:ReplicateDelete`, AND include the
  `s3:x-amz-source-account` condition for the source account ID. Without
  this, replication fails with AccessDenied that surfaces ONLY in S3
  Server Access Logs.

- **Object ownership defaults to the source account.** If the
  destination bucket has `ObjectOwnership: ObjectWriter` (legacy ACL
  mode), replicas are owned by the source account. The destination
  account cannot read or delete them. Set destination
  `ObjectOwnership: BucketOwnerEnforced` (recommended) or
  `BucketOwnerPreferred` AND include
  `s3:ObjectOwnerOverrideToBucketOwner` in the role + bucket policy.

- **SSE-KMS requires grants on BOTH source and destination keys.**
  Source key grants `kms:Decrypt` to the replication role; destination
  key grants `kms:Encrypt`. Both key policies must be updated — the
  destination key policy is the one most commonly missed.

- **Replication Time Control (RTC) is a per-rule flag.** Add
  `ReplicationTime: { Status: Enabled, Time: { Minutes: 15 } }` AND
  `Metrics: { Status: Enabled, EventThreshold: { Minutes: 15 } }` to
  the rule. Enabling RTC exposes the `PendingReplication`,
  `OperationPendingReplicationCount`, and `BytesPendingReplication`
  CloudWatch metrics. Without RTC, you cannot measure replication lag
  via CloudWatch — only via S3 Server Access Logs.

- **Multiple destination replication (Nov 2022+ GA).** A single source
  bucket can replicate to up to 1,000 destination buckets across
  different Regions and accounts. Each destination is a separate Rule
  with a unique `ID` and `Priority`. Filter overlap is resolved by
  Priority (higher wins); the same object can be replicated to multiple
  destinations in parallel.

- **Replication rules respect `Priority` for overlapping filters.** If
  Rule A (prefix `logs/`, Priority 1) and Rule B (prefix
  `logs/audit/`, Priority 2) overlap, an object under `logs/audit/` is
  replicated by Rule B (higher Priority). Use distinct, non-overlapping
  filters when possible.

- **Batch Operations needs a manifest.** Use S3 Inventory (daily CSV)
  as the manifest source. The Batch Operations job runs as an IAM role
  that needs `s3:GetObject`, `s3:ReplicateObject`, and KMS permissions.
  The job does NOT re-use the bucket's replication role.

- **S3 Replication to multiple destinations does NOT de-dupe.** If the
  same object matches multiple rules, each destination gets its own
  replica. Bandwidth and request costs scale linearly with the number
  of matching destinations.

- **Replication failure does NOT raise a CloudWatch alarm by default.**
  S3 emits the `Replication` metric only when RTC is enabled. Without
  RTC, the only failure signal is missing objects in the destination
  bucket or AccessDenied entries in CloudTrail/S3 Server Access Logs
  on the destination.

- **`ReplicationConfiguration` is a full-replacement API.**
  `put-bucket-replication` REPLACES the entire configuration. To add a
  rule, you MUST first `get-bucket-replication`, append the new rule,
  sort by Priority, then `put-bucket-replication` with the merged
  config. There is no `add-rule` API — forgetting this wipes existing
  rules.

- **Versioning cannot be suspended on a bucket with active replication.**
  Suspending versioning on the source stops new replicates; suspending
  on the destination halts in-flight replicates. Re-enabling may not
  resume the backlog automatically.

- **Object Lock + replication.** If the source has Object Lock enabled,
  replicas inherit the retention lock. The destination MUST also have
  Object Lock enabled at the bucket level BEFORE the first object
  replicates, or the object is rejected.

---

## False-green rule — delivery verification deep dive

**Concrete verification techniques:**

| Technique | Mechanism | What it proves |
|---|---|---|
| Test PUT + `head-object` on destination | Put a sentinel object after the rule change; poll destination | End-to-end replication works for new objects |
| CloudWatch `PendingReplication` trend (RTC) | Alarm on > 0 for > 15 min | Backlog is draining within SLA |
| S3 Server Access Logs on destination | Filter for `Replication` operation with error codes | Cross-account or KMS failures |
| CloudTrail data events on destination | Filter `PutObject` with `replication` request header | Replicates are arriving |
| Batch Operations `S3ReplicateObject` job report | Job completion + FAILED count | Existing-object backfill status |
| Version ID comparison | `head-object` source vs destination | Replica is the same version, not a re-PUT |

**Three-bucket verification protocol (apply on every new rule):**

1. **Sentinel object:** PUT a small unique object (e.g.,
   `__replication_test_<timestamp>`) to the source matching the rule's
   filter. Poll `head-object` on the destination every 5 seconds for
   up to 60 seconds (15 minutes with RTC).
2. **Version ID match:** compare `VersionId` on source and destination.
   They MUST match. Different version IDs mean the destination was
   written by something else, not the replication pipeline.
3. **Delete-marker round-trip (if delete-marker replication is on):**
   delete the sentinel object in the source. Poll the destination for
   a delete marker with the same version ID. If absent after 60 seconds,
   delete-marker replication is broken.

**Surface in the output:** for any rule change, include
`DELIVERY_STATUS: <verified | pending | failed>` and the sentinel
object's version-ID comparison. If `DELIVERY_STATUS` is not `verified`,
do NOT mark the operation COMPLETED.

**Detection of silent replication failure post-deploy:** CloudWatch
alarm on `PendingReplication > 0 for 15 minutes` (RTC required) AND a
daily scheduled Lambda that PUTs a sentinel object and verifies the
replica arrives within 60 seconds. The daily sentinel catches failures
that CloudWatch cannot (because non-RTC buckets emit no metrics).

---

## Recent AWS features (2024-2026)

- **S3 Replication to multiple destinations (Nov 2022 GA, expanded
  2024-2025):** A single source bucket can replicate to up to 1,000
  distinct destination buckets across Regions and accounts. Each
  destination is a separate Rule with a unique ID and Priority. Same-
  object-same-multi-destination is supported (no de-dupe).

- **Replica modification sync (Nov 2022 GA, default-off through 2025):**
  Metadata changes (tags, ACLs, content-type) on the source now
  replicate to existing replicas when
  `SourceSelectionCriteria.ReplicaModifications.Status: Enabled`. Before
  this, only the initial PUT replicated.

- **Replication Time Control CloudWatch metrics (2024):**
  `PendingReplication`, `OperationPendingReplicationCount`, and
  `BytesPendingReplication` are now available in the `AWS/S3` namespace
  with 1-minute period. Requires RTC on the rule. Use these for SLA
  alarms.

- **S3 Batch Operations `S3ReplicateObject` operation (2023+):**
  Built-in operation type for backfilling existing objects through the
  replication pipeline. Manifest source is typically S3 Inventory.
  Supports customer-managed KMS keys.

- **Object Lock + replication (2024):** Source Object Lock retention
  now replicates to the destination provided the destination has Object
  Lock enabled at the bucket level BEFORE the first locked object
  arrives. Destination Object Lock cannot be enabled after a locked
  replica is rejected.

- **`BucketOwnerEnforced` ACL mode (2021+, recommended 2024+):**
  Eliminates the ACL ownership problem for cross-account replication.
  Replicas are owned by the destination account automatically; the
  `s3:ObjectOwnerOverrideToBucketOwner` permission is still required in
  the role + bucket policy.

- **S3 Inventory daily manifest with replication status (2024):** The
  Inventory CSV now includes a `Replication Status` column per object,
  enabling filtered Batch Operations manifests (e.g., only `FAILED`
  objects).

- **CloudTrail data events for `Replication` operation (2024-2025):**
  CloudTrail now logs the `Replication` operation type on the
  destination bucket, making cross-account AccessDenied failures
  observable without S3 Server Access Logs.
