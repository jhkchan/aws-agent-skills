---
description: Diagnose Amazon OpenSearch Service snapshot and restore failures through a thirteen-category diagnostic tree (repository registration, verification, IAM role, snapshot timeout, restore version conflict, alias conflict, UltraWarm/Cold migration, S3 lifecycle, cross-region replication, shard allocation, manifest corruption, concurrent snapshot, audit log config) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "OpenSearch snapshot failed"
  - "OpenSearch snapshot stuck"
  - "OpenSearch snapshot timeout"
  - "PUT _snapshot failed"
  - "repository verification failed"
  - "repository_verification_exception"
  - "ConcurrentSnapshotExecutionException"
  - "OpenSearch restore failed"
  - "restore version_not_supported"
  - "OpenSearch alias conflict restore"
  - "resource_already_allocated_exception"
  - "UltraWarm migration failed"
  - "Cold storage migration_failed"
  - "SnapshotMissingException"
  - "cross-region replication lag OpenSearch"
  - "shard allocation restore OpenSearch"
  - "snapshot manifest corruption"
  - "CorruptedIndexException snapshot"
  - "OpenSearch audit logs S3"
  - "troubleshoot OpenSearch snapshot"
  - "diagnose OpenSearch snapshot"
routes_to: opensearch-snapshot-troubleshooter
---

# /aws:troubleshoot-opensearch-snapshot

Activate the `opensearch-snapshot-troubleshooter` skill and diagnose
an Amazon OpenSearch Service snapshot or restore failure through the
thirteen-category diagnostic tree.

## What it does

Reads a symptom description (error message, observed behaviour,
repository/snapshot context) plus the domain configuration, then
walks the symptom-driven diagnostic tree to a root cause with
positive evidence:

1. **Pre-flight** — domain state and ChangeProgressDetails
   (`describe-domain`), recent application logs (`filter-log-events`
   on `/aws/opensearch/domains/<domain>/application-logs`), AWS
   Health (regional incidents). Short-circuits on
   `UpgradeProcessing: true`, `RollbackInProgress`, or red cluster
   health.
2. **Symptom entry** — map the error to one of:
   repository_verification_exception, PUT _snapshot 4xx, snapshot
   stuck IN_PROGRESS, restore version_not_supported, restore
   resource_already_allocated_exception, migration_failed,
   SnapshotMissingException, ConcurrentSnapshotExecutionException,
   CorruptedIndexException, replication lag, audit bucket empty.
3. **Layer-specific probes** —
   - Registration: `curl _snapshot/<repo>` existence, PUT body
     completeness (iam_role_arn, region, base_path), trust policy
     for service principal.
   - Verification / IAM: `get-bucket-policy` principal (role ARN
     vs service principal), `simulate-principal-policy` for the
     authoritative decision, KMS permissions for SSE-KMS buckets,
     verification-file asymmetry.
   - Timeout: `_snapshot/<repo>/<snap>/_status`, `_cat/shards` for
     UNASSIGNED, `_cat/master` for elected master health,
     `_cat/thread_pool/snapshot` for rejects.
   - Version: `_snapshot/<repo>/<snap>` engine_version vs target
     `describe-domain` EngineVersion; snapshot-upgrade flow for
     cross-major restores.
   - Alias conflict: `_cat/aliases` and `_cat/indices` matching
     snapshot index names; rename-on-restore fix.
   - UltraWarm/Cold: `describe-domain-config` WarmEnabled/WarmCount,
     `_plugins/_ism/explain`, `_cat/indices` replica count.
   - S3 lifecycle: `get-bucket-lifecycle-configuration` rules,
     `cloudtrail lookup-events` for lifecycle DeleteObject.
   - Concurrent: `_snapshot/_status` for IN_PROGRESS snapshot.
   - Manifest: `_snapshot/<repo>/<snap>` failures array, `s3api
     head-object` for zero-byte blobs.
   - Replication: `_plugins/_replication/<index>/_status`,
     leader `_cluster/settings`.
   - Audit/cur: `describe-domain-config` LogPublishingOptions,
     audit bucket policy for CloudTrail/Firehose delivery.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom) or INSUFFICIENT_DATA (all probes pass;
   escalate to opensearch-cluster-troubleshooter or AWS Support).

Emits a deterministic diagnostic block per target:

```text
TARGET: <domain-name with repository/snapshot id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-3 sentences naming the failed layer and the failing probe>
LAYER: <REPOSITORY_REGISTRATION | REPOSITORY_VERIFICATION |
        IAM_ROLE_S3_ACCESS | SNAPSHOT_TIMEOUT |
        RESTORE_VERSION_CONFLICT | RESTORE_ALIAS_CONFLICT |
        COLD_STORAGE_MIGRATION | S3_LIFECYCLE_DELETION |
        CROSS_REGION_REPLICATION | SHARD_ALLOCATION_RESTORE |
        MANIFEST_CORRUPTION | CONCURRENT_SNAPSHOT_LIMIT |
        CUR_AUDIT_LOG_CONFIG | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command or API call>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "OpenSearch snapshot verification fails"
- "PUT _snapshot returns 4xx"
- "snapshot stuck IN_PROGRESS for hours"
- "restore returns version_not_supported"
- "restore resource_already_allocated_exception"
- "UltraWarm migration_failed"
- "snapshot SnapshotMissingException"
- "ConcurrentSnapshotExecutionException"
- "OpenSearch audit logs not landing in S3"

A bare domain name + any snapshot error verb ("snapshot failing",
"restore broken", "verification failed") also routes here via the
orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, intermittent
  vs persistent pattern, repository name, snapshot id.
- Domain configuration: name, EngineVersion, ClusterConfig,
  SnapshotOptions, LogPublishingOptions, WarmEnabled, ChangeProgressDetails.
- For live-account diagnosis: repository and snapshot context —
  S3 bucket, IAM role ARN, source/target domain for restore. The
  skill uses `describe-domain`, `describe-domain-config`,
  `get-bucket-policy`, `get-bucket-lifecycle-configuration`,
  `simulate-principal-policy`, `cloudtrail lookup-events`,
  `_snapshot/_status`, `_cat/recovery`, `_cat/shards`,
  `_cluster/health`, `_plugins/_ism/explain`,
  `_plugins/_replication/<index>/_status`.

## Outputs

- One diagnostic block per target domain/repository/snapshot.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: bucket-policy update, repository re-register,
  version upgrade, rename-on-restore, warm-tier enablement, lifecycle
  rule scoping, schedule change, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for OpenSearch snapshot
  failures).
- `/aws:troubleshoot-opensearch-cluster` for cluster-level stability
  incidents (red cluster, node failures) not tied to snapshots.
- `/aws:audit-opensearch-domain` for configuration posture audits on
  the same domain (security exposure, encryption, logging coverage).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  snapshot role is denied by an SCP, permissions boundary, or
  resource-based policy on the S3 bucket.
