# Advanced Patterns — OpenSearch Snapshot Troubleshooter
Edge-case catalogs, expert-knowledge deep dives, and recent AWS features, moved verbatim from SKILL.md.

### Step 0: Non-obvious behaviours that change diagnosis
- **Automated snapshot bucket is read-only and service-managed.**
  The `cs-automated` / `cs-automated-enc` repositories write to an
  AWS-managed bucket you cannot list with `aws s3 ls` without an
  explicit grant. Use `_snapshot/cs-automated/_all` against the
  domain endpoint to enumerate automated snapshots.
- **Manual snapshot IAM role uses a service-principal trust, not an
  sts:ExternalId trust.** The trust policy lists
  `"Service": "opensearchservice.amazonaws.com"` (legacy:
  `es.amazonaws.com`). Cross-account additionally requires
  `aws:SourceAccount` and `aws:SourceArn` conditions — without
  them the confused-deputy check fails verification.
- **The bucket policy grants the ROLE, not the service principal.**
  Operators frequently write a bucket policy keyed to
  `"Service": "opensearchservice.amazonaws.com"`. The role's
  session ARN does not match the service principal and verification
  fails. The service principal goes in the role trust, not the
  bucket policy.
- **Snapshot blobs are deduplicated across snapshots.** Each shard
  is a tree of `index-N` segments referenced by per-snapshot
  `snap-*.dat` manifests. Deleting "old" objects corrupts every
  snapshot that shared the segment. An S3 lifecycle rule scoped to
  the whole bucket will silently invalidate historical snapshots.
- **OpenSearch runs one snapshot per repository at a time.** A
  second snapshot returns `ConcurrentSnapshotExecutionException`.
  Automated and manual snapshots into the SAME repository collide;
  use distinct `base_path` prefixes for distinct schedules.
- **Restore does NOT overwrite existing indices.** If an index or
  alias with the snapshot's name already exists, restore skips or
  fails with `resource_already_allocated_exception`. Use
  `rename_pattern`/`rename_replacement` on restore, or delete the
  conflicting index first.
- **UltraWarm/Cold migration requires replicas and node count.**
  Migration to warm requires the index to have at least one
  assigned replica; migration fails on a primary-only index. Cold
  storage requires the warm tier enabled (warm_count >= 3).
- **Cross-Region async replication is index-level.** `_plugins/_replication`
  replicates indices one at a time from leader to follower. Replication
  stalls briefly when the leader takes a snapshot (expected), and
  fails permanently if the follower is on a lower engine version.
- **`_snapshot/<repo>/_status` is the source of truth.** `state`
  (`SUCCESS`, `IN_PROGRESS`, `FAILED`, `PARTIAL`) plus per-shard
  `stage` (`STARTED`, `TRANSLOCATING`, `FINALIZE`) tell you where
  the snapshot is stuck. Operators who "watch S3" miss the
  in-cluster state machine.
- **PARTIAL is not FAILED.** A `PARTIAL` snapshot is one where some
  primary shards failed (cluster red) but the rest succeeded. The
  snapshot is usable for the successful shards. Operators who
  "got a SUCCESS in S3" sometimes have a PARTIAL they did not notice.
- **Audit logs to S3 require LogPublishingOptions.AuditLogs ENABLED
  AND the S3 bucket policy granting the delivery principal.** The
  bucket policy for CloudTrail must grant `cloudtrail.amazonaws.com`
  with `aws:SourceArn` condition; for Firehose must grant
  `firehose.amazonaws.com` with `aws:SourceAccount`.
- **`repository_verification_exception` is the #1 misdiagnosed
  snapshot error.** Operators reach for "snapshot is corrupt." The
  actual cause is almost always IAM (role trust, role policy, or
  bucket policy). Probe IAM before probing snapshot integrity.

## Deep reference
### Symptom → layer decision matrix

```
Error string                                        → Layer
repository_verification_exception                    → REPOSITORY_VERIFICATION / IAM_ROLE_S3_ACCESS
PUT _snapshot 4xx                                    → REPOSITORY_REGISTRATION
ConcurrentSnapshotExecutionException                 → CONCURRENT_SNAPSHOT_LIMIT
snapshot stuck IN_PROGRESS; unassigned shards        → SNAPSHOT_TIMEOUT
restore 400 version_not_supported                    → RESTORE_VERSION_CONFLICT
restore resource_already_allocated_exception         → RESTORE_ALIAS_CONFLICT
migration_failed to warm/cold                        → COLD_STORAGE_MIGRATION
SnapshotMissingException after N days                → S3_LIFECYCLE_DELETION
plugins/replication status SYNCING lag rising        → CROSS_REGION_REPLICATION
cat/recovery stuck at 5%                             → SHARD_ALLOCATION_RESTORE
CorruptedIndexException index-N                      → MANIFEST_CORRUPTION
audit bucket empty; AuditLogs DISABLED               → CUR_AUDIT_LOG_CONFIG
```

### Snapshot role trust policy template (same-account)

```json
{"Version": "2012-10-17", "Statement": [{
  "Effect": "Allow",
  "Principal": {"Service": "opensearchservice.amazonaws.com"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {"aws:SourceAccount": "<account-id>"},
    "ArnLike": {"aws:SourceArn": "arn:aws:es:<region>:<account-id>:domain/<domain-name>"}
  }
}]}
```

### Engine-version compatibility matrix

| Source engine | Target engine | Direct restore? |
|---|---|---|
| ES 7.0–7.10 | OpenSearch 1.x | Yes |
| ES 7.0–7.10 | OpenSearch 2.x | No — needs intermediate 1.x |
| OpenSearch 1.x | OpenSearch 1.x same/higher | Yes |
| OpenSearch 1.x | OpenSearch 2.x | Yes (one major up) |
| OpenSearch 2.x | OpenSearch 2.y ≥ 2.x | Yes |
| OpenSearch 2.x | OpenSearch 2.y < 2.x | No |

### UltraWarm / Cold tier requirements

| Tier | Minimum nodes | Notes |
|---|---|---|
| Hot (data) | 2 (HA) | Required always |
| Warm (UltraWarm) | 3 | Added via `update-domain-config` |
| Cold | 1 (with warm) | Requires warm tier enabled first |

Migration to warm requires the index to have at least one assigned
replica. Cold indices are searchable via `cold-search` plugin;
queries are slower (disk-backed).

### Snapshot state transitions

| State | Meaning |
|---|---|
| `INIT` | Request accepted, shards not yet started |
| `STARTED` | Shard snapshots in progress |
| `TRANSLOCATING` | Lucene segments being moved to repository |
| `FINALIZE` | Writing snapshot manifest (`snap-*.dat`) |
| `SUCCESS` | Metadata written; usable for restore |
| `FAILED` | One or more primary shards failed; NOT usable |
| `PARTIAL` | Some shards failed; usable for successful shards |
| `IN_PROGRESS` | Visible in `_snapshot/_status` while active |

### Snapshot thread pool sizing

| Setting | Default | Effect |
|---|---|---|
| `thread_pool.snapshot.size` | ~#CPUs/4 | Concurrent shard-snapshot operations per node |
| `thread_pool.snapshot.queue_size` | 350 | Queue depth before rejects |
| `indices.recovery.max_bytes_per_sec` | 40mb (managed) | Restore shard-recovery throttle |

## Recent AWS features (2024-2026)
- **OpenSearch cross-Region async replication (2024-2025):**
  Index-level async replication via `_plugins/_replication`. Stalls
  when the leader takes a snapshot (expected). Watch
  `last_updated_lag_seconds` rather than `last_replication_completion`.
- **Cold storage GA (2024):** Searchable cold tier via `cold-search`
  plugin. Migration requires warm tier enabled and the index to
  have a warm replica. Operators who "set the ISM policy to cold"
  without enabling warm see `migration_failed`.
- **Snapshot upgrade flow (2024):** OpenSearch 1.x intermediate
  domains read 7.x snapshots and emit 1.x snapshots for 2.x targets.
  Direct 7.x → 2.x restore returns `version_not_supported`.
- **Managed OpenSearch 2.13+ (2025):** Snapshot repository supports
  `server_side_encryption` setting explicitly. Bucket-side SSE-KMS
  still requires the role to have `kms:GenerateDataKey`.
