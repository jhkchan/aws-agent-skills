---
name: opensearch-snapshot-troubleshooter
description: 'Diagnoses Amazon OpenSearch Service snapshot failures through a thirteen-category diagnostic tree: S3 repository registration errors (PUT _snapshot), repository verification failure, IAM role missing s3:PutObject / s3:ListBucket / s3:GetObject on the snapshot bucket, snapshot stuck or timeout (unassigned shards, cluster red), restore into a different domain (engine-version mismatch — restore requires same version or higher), index alias conflict during restore, snapshot to UltraWarm / Cold storage, S3 bucket lifecycle policy deleting snapshot blobs, cross-region async replication stalls, shard allocation throttling during restore, snapshot manifest corruption, concurrent snapshot limit (one per repository — ConcurrentSnapshotExecutionException), and Cost and Usage Report / audit-log snapshot configuration. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and domain configuration. Live-account diagnosis uses aws opensearch describe-domain, describe-domain-config, list-domain-names, aws es describe-elasticsearch-domain (legacy), aws s3api get-bucket-policy / get-bucket-lifecycle-configuration, aws iam get-role / simulate-principal-policy, aws logs filter-log-events on...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an OpenSearch Service snapshot failure (S3 repository registration error, repository verification failure, snapshot stuck or timeout, restore failure, alias conflict on restore, UltraWarm/Cold migration failure, snapshots missing due to S3 lifecycle, cross-region replication lag, shard allocation failure during restore, manifest corruption, concurrent snapshot rejection, audit-log/CUR snapshot misconfig), walking a symptom to the failed layer with verify and fix commands, or triaging a "OpenSearch snapshots are broken" page where the root cause may be repository registration, IAM role, bucket lifecycle, cluster state, or version compatibility — not necessarily the OpenSearch domain itself.
  when_not_to_use: Cluster-level stability incidents not tied to snapshots (use opensearch-cluster-troubleshooter), OpenSearch Serverless collection backup (Serverless uses a different snapshot model), index mapping / query performance tuning, S3 bucket public-access posture audits (use s3-public-access-auditor), or VPC endpoint posture audits for the OpenSearch domain. This skill diagnoses snapshot and restore failures; it does not tune shard count for indexing throughput or audit steady-state configuration posture.
  activation_triggers: OpenSearch snapshot failed, OpenSearch snapshot stuck, OpenSearch snapshot timeout, PUT _snapshot failed, repository verification failed, repository_verification_exception, ConcurrentSnapshotExecutionException, OpenSearch restore failed, restore version_not_supported, OpenSearch alias conflict restore, resource_already_allocated_exception, UltraWarm migration failed, Cold storage migration_failed, SnapshotMissingException, cross-region replication lag, shard allocation restore, snapshot manifest corruption, CorruptedIndexException snapshot, OpenSearch audit logs S3, troubleshoot OpenSearch snapshot
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "snapshot stays IN_PROGRESS for hours", "restore returns 400"), optionally paired with the domain configuration (describe-domain output) and recent OpenSearch application logs, OR (b) a DomainName plus snapshot/repository context (repository name, snapshot id, S3 bucket, IAM role ARN, source/target domain for restore) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {REPOSITORY_REGISTRATION, REPOSITORY_VERIFICATION, IAM_ROLE_S3_ACCESS, SNAPSHOT_TIMEOUT, RESTORE_VERSION_CONFLICT, RESTORE_ALIAS_CONFLICT, COLD_STORAGE_MIGRATION, S3_LIFECYCLE_DELETION, CROSS_REGION_REPLICATION, SHARD_ALLOCATION_RESTORE, MANIFEST_CORRUPTION, CONCURRENT_SNAPSHOT_LIMIT, CUR_AUDIT_LOG_CONFIG, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "OpenSearch domain prod-logs-cluster fails to register

    the manual S3 repository. PUT _snapshot/s3-backups returns

    500 with ''repository_verification_exception'' and the IAM role

    arn:aws:iam::111111111111:role/opensearch-snapshot-role is

    listed in the trust policy of the domain but the S3 bucket

    policy does not list the snapshot role ARN."

    DomainName: prod-logs-cluster

    EngineVersion: OpenSearch_2.13

    Repository: s3-backups

    Bucket: prod-os-snapshots-us-east-1

    SnapshotRoleArn: arn:aws:iam::111111111111:role/opensearch-snapshot-role

    Last log line: "repository_verification_exception: [[s3-backups]] verification failed"'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: OpenSearch, snapshot, repository, S3, PUT _snapshot, verification, restore, UltraWarm, Cold storage, shard allocation, manifest corruption, ConcurrentSnapshotExecutionException, cross-region replication, lifecycle policy, alias conflict, troubleshooting
  tags: opensearch, analytics, troubleshooting, snapshot, s3, backup, restore, ultrawarm, iam-role, repository
---

# OpenSearch Snapshot Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  `repository_verification_exception` → REPOSITORY_VERIFICATION /
  IAM_ROLE_S3_ACCESS; `PUT _snapshot` returns 4xx / 5xx →
  REPOSITORY_REGISTRATION; snapshot stays `IN_PROGRESS` for hours →
  SNAPSHOT_TIMEOUT / SHARD_ALLOCATION_RESTORE; restore returns 400
  with version message → RESTORE_VERSION_CONFLICT; restore returns
  `resource_already_allocated_exception` → RESTORE_ALIAS_CONFLICT;
  `ConcurrentSnapshotExecutionException` → CONCURRENT_SNAPSHOT_LIMIT;
  snapshots vanish from S3 after N days → S3_LIFECYCLE_DELETION;
  `migration_failed` to warm/cold → COLD_STORAGE_MIGRATION;
  `SnapshotException` reading `index-N` blob → MANIFEST_CORRUPTION;
  cross-Region replication lag → CROSS_REGION_REPLICATION; audit
  logs empty in S3 → CUR_AUDIT_LOG_CONFIG.
- **Always verify with a probe, never guess.** Each layer has a
  single command that proves or disproves it. A `ROOT_CAUSE_IDENTIFIED`
  verdict requires positive evidence — a failing probe that matches
  the symptom.
- **Manual and automated snapshots use different repositories.**
  Automated snapshots write to a service-managed S3 bucket
  (`cs-automated` / `cs-automated-enc`) that you cannot list directly.
  Manual snapshots write to a customer-owned S3 bucket via a customer
  IAM role. Operators "cannot find the snapshot in S3" while
  debugging an automated snapshot are looking in the wrong bucket.
- **Restore requires target engine version same or higher than
  source.** A snapshot on OpenSearch 2.13 restores into 2.13 or
  higher, fails on 2.11 with `version_not_supported`. ES 7.x →
  OpenSearch 2.x requires the snapshot-upgrade flow via 1.x.
- **One snapshot per repository at a time.** A second snapshot into
  the same repository returns `ConcurrentSnapshotExecutionException`.
  Automated and manual schedules colliding on the same repository
  is the most common cause.

## Mindset

A failing OpenSearch snapshot is usually a permissions, lifecycle,
or version-compatibility incident wearing a cluster costume. The
domain is healthy in the majority of cases; the broken thing is
the IAM role assumed for S3, the bucket policy that does not trust
the role, an S3 lifecycle rule expiring snapshot blobs, a version
mismatch between source and target, or an alias collision at
restore time. Treat the OpenSearch cluster as innocent until the
repository registration, IAM role, bucket lifecycle, and version
layers are proven clean. Senior analytics engineers do not start
by raising node count; they start with `_snapshot/<repo>/_status`,
`get-bucket-policy`, and `simulate-principal-policy`.

## Philosophy

- **Repository registration is a three-way contract.** A working
  S3 snapshot repository requires (1) an IAM role the OpenSearch
  domain can assume, (2) a trust policy on that role listing the
  OpenSearch service principal for the account, and (3) a bucket
  policy granting the role `s3:PutObject`/`s3:ListBucket`/`s3:GetObject`/
  `s3:DeleteObject`/`s3:GetBucketLocation`. Any one missing and
  registration either fails outright or succeeds with verification
  failure on the first snapshot. Operators who "added S3 permissions
  to the role" but still see `repository_verification_exception`
  usually miss the bucket-policy side.
- **Snapshot and restore are NOT symmetric on version.** A snapshot
  on OpenSearch 2.x restores into any 2.y ≥ 2.x. It CANNOT restore
  into a lower 2.x, into ES 7.x, or skip a major version. The
  snapshot-upgrade flow (7.x → 1.x → 2.x) handles cross-major
  restore. Operators who "took a snapshot in prod, tried to restore
  into a lower-version dev domain" hit `version_not_supported` on
  the first shard and assume corruption.
- **Restore into a non-empty cluster fights aliases and existing
  indices.** `_restore` opens snapshot indices by their original
  names. If an index with the same name (or the alias the snapshot
  references) already exists, restore fails with
  `resource_already_allocated_exception` or silently skips. The fix
  is `rename_pattern`/`rename_replacement` on restore, or delete
  the conflicting index/alias first — not to retry.
- **S3 lifecycle rules DO delete snapshot blobs.** Snapshots are
  trees of `index-*`, `snap-*` blobs referenced by repository
  metadata. Segments are deduplicated across snapshots. An S3
  lifecycle rule that expires "all objects" after N days deletes
  blobs while the repository still lists the snapshot. The next
  restore fails with `SnapshotMissingException`. Always scope
  lifecycle rules by prefix when a bucket holds snapshot repositories.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `repository_verification_exception` on `PUT _snapshot` or first snapshot | REPOSITORY_VERIFICATION / IAM_ROLE_S3_ACCESS | `get-bucket-policy`, `iam simulate-principal-policy` on snapshot role |
| `PUT _snapshot/<repo>` returns 4xx; repository never registers | REPOSITORY_REGISTRATION | `curl $ENDPOINT/_snapshot/<repo>` — does the repo exist? `get-role` trust policy |
| Snapshot stays `IN_PROGRESS`; `_cat/shards` shows UNASSIGNED | SNAPSHOT_TIMEOUT / SHARD_ALLOCATION_RESTORE | `_snapshot/<repo>/<snap>/_status`, `_cat/shards?v&h=index,shard,prirep,state,unassigned.reason` |
| `_restore` returns 400 with `version_not_supported` | RESTORE_VERSION_CONFLICT | `_snapshot/<repo>/<snap>` — read `engine_version` |
| `_restore` of alias-bearing indices returns `resource_already_allocated_exception` | RESTORE_ALIAS_CONFLICT | `_cat/aliases?v&s=alias:desc` for the alias in the snapshot |
| `migration_failed` to UltraWarm/Cold; warm node count < 3 | COLD_STORAGE_MIGRATION | `describe-domain-config` (WarmEnabled, WarmCount), `_nodes/_all` |
| `_snapshot/<repo>/_status` returns `SNAPSHOT_FAILED`; S3 lifecycle shows `ExpirationInDays` | S3_LIFECYCLE_DELETION | `get-bucket-lifecycle-configuration`, `s3 ls s3://<bucket>/<prefix> --recursive` |
| Cross-Region async replication lags; follower `SYNCING` lag rising | CROSS_REGION_REPLICATION | `_plugins/_replication/<index>/_status`, source `_cluster/settings` |
| `_restore` stalls; `_cat/recovery` shows throttle at low % | SHARD_ALLOCATION_RESTORE | `_cat/recovery?v&h=index,shard,time,stage,percent` |
| `SnapshotException` reading `index-N` blob; `_status` shows `INTERNAL_ERROR` | MANIFEST_CORRUPTION | `s3 head-object` for size 0; `s3 ls` for missing blob |
| Second snapshot into same repo fails immediately with `ConcurrentSnapshotExecutionException` | CONCURRENT_SNAPSHOT_LIMIT | `_snapshot/_status` — is another snapshot `IN_PROGRESS`? |
| Audit S3 bucket empty; `LogPublishingOptions.AuditLogs: DISABLED` | CUR_AUDIT_LOG_CONFIG | `describe-domain-config` LogPublishingOptions, `s3 ls s3://<audit-bucket>/` |
| None of the above; cluster red; multiple indices unassigned | INSUFFICIENT_DATA | `_cluster/health`, `describe-domain` (ClusterConfig) |

## Pre-flight: domain state and gather-info gate

Gather the canonical configuration and short-circuit on domain
states that mimic snapshot failures. Misclassifying these produces
hours of snapshot debugging for a problem that is not a snapshot
problem.

```bash
# 1. Domain configuration (EngineVersion, ClusterConfig, EBSOptions,
#    SnapshotOptions, LogPublishingOptions, WarmEnabled,
#    ColdStorageOptions, ChangeProgressDetails)
aws opensearch describe-domain --domain-name <domain> --output json
aws opensearch describe-domain-config --domain-name <domain> --output json

ENDPOINT=$(aws opensearch describe-domain --domain-name <domain> \
  --query 'Domain.Endpoint' --output text)

# 2. Recent application logs (snapshot / restore / migration events)
aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/application-logs \
  --start-time $(date -d '-60 minutes' +%s)000 \
  --filter-pattern '"repository_verification_exception" OR "SnapshotException" OR "ConcurrentSnapshotExecutionException" OR "migration_failed" OR "version_not_supported"' \
  --output json

# 3. Repository + snapshot status
curl -sS "https://$ENDPOINT/_cat/repositories?v"
curl -sS "https://$ENDPOINT/_snapshot/_status" | jq '.snapshots[] | {repository, snapshot, state}'

# 4. S3 bucket policy + lifecycle for the snapshot bucket
aws s3api get-bucket-policy --bucket <bucket> --output json 2>/dev/null || echo "No bucket policy"
aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json

# 5. Snapshot role trust + simulated permissions
aws iam get-role --role-name <role-name> --query 'Role.AssumeRolePolicyDocument' --output json
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::<account>:role/<role>" \
  --action-names s3:PutObject s3:ListBucket s3:GetObject s3:DeleteObject s3:GetBucketLocation \
  --resource-arns "arn:aws:s3:::<bucket>" "arn:aws:s3:::<bucket>/*" --output json

# 6. CloudWatch automated-snapshot-failure metric
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name AutomatedSnapshotFailure \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 day' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 7. AWS Health (regional OpenSearch events, scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING --region us-east-1 --output json
```

### Domain-state short-circuit

| `DomainStatus` / `ChangeProgressDetails` | Effect on diagnosis |
|---|---|
| `Processing: false`, no `PendingChanges` | Domain steady; proceed with symptom-driven diagnosis. |
| `Processing: true` (blue/green deployment) | Configuration update in flight. Snapshots can run but may be slow. Wait for `Processing: false`. |
| `UpgradeProcessing: true` | Engine upgrade in flight. Snapshots can fail verification. Wait for `UpgradeStatus: Succeeded`. |
| `UpgradeStatus: RollbackInProgress` | Last upgrade failed; cluster is on prior engine. A restore that assumed higher version fails. Re-read `EngineVersion`. |
| `ClusterConfig.DedicatedMasterEnabled: false` and cluster red | Heavy snapshot can starve the elected master. This is a cluster-sizing issue, not snapshot config. |

If input is malformed (missing DomainName, absent symptom, no
repository/snapshot id for restore debugging), emit:

```text
TARGET: <domain-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (error string or observed behaviour) and the
  DomainName plus, for restore errors, the repository name and
  snapshot id.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt for: (1) the exact error string or observed
  symptom, (2) the DomainName and EngineVersion, and (3) for
  restore errors, the source and target EngineVersions plus the
  repository name and snapshot id.
```

## Process — Diagnostic decision tree (apply in symptom order)

Symptom-driven. Pick the entry point based on the observed symptom,
then walk the layer-specific probes in order. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the
symptom.**

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

### Step 1: Repository registration & verification layer

Entry: `PUT _snapshot/<repo>` returns 4xx / 5xx, or first snapshot
fails with `repository_verification_exception`.

1. **Does the repository exist?**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>" | jq '.'
   ```
   - 404 → never registered; re-issue `PUT _snapshot`.
2. **Was the registration body correct?** Minimum body for an S3
   repository on a managed domain:
   ```json
   {"type": "s3", "settings": {
     "bucket": "<bucket>", "region": "<bucket-region>",
     "base_path": "<prefix>",
     "iam_role_arn": "arn:aws:iam::<account>:role/<role>",
     "compress": true}}
   ```
   - Missing `iam_role_arn` → registration succeeds but writes fail.
     **REPOSITORY_REGISTRATION.**
   - `region` missing and bucket is in a different Region →
     verification fails. **REPOSITORY_REGISTRATION.**
   - `base_path` overlaps another repository's prefix → manifest
     collision; both repositories become corrupt.
3. **Is the snapshot role's trust policy correct?**
   ```bash
   aws iam get-role --role-name <role-name> \
     --query 'Role.AssumeRolePolicyDocument' --output json | jq '.'
   ```
   - Trust MUST list `"Service": "opensearchservice.amazonaws.com"`.
   - Cross-account: MUST include `aws:SourceAccount` and `aws:SourceArn`
     conditions on the principal. **REPOSITORY_REGISTRATION.**

### Step 2: Repository verification & IAM role layer

Entry: `repository_verification_exception`,
`repository_verification_failed_exception`, or every snapshot attempt
fails.

1. **Bucket policy — does it grant the snapshot ROLE?**
   ```bash
   aws s3api get-bucket-policy --bucket <bucket> --output json | jq '.'
   ```
   - Policy MUST grant the snapshot role ARN the actions
     `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`,
     `s3:GetBucketLocation` on `arn:aws:s3:::<bucket>` and
     `arn:aws:s3:::<bucket>/*`.
   - Bucket policy keyed to the SERVICE PRINCIPAL is incorrect — the
     role's session ARN does not match. **IAM_ROLE_S3_ACCESS.**
   - Missing `s3:GetBucketLocation` → S3 client cannot resolve Region.
     **IAM_ROLE_S3_ACCESS.**
   - Missing `s3:PutObjectAcl` for cross-account → cross-account write
     fails the ACL step. **IAM_ROLE_S3_ACCESS.**
2. **Role policy — authoritative simulation.**
   ```bash
   aws iam simulate-principal-policy \
     --policy-source-arn "arn:aws:iam::<account>:role/<role>" \
     --action-names s3:PutObject s3:ListBucket s3:GetObject s3:DeleteObject s3:GetBucketLocation \
     --resource-arns "arn:aws:s3:::<bucket>" "arn:aws:s3:::<bucket>/*" --output json
   ```
   - Any action that returns `implicitDeny` or `explicitDeny` confirms
     the role is missing the permission. **IAM_ROLE_S3_ACCESS.**
3. **SSE-KMS bucket — does the role have KMS permissions?**
   ```bash
   aws s3api get-bucket-encryption --bucket <bucket> --output json
   aws iam simulate-principal-policy --policy-source-arn "<role-arn>" \
     --action-names kms:Decrypt kms:GenerateDataKey \
     --resource-arns "<kms-key-arn>" --output json
   ```
   - SSE-KMS bucket where the role lacks `kms:GenerateDataKey` → first
     object PUT fails with `AccessDenied` from KMS. **IAM_ROLE_S3_ACCESS.**
4. **Verification-file check.** OpenSearch writes a
   `verification-file-<uuid>` object during verification, then reads
   it back. If `s3 ls s3://<bucket>/<prefix>/verification-file-*`
   shows the object, write succeeded; failure is read-path (KMS,
   policy, Region). If absent, failure is write-path (IAM, bucket
   policy, wrong `base_path`).

If IAM is correct but verification still fails, emit
REPOSITORY_VERIFICATION with the verification-file evidence.

### Step 3: Snapshot timeout & shard allocation layer

Entry: snapshot stays `IN_PROGRESS` for hours, or returns
`SNAPSHOT_FAILED` with `master_not_discovered_exception` /
`process_cluster_event_timeout_exception`.

1. **Snapshot status — which shard is stuck?**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>/_status?human" | \
     jq '.snapshots[0].shards_stats, .snapshots[0].indices[].shards.stats'
   ```
   - `stage: INIT` shards (never started) → snapshot thread blocked on
     master event.
2. **Cluster health and shard assignment.**
   ```bash
   curl -sS "https://$ENDPOINT/_cluster/health?pretty"
   curl -sS "https://$ENDPOINT/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason" | grep -i unassigned
   ```
   - Cluster red → snapshot will go `PARTIAL` or `FAILED`. Root cause
     is the missing primary shard, not the snapshot.
3. **Master node health.**
   ```bash
   curl -sS "https://$ENDPOINT/_cat/master?v"
   curl -sS "https://$ENDPOINT/_nodes/_master/jvm,process"
   ```
   - `master_not_discovered_exception` during snapshot → elected master
     overloaded. Dedicated master count < 3 or master heap > 30 GB.
4. **Snapshot thread pool saturation.**
   ```bash
   curl -sS "https://$ENDPOINT/_cat/thread_pool/snapshot?v&h=name,active,queue,rejected"
   ```
   - `rejected > 0` → snapshot thread pool saturated; queue full.
     Raise the thread pool or stop competing work.

Emit SNAPSHOT_TIMEOUT when the snapshot thread is blocked; emit
SHARD_ALLOCATION_RESTORE when recovery throttling starves a restore.

### Step 4: Restore version-compatibility layer

Entry: `_restore` returns 400 with `version_not_supported`,
`snapshot_restore_failure`.

```bash
curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>" | \
  jq '.snapshots[0].version.id, .snapshots[0].engine_version'
```

Compare with target `EngineVersion` from `describe-domain`. Source >
Target → restore fails on first shard. **RESTORE_VERSION_CONFLICT.**

For 7.x → 2.x restores, use the snapshot-upgrade flow: restore into
an intermediate 1.x domain, snapshot from there, then restore into
the 2.x target.

### Step 5: Restore alias conflict layer

Entry: `_restore` returns `resource_already_allocated_exception` or
silently skips indices.

```bash
curl -sS "https://$ENDPOINT/_cat/aliases?v&s=alias:desc" | grep -E "<pattern>"
curl -sS "https://$ENDPOINT/_cat/indices/<pattern>?v"
```

Any alias or index matching a name in the snapshot blocks restore.
**RESTORE_ALIAS_CONFLICT.**

Fix by renaming on restore or by deleting the conflict (CONFIRM first):
```bash
curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore" \
  -H 'Content-Type: application/json' -d \
  '{"indices": "<pattern>", "rename_pattern": "<from>", "rename_replacement": "<to>"}'
```

### Step 6: UltraWarm / Cold storage migration layer

Entry: `_plugins/_ism` migration returns `migration_failed`.

```bash
aws opensearch describe-domain-config --domain-name <domain> \
  --query 'ClusterConfig.WarmEnabled, ClusterConfig.WarmCount, ColdStorageOptions' --output json
curl -sS "https://$ENDPOINT/_plugins/_ism/explain/<index>?v" | jq '.'
curl -sS "https://$ENDPOINT/_cat/indices/<index>?v"
```

- `WarmEnabled: false` → nothing to migrate to. **COLD_STORAGE_MIGRATION.**
- `WarmCount: < 3` → managed minimum violated. **COLD_STORAGE_MIGRATION.**
- `pri: 1 rep: 0` → migration fails on primary-only; raise replicas to
  1 and wait for green.

### Step 7: S3 lifecycle deletion layer

Entry: `_snapshot/<repo>/_all` lists snapshots that fail to restore
with `SnapshotMissingException`; S3 object count drops unexpectedly.

```bash
aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json | jq '.'
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<bucket> \
  --start-time $(date -d '-7 days' +%s) --end-time $(date +%s) \
  --output json | jq '.Events[] | select(.EventName == "DeleteObject")'
```

Any `Expiration`/`NoncurrentVersionExpiration` rule matching the
snapshot prefix → blobs deleted on schedule.
**S3_LIFECYCLE_DELETION.** Cross-check `_snapshot/<repo>/_status`
against `s3 ls s3://<bucket>/<prefix>/indices/<shard-id>/` for
missing blobs.

### Step 8: Concurrent snapshot limit layer

Entry: `_snapshot` returns `ConcurrentSnapshotExecutionException`.

```bash
curl -sS "https://$ENDPOINT/_snapshot/_status" | jq '.snapshots[] | {repository, snapshot, state}'
```

Any snapshot with `state: IN_PROGRESS` blocks a second into the same
repository. **CONCURRENT_SNAPSHOT_LIMIT.** If automated and manual
schedules collide, move the manual schedule to a different
repository/prefix or different `base_path`.

### Step 9: Manifest corruption layer

Entry: `_snapshot/<repo>/<snap>/_status` shows `FAILED: INTERNAL_ERROR`;
restore fails with `CorruptedIndexException`.

```bash
curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>" | jq '.snapshots[0].failures'
aws s3api head-object --bucket <bucket> --key <prefix>/indices/<shard-id>/0/index-N | jq '.ContentLength'
```

- `ContentLength: 0` → corrupt (zero-byte) blob. **MANIFEST_CORRUPTION.**
- `NoSuchKey` → blob missing; usually lifecycle (cross-reference Step 7).
- `index-N` blobs at the repo root fail to parse as JSON → repository
  metadata corrupt; re-register against a clean prefix.

### Step 10: Cross-region replication layer

Entry: `_plugins/_replication/<index>/_status` shows `SYNCING` with
lag rising, or `REPLICATION_NOT_ALIVE`.

```bash
curl -sS "https://$FOLLOWER/_plugins/_replication/<index>/_status?pretty"
curl -sS "https://$LEADER/_cluster/settings?include_defaults=true&filter_path=defaults.index.plugins" | jq '.'
```

- `status: SYNCING` with high `last_updated_lag_seconds` → follower
  behind; check leader snapshot activity (brief lock is transient).
- `REPLICATION_NOT_ALIVE` → leader check failed; verify leader
  endpoint, security, write block on follower.
- Follower engine version MUST be same or higher than leader. Lower
  version → replication fails.

### Step 11: CUR / audit log snapshot config layer

Entry: CloudTrail or OpenSearch audit logs not landing in the audit
S3 bucket.

```bash
aws opensearch describe-domain-config --domain-name <domain> \
  --query 'LogPublishingOptions' --output json
aws s3api get-bucket-policy --bucket <audit-bucket> --output json | jq '.'
```

- `AuditLogs: DISABLED` → no audit logs anywhere; S3 audit bucket
  will be empty regardless. **CUR_AUDIT_LOG_CONFIG.**
- `AuditLogs: ENABLED` but zero events in the CloudWatch log group →
  fine-grained audit log categories not enabled on the domain.
- S3 bucket policy missing `cloudtrail.amazonaws.com` grant with
  `aws:SourceArn` condition → CloudTrail trails show "Access Denied".
  **CUR_AUDIT_LOG_CONFIG.**

### Step 12: INSUFFICIENT_DATA — when none of the layers confirm

If every probe passes and no failing probe matches the symptom,
emit INSUFFICIENT_DATA. List the passing probes in EVIDENCE.
Recommend escalation to `opensearch-cluster-troubleshooter` for
cluster-state diagnosis, or open an AWS Support case with the domain
ARN, snapshot id, repository name, and the failing probe outputs.

## Output specification — diagnostic block

For every diagnosis, emit ONE diagnostic block per target. Field
order is fixed.

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

Field rules:

- `TARGET` includes domain name and, when applicable, repository name
  and snapshot id.
- `VERDICT` is one of the two enumerated values; never
  `ROOT_CAUSE_FOUND` (that is a different skill family).
- `REASON` names both the layer AND the failing probe.
- `EVIDENCE` always includes (a) symptom, (b) failing probe output,
  (c) at least one passing probe ruling out a competing layer.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`PUT _snapshot`, `DELETE _snapshot/<repo>`,
  `_snapshot/<repo>/<snap>/_restore`, `update-domain-config`,
  `s3api put-bucket-lifecycle-configuration`), emit and await
  operator approval. Do NOT execute the CLI or curl until confirmed.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only. Do not perform state-changing operations as diagnostic
  probes.
- **`DELETE _snapshot/<repo>/<snap>`** removes the snapshot from the
  repository; it does NOT delete S3 blobs (segments are deduplicated).
  Confirm before deleting.
- **`_restore`** opens snapshot indices on the target. If a same-named
  index exists, restore skips or fails. Confirm target state first.
- **`update-domain-config` to enable warm/cold** triggers a blue/green
  deployment. Plan outside traffic peaks.
- **`s3api put-bucket-lifecycle-configuration`** overwrites the
  existing lifecycle. Always read current config first and merge.
- **Re-registering a repository** overwrites prior settings. If the
  prior repository had snapshots, the new registration must point at
  the same bucket + prefix or those snapshots become orphaned.
- **Bulk remediation batch limit.** Batch groups of at most 5
  repositories, one CONFIRM per batch.

## Remediation guidance

### For REPOSITORY_REGISTRATION — repository not registered

```bash
curl -X PUT "https://$ENDPOINT/_snapshot/<repo>" -H 'Content-Type: application/json' -d '
{"type": "s3", "settings": {
  "bucket": "<bucket>", "region": "<bucket-region>",
  "base_path": "<prefix>",
  "iam_role_arn": "arn:aws:iam::<account>:role/<role>",
  "compress": true}}'
curl -sS "https://$ENDPOINT/_snapshot/<repo>" | jq '.'
```

### For REPOSITORY_VERIFICATION — verification failed

1. Update the bucket policy (see IAM_ROLE_S3_ACCESS).
2. Re-run verification:
   ```bash
   curl -X POST "https://$ENDPOINT/_snapshot/<repo>/_verify?verbose=true"
   ```
3. If verification still fails, delete and re-register (CONFIRM first).

### For IAM_ROLE_S3_ACCESS — role or bucket policy missing

```bash
# Bucket policy granting the snapshot role
aws s3api put-bucket-policy --bucket <bucket> --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "ListBucketForSnapshot", "Effect": "Allow",
     "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
     "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
     "Resource": "arn:aws:s3:::<bucket>"},
    {"Sid": "ReadWriteSnapshotObjects", "Effect": "Allow",
     "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
     "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"}
  ]}'
# SSE-KMS: add kms:Decrypt and kms:GenerateDataKey to the role
aws iam put-role-policy --role-name <role-name> --policy-name KmsAccess \
  --policy-document '{"Version": "2012-10-17", "Statement": [
    {"Effect": "Allow", "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
     "Resource": "<kms-key-arn>"}]}'
```

Verify with `simulate-principal-policy`.

### For SNAPSHOT_TIMEOUT — snapshot stuck

1. Resolve cluster health (red → yellow → green).
2. Raise `thread_pool.snapshot.size` if saturated.
3. Stop competing snapshots in the same repository.
4. Cancel the snapshot if it cannot complete (CONFIRM first):
   ```bash
   curl -X DELETE "https://$ENDPOINT/_snapshot/<repo>/<snap>"
   ```

### For RESTORE_VERSION_CONFLICT — target version too low

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --engine-version OpenSearch_<target> --profile <p>
# Wait for UpgradeStatus: Succeeded, then retry restore
```

### For RESTORE_ALIAS_CONFLICT — alias or index exists

```bash
curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore" \
  -H 'Content-Type: application/json' -d \
  '{"indices": "<pattern>", "rename_pattern": "<from>", "rename_replacement": "<to>"}'
# Or delete the conflict (CONFIRM first):
curl -X DELETE "https://$ENDPOINT/<index-or-alias>"
```

### For COLD_STORAGE_MIGRATION — warm/cold misconfig

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --cluster-config WarmEnabled=true,WarmCount=3,WarmType=ultrawarm1.medium.search --profile <p>
curl -X PUT "https://$ENDPOINT/<index>/_settings" -H 'Content-Type: application/json' -d \
  '{"index": {"number_of_replicas": 1}}'
# Wait for green, then retry the migration via ISM
```

### For S3_LIFECYCLE_DELETION — lifecycle expires snapshots

```bash
aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json > lifecycle.json
# Edit to scope/expire the rule, then:
aws s3api put-bucket-lifecycle-configuration --bucket <bucket> \
  --lifecycle-configuration file://lifecycle-merged.json
# Re-take snapshots that were lost
```

### For CROSS_REGION_REPLICATION — async replication stall

1. Verify `index.plugins.replication.enabled: true` on leader.
2. Verify follower write block is off and follower engine >= leader.
3. Resume replication: `curl -X POST "https://$FOLLOWER/_plugins/_replication/<index>/_resume"`

### For SHARD_ALLOCATION_RESTORE — recovery throttling

Raise `cluster.routing.allocation.node_concurrent_recoveries` (default 2)
and `indices.recovery.max_bytes_per_sec` (default 40mb). Watch
`_cat/recovery` for 100%.

### For MANIFEST_CORRUPTION — corrupt blob

1. `DELETE _snapshot/<repo>/<snap>` (CONFIRM first).
2. Re-take a fresh snapshot; new snapshot uses healthy segments.
3. If repository metadata itself is corrupt, re-register against a
   clean prefix and re-take all snapshots.

### For CONCURRENT_SNAPSHOT_LIMIT — second snapshot blocked

Wait for the in-flight snapshot, OR cancel it (CONFIRM first).
Reschedule the manual cadence to avoid the automated snapshot hour,
or use a different repository/prefix.

### For CUR_AUDIT_LOG_CONFIG — audit logs missing

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --log-publishing-options AuditLogsEnabled=true,CloudWatchLogsLogGroupArn="<log-group-arn>" --profile <p>
# Then configure CloudWatch Logs → S3 export (subscription filter to Firehose)
```

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

## Domain

AWS CloudOps / OpenSearch Service, Snapshot and Restore Diagnostics,
S3 Repository Management, IAM Role Configuration, UltraWarm/Cold
Tier Migration, Cross-Region Replication, and Audit Log Delivery.

## AWS documentation

- **Working with Amazon OpenSearch Service snapshots** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html
- **Registering a manual snapshot repository** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html#managedomains-snapshot-registerdirectory
- **Restoring snapshots** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html#managedomains-snapshot-restore
- **UltraWarm storage for OpenSearch Service** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html
- **Cold storage for OpenSearch Service** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/cold-storage.html
- **Cross-cluster replication** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/replication.html
- **Monitoring OpenSearch Service with CloudWatch** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/monitoring.html
- **Configuring audit logs** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/audit-logs.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
