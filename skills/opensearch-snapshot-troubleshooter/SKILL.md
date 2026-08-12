---
name: opensearch-snapshot-troubleshooter
description: >-
  Diagnoses Amazon OpenSearch Service snapshot failures through a
  thirteen-category diagnostic tree: S3 repository registration errors
  (PUT _snapshot), repository verification failure (bucket policy,
  IAM role trust), IAM role missing s3:PutObject / s3:ListBucket /
  s3:GetObject / s3:PutObjectAcl on the bucket, snapshot stuck or
  timeout (unassigned shards, large shard count, cluster red),
  restore into a different domain (cluster-state conflict, OpenSearch
  version mismatch — restore requires same version or higher), index
  alias conflict during restore (alias in use by a running index),
  snapshot to UltraWarm / Cold storage (migration failures, storage
  mode mismatch), S3 bucket lifecycle policy deleting snapshot
  objects before retention, cross-region snapshot replication
  (cross-Region async replication config), shard allocation during
  restore (shard rebalance starved by recovery throttling), snapshot
  manifest corruption (index-N blob corrupt, repository metadata
  stale), concurrent snapshot limit (one repository-level snapshot
  at a time — second PUT returns ConcurrentSnapshotExecution),
  Cost and Usage Report / audit-log snapshot configuration
  (CloudTrail / OpenSearch audit logs to S3). Walks symptoms to a
  verified root cause with evidence-backed probes; emits
  ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and domain configuration. Live-account diagnosis uses aws opensearch describe-domain, describe-domain-config, list-domain-names, aws es describe-elasticsearch-domain (legacy), aws s3 ls / get-bucket-policy / get-bucket-lifecycle-configuration, aws iam get-role-policy / simulate-principal-policy, aws logs filter-log-events on /aws/opensearch/domains/<domain>/application-logs, curl against the domain endpoint for _snapshot, _cat/recovery, _cat/shards, _cluster/health, and aws cloudwatch get-metric-statistics on the AWS/ES namespace (AWS CLI v2, SSO or key-based credentials).
keywords:
- OpenSearch
- snapshot
- repository
- S3
- PUT _snapshot
- verification
- restore
- UltraWarm
- Cold storage
- shard allocation
- manifest corruption
- concurrent snapshot
- cross-region replication
- lifecycle policy
- alias conflict
- ClusterBlockException
- troubleshooting
tags:
- opensearch
- analytics
- troubleshooting
- snapshot
- s3
- backup
- restore
- ultrawarm
- iam-role
- repository
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an OpenSearch Service snapshot failure (S3 repository registration error, repository verification failure, snapshot stuck or timeout, restore failure, alias conflict on restore, UltraWarm/Cold migration failure, missing snapshots due to S3 lifecycle, cross-region replication lag, shard allocation failure during restore, manifest corruption, concurrent snapshot rejection, audit-log/CUR snapshot misconfig), walking a symptom to the failed layer with verify and fix commands, validating why a snapshot or restore did not complete, or triaging a "OpenSearch snapshots are broken" page where the root cause may be repository registration, IAM role, bucket lifecycle, cluster state, or version compatibility — not necessarily the OpenSearch domain itself.
  when_not_to_use: Cluster-level stability incidents not tied to snapshots (use opensearch-cluster-troubleshooter), OpenSearch Serverless collection backup (Serverless collections use a different snapshot model), index mapping / query performance tuning (use the index deployer / a query tuning skill), S3 bucket public-access posture audits (use s3-public-access-auditor), or VPC endpoint posture audits for the OpenSearch domain. This skill diagnoses snapshot and restore failures; it does not tune shard count for indexing throughput or audit steady-state configuration posture.
  activation_triggers:
  - OpenSearch snapshot failed
  - OpenSearch snapshot stuck
  - OpenSearch snapshot timeout
  - PUT _snapshot failed
  - repository verification failed
  - SnapshotException
  - ConcurrentSnapshotExecutionException
  - OpenSearch restore failed
  - restore version mismatch
  - OpenSearch alias conflict restore
  - UltraWarm migration failed
  - Cold storage migration failed
  - snapshot missing from S3
  - S3 lifecycle deleted snapshots
  - cross-region replication lag
  - shard allocation restore
  - snapshot manifest corruption
  - OpenSearch audit logs S3
  - troubleshoot OpenSearch snapshot
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "snapshot stays IN_PROGRESS for hours", "restore returns 400"), optionally paired with the domain configuration (describe-domain output) and recent OpenSearch application logs, OR (b) a DomainName plus snapshot/repository context (repository name, snapshot id, S3 bucket, IAM role ARN, source/target domain for restore) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {REPOSITORY_REGISTRATION, REPOSITORY_VERIFICATION, IAM_ROLE_S3_ACCESS, SNAPSHOT_TIMEOUT, RESTORE_VERSION_CONFLICT, RESTORE_ALIAS_CONFLICT, COLD_STORAGE_MIGRATION, S3_LIFECYCLE_DELETION, CROSS_REGION_REPLICATION, SHARD_ALLOCATION_RESTORE, MANIFEST_CORRUPTION, CONCURRENT_SNAPSHOT_LIMIT, CUR_AUDIT_LOG_CONFIG, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"OpenSearch domain prod-logs-cluster fails to register\nthe manual S3 repository. PUT _snapshot/s3-backups returns\n500 with 'repository_verification_exception' and the IAM role\narn:aws:iam::111111111111:role/opensearch-snapshot-role is\nlisted in the trust policy of the domain but the S3 bucket\npolicy does not list the OpenSearch service principal.\"\nDomainName: prod-logs-cluster\nEngineVersion: OpenSearch_2.13\nRepository: s3-backups\nBucket: prod-os-snapshots-us-east-1\nSnapshotRoleArn: arn:aws:iam::111111111111:role/opensearch-snapshot-role\nLast log line: \"repository_verification_exception: [[s3-backups]]
    verification failed\""
---

# OpenSearch Snapshot Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  `repository_verification_exception` → REPOSITORY_VERIFICATION /
  IAM_ROLE_S3_ACCESS; `PUT _snapshot` returns 4xx / 5xx →
  REPOSITORY_REGISTRATION; snapshot stays `IN_PROGRESS` for hours →
  SNAPSHOT_TIMEOUT / SHARD_ALLOCATION_RESTORE; restore returns 400
  with version message → RESTORE_VERSION_CONFLICT; restore returns
  `resource_already_allocated_exception` on an alias →
  RESTORE_ALIAS_CONFLICT; `ConcurrentSnapshotExecutionException` →
  CONCURRENT_SNAPSHOT_LIMIT; snapshots vanish from S3 after N days →
  S3_LIFECYCLE_DELETION; UltraWarm/Cold migration fails with
  `migration_failed` → COLD_STORAGE_MIGRATION; `SnapshotException`
  with `SnapshotFailedEngineException` reading index-N →
  MANIFEST_CORRUPTION; cross-Region replica lags or stalls →
  CROSS_REGION_REPLICATION; CloudWatch shows no
  `SnapshotFromAutoFollow` for audit logs → CUR_AUDIT_LOG_CONFIG.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A `ROOT_CAUSE_IDENTIFIED`
  verdict requires positive evidence — a failing probe that matches
  the symptom — not a process of elimination that "must be the IAM
  role."
- **Manual and automated snapshots use different repositories.**
  Automated snapshots write to a service-managed S3 bucket
  (`cs-automated` / `cs-automated-enc` repositories) that you cannot
  inspect or lifecycle directly. Manual snapshots write to a
  customer-owned S3 bucket via a customer IAM role. Operators who
  "cannot find the snapshot in S3" while debugging an automated
  snapshot are looking in the wrong bucket — the automated snapshot
  bucket is read-only and only the OpenSearch service can list it.
- **Restore requires the target domain engine version to be the same
  or higher than the source.** A snapshot taken on OpenSearch 2.13
  restores fine into 2.13 or 2.15 but fails on 2.11 with a
  `version_not_supported` error. Elasticsearch 7.x snapshots do not
  restore into OpenSearch 2.x domains without a 7.10 → 1.x → 2.x
  upgrade chain (snapshot upgrade). Always read the source snapshot
  `engine_version` before attempting a restore into a new domain.
- **One snapshot at a time per repository.** OpenSearch rejects a
  second concurrent snapshot into the same repository with
  `ConcurrentSnapshotExecutionException`. Automated and manual
  snapshots into the same repository DO collide; if you register a
  manual repo pointing at the automated-repository prefix, the next
  automated snapshot can fail. Use distinct S3 prefixes for distinct
  schedules.

## Mindset

A failing OpenSearch snapshot is usually a permissions, lifecycle,
or version-compatibility incident wearing a cluster costume. The
domain is healthy in the majority of cases; the broken thing is
the IAM role assumed for S3, the bucket policy that does not trust
the OpenSearch service principal, an S3 lifecycle rule expiring
snapshot blobs, a version mismatch between source and target
domain, or an alias collision at restore time. Treat the OpenSearch
cluster as innocent until the repository registration, IAM role,
bucket lifecycle, and version-compatibility layers are proven clean.
Senior analytics engineers do not start by raising node count;
they start with `_snapshot/<repo>/_status`, `get-bucket-policy`,
and `simulate-principal-policy`, and only resize the cluster once
repository registration, IAM, and lifecycle are confirmed correct.

## Philosophy

Four behaviours separate a senior OpenSearch engineer from a
generalist:

- **Repository registration is a three-way contract.** A working
  S3 snapshot repository requires (1) an IAM role the OpenSearch
  domain can assume, (2) a trust policy on that role listing the
  OpenSearch service principal for the account, and (3) a bucket
  policy on the target S3 bucket granting the role
  `s3:PutObject`/`s3:ListBucket`/`s3:GetObject`/`s3:PutObjectAcl`
  (or a broader policy on the role itself). Any one missing and
  `PUT _snapshot` either fails outright (registration rejected)
  or succeeds with verification failure on the first snapshot
  attempt. Operators who "added S3 permissions to the role" but
  still see `repository_verification_exception` usually miss the
  bucket-policy side or the trust-policy side.
- **Snapshot and restore are NOT symmetric on version.** A snapshot
  taken on OpenSearch 2.x can be restored into any 2.y ≥ 2.x. It
  CANNOT be restored into Elasticsearch 7.x or into a lower 2.x.
  Operators who "took a snapshot in prod, tried to restore into a
  lower-version dev domain" hit `version_not_supported` on the
  first shard and assume the snapshot is corrupt. The snapshot is
  fine; the target domain needs an engine-version upgrade.
- **Restore into a non-empty cluster fights aliases and existing
  indices.** `_snapshot/.../_restore` opens the snapshot's indices
  by their original names. If an index with the same name (or the
  alias the snapshot references) already exists, restore fails with
  `resource_already_allocated_exception` or silently skips the
  index. The fix is to rename on restore (`"rename_pattern":
  "logs-", "rename_replacement": "restored-logs-"`) or to delete
  the conflicting index/alias first — not to retry the restore.
- **S3 lifecycle rules DO delete snapshot blobs.** OpenSearch
  snapshots are not single files; they are trees of `index-*`,
  `snap-*`, and `index-*` blobs referenced by the repository
  metadata. An S3 lifecycle rule that expires "all objects" after
  N days deletes the blobs while the repository still lists the
  snapshot. The next `_snapshot/<repo>/_restore` then fails with
  `SnapshotMissingException` or a partial-shard error. Always
  scope S3 lifecycle rules by prefix when a bucket holds snapshot
  repositories.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `repository_verification_exception` on `PUT _snapshot` or first snapshot | REPOSITORY_VERIFICATION / IAM_ROLE_S3_ACCESS | `get-bucket-policy`, `iam simulate-principal-policy` on the snapshot role |
| `PUT _snapshot/<repo>` returns 4xx; repository never registers | REPOSITORY_REGISTRATION | `curl $ENDPOINT/_snapshot/<repo>` — does the repo exist? `get-role` trust policy for the OpenSearch service principal |
| Snapshot stays `IN_PROGRESS` > expected window; `_cat/shards` shows UNASSIGNED | SNAPSHOT_TIMEOUT / SHARD_ALLOCATION_RESTORE | `_snapshot/<repo>/<snap>/_status`, `_cat/shards?v&h=index,shard,prirep,state,unassigned.reason` |
| `_restore` returns 400 with `version_not_supported` or `SnapshotImageCorruptedException` | RESTORE_VERSION_CONFLICT | `curl $ENDPOINT/_snapshot/<repo>/<snap>` — read `engine_version` |
| `_restore` of alias-bearing indices returns `resource_already_allocated_exception` | RESTORE_ALIAS_CONFLICT | `_cat/aliases?v&s=alias:desc` for the alias in the snapshot |
| `migration_failed` to UltraWarm or Cold; node roles include `warm` but `cluster.memory_level` mismatch | COLD_STORAGE_MIGRATION | `opensearch describe-domain-config` (WarmEnabled, ColdStorageOptions), `_nodes/_all` (warm node count) |
| `_snapshot/<repo>/_status` returns `SNAPSHOT_FAILED` and S3 lifecycle shows `ExpirationInDays` | S3_LIFECYCLE_DELETION | `s3 get-bucket-lifecycle-configuration`, `s3 ls s3://<bucket>/<prefix>` for recent deletes |
| Cross-Region async replication lags; `index` blocks on follower | CROSS_REGION_REPLICATION | `_plugins/_replication/<index>/_status`, source `_cluster/settings` for `index.plugins.replication.enabled` |
| `_restore` stalls on shard init; `_cat/recovery` shows throttle | SHARD_ALLOCATION_RESTORE | `_cat/recovery?v&h=index,shard,time,stage,percent`, `cluster.routing.allocation.node_concurrent_recoveries` |
| `SnapshotException` reading `index-N` blob; `_snapshot/.../_status` shows `INTERNAL_ERROR` | MANIFEST_CORRUPTION | `s3 ls s3://<bucket>/<prefix>/indices/<shard-id>/index-N` — does the object exist? `s3 head-object` for size 0 |
| Second snapshot into same repo fails immediately with `ConcurrentSnapshotExecutionException` | CONCURRENT_SNAPSHOT_LIMIT | `_snapshot/_status` — is another snapshot `IN_PROGRESS`? |
| CloudWatch `SnapshotFromAutoFollow` metric flat; CloudTrail logs not landing in the S3 audit bucket | CUR_AUDIT_LOG_CONFIG | `opensearch describe-domain-config` (LogPublishingOptions.AuditLogs), `s3 ls s3://<audit-bucket>/` for today's prefix |
| None of the above, cluster red, multiple indices unassigned | INSUFFICIENT_DATA → escalate | `_cluster/health`, `describe-domain` (ClusterConfig, EBSOptions) |

## Pre-flight: domain state and gather-info gate

Before running symptom-specific probes, gather the canonical domain
configuration and short-circuit on domain states that mimic snapshot
failures. Misclassifying these produces hours of snapshot debugging
for a problem that is not a snapshot problem.

### Account-wide pre-flight commands

```bash
# 1. Domain configuration (EngineVersion, ClusterConfig,
#    EBSOptions, EncryptionAtRestOptions, NodeToNodeEncryptionOptions,
#    SnapshotOptions, AdvancedOptions, LogPublishingOptions,
#    WarmEnabled, ColdStorageOptions, ChangeProgressDetails)
aws opensearch describe-domain --domain-name <domain> --output json

aws opensearch describe-domain-config --domain-name <domain> --output json

# 2. Recent OpenSearch application logs (snapshot / restore / migration
#    events, repository_verification_exception, SnapshotException)
aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/application-logs \
  --start-time $(date -d '-60 minutes' +%s)000 \
  --filter-pattern '"repository_verification_exception" OR "SnapshotException" OR "ConcurrentSnapshotExecutionException" OR "migration_failed" OR "version_not_supported"' \
  --output json

# 3. Domain endpoint and snapshot configuration
ENDPOINT=$(aws opensearch describe-domain --domain-name <domain> \
  --query 'Domain.Endpoint' --output text)

# 4. Repository status (does the repo exist, is it verifying?)
curl -sS "https://$ENDPOINT/_cat/repositories?v" \
  --aws-sigv4 "aws:amz:us-east-1:opensearch" \
  --aws-sigv4-a "AWSC4-IAM" || echo "sigv4 not available; pass an API key or signed request"

# 5. S3 bucket policy + lifecycle for the snapshot bucket
aws s3api get-bucket-policy --bucket <bucket> --output json 2>/dev/null || \
  echo "No bucket policy"

aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json

# 6. IAM role trust + policies for the snapshot role
aws iam get-role --role-name <role-name> --output json
aws iam list-attached-role-policies --role-name <role-name> --output json
aws iam list-role-policies --role-name <role-name> --output json

# 7. CloudWatch metrics (SnapshotCount, AutomatedSnapshotFailure,
#    SearchableDocuments, ClusterUsedSpace)
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name AutomatedSnapshotFailure \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 day' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 8. AWS Health (regional OpenSearch events, scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Domain-state short-circuit

| `DomainStatus` / `ChangeProgressDetails` | Effect on diagnosis |
|---|---|
| `Processing: false`, no `PendingChanges` | Domain is steady; proceed with symptom-driven diagnosis. |
| `Processing: true` (blue/green deployment in progress) | A configuration update is in flight. Snapshot and restore can still run but may be slow because blue/green spins up new nodes. Note in REMEDIATION; wait for `Processing: false` before drawing conclusions. |
| `ChangeProgressDetails: Pending` | Same as `Processing: true`. A snapshot taken mid-deployment can complete on the old node set; a restore mid-deployment may fail when the new node set rolls in. |
| `UpgradeProcessing: true` | Engine-version upgrade in flight. Snapshots taken mid-upgrade can fail verification. Wait for `UpgradeStatus: Succeeded` before attempting cross-version restore. |
| `UpgradeStatus: Failed` or `UpgradeStatus: RollbackInProgress` | Last upgrade failed; the cluster is back on the prior engine. A restore attempt that assumed the higher version will fail. Re-read the current `EngineVersion` before retrying restore. |
| `ClusterConfig.DedicatedMasterEnabled: false` and cluster red | Without dedicated masters, a heavy snapshot can starve the elected master and the cluster goes red. Snapshot failures here are a cluster-sizing issue, not a snapshot config issue. |
| `LogPublishingOptions.AuditLogs: DISABLED` | No audit logs are landing in CloudWatch; you cannot diagnose CUR/audit log snapshot config from CloudWatch Logs. Read `describe-domain-config` directly. |

### Repository-state pre-flight

| Field from `_snapshot/<repo>` | Effect |
|---|---|
| `settings.iam_role_arn` does not match the role on the snapshot bucket | Registration used the wrong role. Re-register with the correct `iam_role_arn` — never override an existing repository without deleting and re-creating it. |
| `settings.bucket` includes a Region prefix that does not match the domain Region | Cross-Region snapshot repository requires the bucket to be in the same Region unless explicit `region` is set in `compress`, `bucket`, `base_path`. Verify the bucket Region with `s3 get-bucket-location`. |
| `compress: false` on a 10+ TB repository | Compression halves S3 GET volume on restore. Performance, not correctness, but worth noting. |
| `chunk_size: 1g` on a cluster with > 50 GB shards | Large chunks increase the chance a single corrupt blob invalidates the whole shard; lower to 256m for large-cluster snapshot. |

If the input is malformed (missing DomainName, absent symptom
description, no repository or snapshot id for restore debugging),
emit:

```text
TARGET: <domain-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the error string or observed behaviour) and the
  DomainName plus, for snapshot/restore errors, the repository
  name and snapshot id.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string
  or observed symptom (snapshot stuck, restore failed, missing in
  S3), (2) the DomainName and EngineVersion, and (3) for restore
  errors, the source domain's EngineVersion and the target
  domain's EngineVersion, plus the repository name and snapshot id.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the layer-specific probes in order.
Each layer ends with either a positive root-cause confirmation
(failing probe that matches the symptom) or a pass that moves to the
next layer. **Never emit ROOT_CAUSE_IDENTIFIED without a failing
probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior OpenSearch engineer knows
from incident experience. Each one routes a diagnosis away from the
obvious layer to a less obvious one:

- **Automated snapshot bucket is read-only and service-managed.**
  The `cs-automated` and `cs-automated-enc` repositories write to
  an AWS-managed S3 bucket you cannot list directly with `aws s3 ls`
  unless you have an explicit bucket policy grant. Operators who
  "cannot find yesterday's snapshot" while debugging an automated
  snapshot waste hours listing the wrong bucket. Use
  `_snapshot/cs-automated/_all` against the domain endpoint to
  enumerate automated snapshots.

- **Manual snapshot IAM role uses an OpenSearch service-principal
  trust, not an sts:ExternalId trust.** The trust policy on the
  snapshot role lists `"Service": "opensearchservice.amazonaws.com"`
  (and the older `"Service": "es.amazonaws.com"`). Cross-account
  snapshots additionally require a `Condition` on `aws:SourceAccount`
  and `aws:SourceArn` — a role without the condition can be confused
  by the confused-deputy check and fail verification even with the
  right S3 permissions.

- **The bucket policy must grant the role, not the OpenSearch
  service principal.** Operators frequently write a bucket policy
  that lists `"Service": "opensearchservice.amazonaws.com"` as the
  principal. The role the domain assumes is what needs the S3
  actions; the service principal goes in the role trust, not the
  bucket policy. A bucket policy keyed to the service principal
  produces intermittent verification failures because the role's
  session ARN does not match the service principal.

- **Snapshot blobs are not independent files.** Each shard is a
  tree of `index-N` segment files referenced by a per-snapshot
  `snap-*.dat` manifest. An S3 lifecycle rule that deletes any
  `index-N` object invalidates every snapshot that references that
  segment. Deleting "old" objects from a snapshot repository
  corrupts every snapshot that shared the segment — segments are
  deduplicated across snapshots.

- **OpenSearch Service runs one snapshot per repository at a time.**
  `ConcurrentSnapshotExecutionException` is thrown if a second
  snapshot is requested into the same repository while one is in
  flight. Automated and manual snapshots into the SAME repository
  collide; use distinct S3 prefixes (`base_path`) for distinct
  schedules.

- **Restore DOES NOT overwrite existing indices.** If an index or
  alias with the snapshot's name already exists on the target
  cluster, the restore either skips the index (default) or fails
  with `resource_already_allocated_exception`. The fix is to
  rename-on-restore or to delete the conflicting index first —
  not to retry the restore.

- **UltraWarm / Cold migration is one-way for storage cost.** A
  managed OpenSearch domain with WarmEnabled can migrate indices to
  warm storage via `_plugins/_ism` policies or `migrate` API. Cold
  storage adds a second tier; both require explicit node count > 0
  in the cluster config. Migration fails if the index does not
  have replicas on the hot tier (cannot migrate a primary-only
  index without first restoring the replica), if the index is
  currently being snapshotted, or if the `warm_count` is below 3
  (managed minimum).

- **Cross-Region async replication is index-level, not cluster-level.**
  The OpenSearch `_plugins/_replication` API replicates indices one
  at a time from leader to follower domain. Replication stalls when
  the leader takes a snapshot (locks the index briefly), when the
  follower is on a lower engine version, or when the follower
  cluster block disables writes. Operators expecting "cross-Region
  cluster mirroring" need to set up per-index replication and add
  each new index explicitly.

- **`_snapshot/<repo>/_status` is the single source of truth for
  snapshot progress.** The `state` field (`SUCCESS`, `IN_PROGRESS`,
  `FAILED`, `PARTIAL`) plus per-shard `stage` (`STARTED`, `TRANSLOCATING`,
  `FINALIZE`) tell you where the snapshot is stuck. Operators who
  "watch S3" for new objects during a snapshot miss the in-cluster
  state machine; S3 object count is a trailing indicator.

- **Snapshot of a yellow/red cluster can succeed PARTIAL.** A
  `PARTIAL` snapshot is one where one or more primary shards failed
  to snapshot (cluster red) but the rest succeeded. The snapshot is
  usable but restores only the shards that snapshotted cleanly.
  Operators who "got a SUCCESS in S3" sometimes have a `PARTIAL`
  they did not notice; check the snapshot metadata before relying
  on it for DR.

- **Audit logs to S3 require `LogPublishingOptions.AuditLogs:
  ENABLED` AND a CloudWatch Logs delivery, AND the S3 bucket must
  have a bucket policy granting the OpenSearch service principal
  `s3:PutObject` with the `aws:SourceAccount` condition.** Operators
  who "set the LogPublishingOptions but never see audit logs in S3"
  are missing the bucket policy side. CUR (Cost and Usage Report)
  is a separate stream (billing → S3) and does not depend on
  OpenSearch config.

- **`describe-domain` returns snapshot config in `SnapshotOptions.`
  only for automated snapshot hour.** The automated-snapshot hour
  (0-23, `AutomatedSnapshotStartHour`) is the only knob OpenSearch
  exposes for automated snapshots. Manual snapshot frequency is
  controlled by the customer (cron, Lambda, Step Functions).
  Operators asking "where do I configure automated snapshot
  retention?" — there is no managed retention; you copy automated
  snapshots to a manual repository on a schedule if you need
  retention > 14 days.

- **Repository_verification_exception is the #1 misdiagnosed
  snapshot error.** The error text says "verification failed" and
  operators reach for "the snapshot is corrupt." The actual cause
  is almost always IAM (role trust, role policy, or bucket policy),
  not snapshot blob corruption. Always probe IAM before probing
  snapshot integrity.

- **Cross-account snapshot copy is two-step.** To copy a snapshot
  from Account A's OpenSearch to Account B's bucket, the snapshot
  role in A must trust Account B (or the OpenSearch service
  principal in B), the bucket policy in B must grant the role in A
  `s3:PutObject`, and the OpenSearch domain in B must register the
  repository with `iam_role_arn` pointing at A's role. Operators
  who "shared the snapshot role with Account B" without updating
  the trust policy get verification failure on the B side.

### Step 1: Repository registration & verification layer

Entry symptom: `PUT _snapshot/<repo>` returns 4xx / 5xx, or first
snapshot fails with `repository_verification_exception`.

Probes in order:

1. **Does the repository exist?**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>" | jq '.'
   ```
   - 404 → repository was never registered, or registration failed
     silently. Re-issue `PUT _snapshot/<repo>` with the documented
     body.
   - 200 → repository exists but verification may be failing on
     first snapshot; move to probe 2.

2. **Was `PUT _snapshot` issued with the correct body?**
   The minimum body for an S3 snapshot repository on a managed
   OpenSearch domain is:
   ```json
   {
     "type": "s3",
     "settings": {
       "bucket": "<bucket>",
       "region": "<bucket-region>",
       "base_path": "<prefix>",
       "iam_role_arn": "arn:aws:iam::<account>:role/<role>",
       "compress": true
     }
   }
   ```
   - Missing `iam_role_arn` → registration succeeds but the domain
     cannot write to S3; first snapshot fails verification.
     **Confirms REPOSITORY_REGISTRATION.**
   - `region` missing and bucket is in a different Region →
     registration succeeds but writes go to the wrong endpoint;
     verification fails. **Confirms REPOSITORY_REGISTRATION.**
   - `base_path` overlaps another repository's prefix on the same
     bucket → manifest collision; both repositories become corrupt.
     **Confirms REPOSITORY_REGISTRATION.**

3. **Is the snapshot role's trust policy correct?**
   ```bash
   aws iam get-role --role-name <role-name> \
     --query 'Role.AssumeRolePolicyDocument' --output json | jq '.'
   ```
   - Trust policy MUST list `"Service": "opensearchservice.amazonaws.com"`
     (legacy: `es.amazonaws.com`).
   - For cross-account: trust policy MUST include the
     `"aws:SourceAccount"` and `"aws:SourceArn"` conditions on the
     principal. Missing condition → confused-deputy protection
     rejects the assume-role call. **Confirms REPOSITORY_REGISTRATION.**

If the repository does not exist or the registration body / role
trust is wrong, emit REPOSITORY_REGISTRATION. If registration is
correct but verification fails, move to Step 2.

### Step 2: Repository verification & IAM role layer

Entry symptom: `repository_verification_exception`,
`repository_verification_failed_exception`, or `_snapshot/<repo>` is
registered but every snapshot attempt fails.

Probes in order:

1. **Bucket policy — does it grant the snapshot role?**
   ```bash
   aws s3api get-bucket-policy --bucket <bucket> --output json | jq '.'
   ```
   - The bucket policy MUST grant the snapshot role ARN
     (`arn:aws:iam::<account>:role/<role>`) the actions
     `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`,
     `s3:DeleteObject`, `s3:GetBucketLocation` on
     `arn:aws:s3:::<bucket>` and `arn:aws:s3:::<bucket>/*`.
   - A bucket policy keyed to `"Service": "opensearchservice.amazonaws.com"`
     is INCORRECT — the role's session ARN does not match the
     service principal and verification fails.
   - Missing `s3:GetBucketLocation` → the OpenSearch S3 client
     cannot resolve the bucket Region; verification fails.
     **Confirms IAM_ROLE_S3_ACCESS.**
   - Missing `s3:PutObjectAcl` for cross-account → cross-account
     snapshot write fails the ACL set step. **Confirms
     IAM_ROLE_S3_ACCESS.**

2. **Role policy — does the role grant the S3 actions?**
   ```bash
   aws iam list-attached-role-policies --role-name <role-name> --output json
   aws iam list-role-policies --role-name <role-name> --output json
   aws iam simulate-principal-policy \
     --policy-source-arn "arn:aws:iam::<account>:role/<role>" \
     --action-names s3:PutObject s3:ListBucket s3:GetObject s3:DeleteObject s3:GetBucketLocation \
     --resource-arns "arn:aws:s3:::<bucket>" "arn:aws:s3:::<bucket>/*" \
     --output json
   ```
   - Any action that returns `Decision: implicitDeny` or
     `explicitDeny` confirms the role is missing the permission.
     **Confirms IAM_ROLE_S3_ACCESS.**
   - `simulate-principal-policy` is authoritative; do NOT eyeball
     the policy JSON. SCPs, permissions boundaries, and session
     policies all feed the simulation result.

3. **Is the bucket KMS-encrypted? If so, does the role have
   `kms:Decrypt` and `kms:GenerateDataKey`?**
   ```bash
   aws s3api get-bucket-encryption --bucket <bucket> --output json
   aws iam simulate-principal-policy \
     --policy-source-arn "arn:aws:iam::<account>:role/<role>" \
     --action-names kms:Decrypt kms:GenerateDataKey \
     --resource-arns "<kms-key-arn>" --output json
   ```
   - SSE-KMS bucket where the role lacks `kms:GenerateDataKey` →
     snapshot PUT fails on the first object with `AccessDenied` from
     KMS. **Confirms IAM_ROLE_S3_ACCESS.**

4. **Verification file check.** OpenSearch writes a
   `verification-file-<uuid>` object at the repository root during
   verification, then reads it back. If `s3 ls
   s3://<bucket>/<prefix>/verification-file-*` shows the object,
   write succeeded; the failure is on the read path (KMS, policy,
   or bucket Region). If the object is absent, the failure is on
   the write path (IAM, bucket policy, or wrong `base_path`).

If the role's bucket policy or identity policy is missing a
required S3 action, emit IAM_ROLE_S3_ACCESS. If verification still
fails after IAM is correct, emit REPOSITORY_VERIFICATION with the
verification-file evidence.

### Step 3: Snapshot timeout & shard allocation layer

Entry symptom: snapshot stays `IN_PROGRESS` for hours, or returns
`SNAPSHOT_FAILED` with a `process_cluster_event_timeout_exception`
/ `master_not_discovered_exception`.

Probes in order:

1. **Snapshot status — which shard is stuck?**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>/_status?human" | \
     jq '.snapshots[0].shards_stats, .snapshots[0].indices[].shards.stats'
   ```
   - Look for `stage: INIT` shards (never started) vs
     `stage: TRANSLOCATING` (in flight) vs `stage: FINALIZE` (writing
     manifest). `INIT` shards with no progress indicate the snapshot
     thread is blocked on a master event.

2. **Cluster health and shard assignment.**
   ```bash
   curl -sS "https://$ENDPOINT/_cluster/health?pretty"
   curl -sS "https://$ENDPOINT/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason" | \
     grep -i unassigned
   ```
   - Cluster `status: red` → snapshot will go `PARTIAL` or `FAILED`.
     The root cause is the missing primary shard, not the snapshot.
   - Cluster `status: yellow` → replicas missing; snapshot of
     primaries still works but `INIT` replicas may delay
     `TRANSLOCATING`.

3. **Master node health.**
   ```bash
   curl -sS "https://$ENDPOINT/_cat/master?v"
   curl -sS "https://$ENDPOINT/_nodes/_master/jvm,process"
   ```
   - `master_not_discovered_exception` during a snapshot indicates
     the elected master is overloaded. Dedicated master count < 3 or
     master heap > 30 GB → master instability.

4. **Snapshot thread pool saturation.**
   ```bash
   curl -sS "https://$ENDPOINT/_cat/thread_pool/snapshot?v&h=name,active,queue,rejected"
   ```
   - `rejected > 0` → the snapshot thread pool is saturated; queue
     is full and the snapshot is effectively paused. Raise the
     thread pool or stop competing snapshot work.

If shards are unassigned or master is overloaded, emit
SNAPSHOT_TIMEOUT (snapshot thread blocked) or
SHARD_ALLOCATION_RESTORE (shard allocation failure preventing
finalise). Distinguish by where the shard is stuck:
`SHARD_ALLOCATION_RESTORE` applies when the issue is recovery
throttling on a restore; SNAPSHOT_TIMEOUT applies to backup.

### Step 4: Restore version-compatibility layer

Entry symptom: `_snapshot/<repo>/<snap>/_restore` returns 400 with
`version_not_supported`, `snapshot_restore_failure`, or
`SnapshotImageCorruptedException`.

Probes in order:

1. **Source snapshot engine version.**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>" | \
     jq '.snapshots[0].version.id, .snapshots[0].version.minimum_wire_compatibility_version, .snapshots[0].engine_version'
   ```
   - Compare with the target domain `EngineVersion` from
     `describe-domain`. Source > Target → restore fails on first
     shard. **Confirms RESTORE_VERSION_CONFLICT.**
   - Snapshots from Elasticsearch 7.x can be restored into
     OpenSearch 1.x; from 1.x into 2.x; from 2.x into higher 2.x.
     Skipping a major version requires the snapshot-upgrade flow.

2. **Snapshot-upgrade path for cross-major restores.**
   If you need to restore a 7.x snapshot into a 2.x target, OpenSearch
   supports it only via an intermediate 1.x domain. The intermediate
   domain reads the 7.x snapshot, re-indexes into a 1.x snapshot, then
   the 2.x target reads the 1.x snapshot. The error on a direct
   7.x → 2.x restore is `version_not_supported`.

3. **Read the snapshot's index-level metadata.**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>" | \
     jq '.snapshots[0].indices'
   ```
   - Indices created with features removed in the target version
     (e.g., type-based APIs in 7.x) fail restore at the mapping
     step, not the version check. Note in REMEDIATION.

If source engine version > target engine version, emit
RESTORE_VERSION_CONFLICT with both versions in evidence.

### Step 5: Restore alias conflict layer

Entry symptom: `_restore` returns
`resource_already_allocated_exception` or silently skips some
indices.

Probes in order:

1. **List aliases on the target cluster that match snapshot
   index names.**
   ```bash
   curl -sS "https://$ENDPOINT/_cat/aliases?v&s=alias:desc" | \
     grep -E "<snapshot-alias-pattern>"
   curl -sS "https://$ENDPOINT/_cat/indices/<pattern>?v"
   ```
   - Any index or alias matching a name in the snapshot blocks
     restore. **Confirms RESTORE_ALIAS_CONFLICT.**

2. **Check restore response for skipped indices.**
   ```bash
   curl -sS -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore?wait_for_completion=false" \
     -H 'Content-Type: application/json' -d '
   {"indices": "<pattern>", "rename_pattern": "<from>",
    "rename_replacement": "<to>"}' | jq '.'
   ```
   - `snapshot_restore_response` includes `snapshot.snapshot` and
     optionally a `skipped_indices` list if conflicts were silently
     skipped. `skipped_indices` length > 0 with no error in the
     response indicates silent skip — restore "succeeded" but the
     operator's target index name was not what they expected.

3. **Resolve by renaming on restore or by deleting the conflict.**
   Either delete the conflicting alias / index on the target, or
   rename on restore. Never delete a production alias to "make the
   restore work" without confirmation.

If an alias or index on the target matches a snapshot index name,
emit RESTORE_ALIAS_CONFLICT.

### Step 6: UltraWarm / Cold storage migration layer

Entry symptom: `_plugins/_ism` or `_plugins/_warm` migration returns
`migration_failed`, or index stays on hot tier despite policy.

Probes in order:

1. **Domain warm/cold tier state.**
   ```bash
   aws opensearch describe-domain-config --domain-name <domain> \
     --query 'ClusterConfig.WarmEnabled, ClusterConfig.WarmCount,
       ClusterConfig.WarmType, ColdStorageOptions' --output json
   ```
   - `WarmEnabled: false` → migration fails; nothing to migrate TO.
     **Confirms COLD_STORAGE_MIGRATION.**
   - `WarmCount: < 3` → managed minimum violated; migration fails
     on allocation. **Confirms COLD_STORAGE_MIGRATION.**

2. **Index state management policy.**
   ```bash
   curl -sS "https://$ENDPOINT/_plugins/_ism/policies/<policy-id>" | jq '.'
   curl -sS "https://$ENDPOINT/_plugins/_ism/explain/<index>?v" | jq '.'
   ```
   - `state: <not-migration-state>` → the ISM policy has not reached
     the `migration` action; check the policy's state transitions.
   - `action: { migration: { ... } }` errors → read
     `action_failed_reason` for the allocation block.

3. **Index replicas.** Migration to warm requires at least one
   assigned replica; a primary-only index cannot be migrated.
   ```bash
   curl -sS "https://$ENDPOINT/_cat/indices/<index>?v"
   ```
   - `pri: 1 rep: 0` → migration fails; raise replicas to 1 and
     wait for green before retrying.

If the warm tier is misconfigured or the index lacks replicas,
emit COLD_STORAGE_MIGRATION.

### Step 7: S3 lifecycle deletion layer

Entry symptom: `_snapshot/<repo>/_all` lists snapshots that fail to
restore with `SnapshotMissingException`, or S3 object count drops
unexpectedly.

Probes in order:

1. **Bucket lifecycle configuration.**
   ```bash
   aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json | jq '.'
   ```
   - Any `Expiration` / `NoncurrentVersionExpiration` rule with
     `Days: N` that matches the snapshot prefix → blobs are being
     deleted on schedule. **Confirms S3_LIFECYCLE_DELETION.**
   - Rules scoped by `<prefix>/` to a non-snapshot sub-prefix are
     safe; rules scoped to the entire bucket are dangerous.

2. **S3 server access logs or CloudTrail for s3:DeleteObject.**
   ```bash
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=<bucket> \
     --start-time $(date -d '-7 days' +%s) --end-time $(date +%s) \
     --output json | jq '.Events[] | select(.EventName == "DeleteObject")'
   ```
   - `DeleteObject` events from `s3.amazonaws.com` (lifecycle) or
     from a role you do not expect → lifecycle (or another
     workload) is deleting snapshot blobs.

3. **Cross-check `_snapshot/<repo>/_status` against S3 listing.**
   - Snapshot metadata lists `indices[].shards[].segments` that
     reference `index-N` blobs. `s3 ls s3://<bucket>/<prefix>/indices/<shard-id>/`
     should list every referenced blob. Missing blobs confirm
     deletion.

If the bucket lifecycle deletes snapshot blobs, emit
S3_LIFECYCLE_DELETION.

### Step 8: Concurrent snapshot limit layer

Entry symptom: `_snapshot` returns
`ConcurrentSnapshotExecutionException` immediately.

Probes:

1. **Is a snapshot already in progress?**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/_status" | \
     jq '.snapshots[] | {repository, snapshot, state}'
   ```
   - Any snapshot with `state: IN_PROGRESS` blocks a second into
     the same repository. **Confirms CONCURRENT_SNAPSHOT_LIMIT.**
2. **Is an automated snapshot colliding with the manual schedule?**
   Automated snapshots run at the `AutomatedSnapshotStartHour` into
   the `cs-automated` repository. If your manual schedule writes to
   `cs-automated` prefix (or any prefix the automated job uses), the
   automated job collides with yours. Move the manual schedule to a
   different repository / prefix.

If a snapshot is already in flight, emit CONCURRENT_SNAPSHOT_LIMIT.

### Step 9: Manifest corruption layer

Entry symptom: `_snapshot/<repo>/<snap>/_status` shows
`FAILED: INTERNAL_ERROR`, restore fails with
`CorruptedIndexException` or `SnapshotException` naming a specific
`index-N` blob.

Probes:

1. **Snapshot failure detail.**
   ```bash
   curl -sS "https://$ENDPOINT/_snapshot/<repo>/<snap>" | \
     jq '.snapshots[0].failures'
   ```
   - `failures` array names the shard and the exception. A
     `FileNotFoundException` or `S3Exception: NoSuchKey` in the
     failure indicates a missing blob; a `CorruptedIndexException`
     indicates a truncated or zero-byte blob.

2. **Object existence and size.**
   ```bash
   aws s3api head-object --bucket <bucket> --key <prefix>/indices/<shard-id>/0/index-N | jq '.ContentLength'
   aws s3 ls s3://<bucket>/<prefix>/indices/<shard-id>/0/ --recursive
   ```
   - `ContentLength: 0` → corrupted (zero-byte) blob, almost
     always a partial write during a previous snapshot failure.
     **Confirms MANIFEST_CORRUPTION.**
   - `NoSuchKey` → blob missing; usually an S3 lifecycle deletion
     (cross-reference Step 7).

3. **Repository metadata integrity.**
   ```bash
   aws s3 cp s3://<bucket>/<prefix>/index-0 - | jq '.'
   aws s3 cp s3://<bucket>/<prefix>/index-1 - | jq '.'
   ```
   - The `index-N` blobs at the repo root are the repository
     metadata listing every snapshot. If they fail to parse as
     JSON, the repository metadata is corrupt; re-register the
     repository and re-take snapshots.

If a blob is corrupt or missing AND S3 lifecycle is not the cause,
emit MANIFEST_CORRUPTION.

### Step 10: Cross-region replication layer

Entry symptom: `_plugins/_replication/<index>/_status` shows
`SYNCING` with `last_updated_lag_seconds` rising, or
`REPLICATION_NOT_ALIVE`.

Probes:

1. **Replication status on the follower.**
   ```bash
   curl -sS "https://$FOLLOWER/_plugins/_replication/<index>/_status?pretty"
   ```
   - `status: SYNCING` with high `last_updated_lag_seconds` →
     follower is behind. Check leader snapshot activity (brief lock).
   - `status: PAUSED` or `REPLICATION_NOT_ALIVE` → leader check
     failed; verify leader endpoint, security, and write block on
     follower.

2. **Leader-side settings.**
   ```bash
   curl -sS "https://$LEADER/_cluster/settings?include_defaults=true&filter_path=defaults.index.plugins" | jq '.'
   ```
   - `index.plugins.replication.enabled: true` required on leader.
     Missing → replication cannot start.

3. **Follower engine version vs leader.**
   - Follower MUST be same version or higher than leader. Lower
     follower version → replication fails on first incompatible
     operation.

If the follower lags because of leader snapshot locking, that is
transient; if it lags because of version mismatch or write block,
emit CROSS_REGION_REPLICATION.

### Step 11: CUR / audit log snapshot config layer

Entry symptom: CloudTrail logs or OpenSearch audit logs not landing
in the audit S3 bucket; `SnapshotFromAutoFollow` metric flat.

Probes:

1. **Domain log-publishing options.**
   ```bash
   aws opensearch describe-domain-config --domain-name <domain> \
     --query 'LogPublishingOptions' --output json
   ```
   - `AuditLogs: ENABLED` with a CloudWatch Logs ARN → audit logs
     land in CloudWatch first; the S3 export is a separate stream
     (CloudWatch subscription filter or Kinesis Firehose).
   - `AuditLogs: DISABLED` → no audit logs anywhere; the S3 audit
     bucket will be empty regardless of bucket policy.
     **Confirms CUR_AUDIT_LOG_CONFIG.**

2. **CloudWatch Logs delivery.**
   ```bash
   aws logs describe-log-groups \
     --log-group-name-prefix /aws/opensearch/domains/<domain> --output json
   aws logs filter-log-events \
     --log-group-name /aws/opensearch/domains/<domain>/audit-logs \
     --start-time $(date -d '-1 hour' +%s)000 --output json | jq '.events | length'
   ```
   - Zero events in the audit log group with `AuditLogs: ENABLED`
     → fine-grained access log config on the domain is incomplete;
     enable the audit log categories you need (REST API, auth,
     SSL, etc.).

3. **S3 audit bucket policy.**
   ```bash
   aws s3api get-bucket-policy --bucket <audit-bucket> --output json | jq '.'
   ```
   - For CloudTrail delivery: the bucket policy must grant
     `cloudtrail.amazonaws.com` `s3:GetBucketAcl` and
     `s3:PutObject` with the `aws:SourceArn` condition. Missing
     → CloudTrail trails show "Access Denied" writing to S3.
     **Confirms CUR_AUDIT_LOG_CONFIG.**
   - For Firehose delivery: the bucket policy must grant
     `firehose.amazonaws.com` `s3:PutObject` with
     `aws:SourceAccount` condition.

If the audit/cur stream is misconfigured at the domain or bucket
side, emit CUR_AUDIT_LOG_CONFIG.

### Step 12: INSUFFICIENT_DATA — when none of the layers confirm

If you have run every probe and no failing probe matches the
symptom, emit:

```text
TARGET: <domain-name>
VERDICT: INSUFFICIENT_DATA
REASON: All standard layers (registration, verification, IAM,
  shard allocation, version compatibility, alias conflict, warm
  tier, S3 lifecycle, concurrent snapshot, manifest corruption,
  cross-region replication, audit log config) returned passing
  probes. The symptom may require:
  (a) cluster-level debugging (use opensearch-cluster-troubleshooter),
  (b) AWS Health event investigation (regional OpenSearch incident),
  (c) AWS Support escalation with the snapshot id and repository
      name for service-side log analysis.
LAYER: UNKNOWN
EVIDENCE:
  - Passing probes: <list each probe run with its pass result>
REMEDIATION: Escalate to opensearch-cluster-troubleshooter for
  cluster-state diagnosis, or open an AWS Support case with the
  domain ARN, snapshot id, repository name, and the failing probe
  outputs.
```

## Output specification — diagnostic block

For every diagnosis, emit ONE diagnostic block per target domain.
Do not omit fields. Field order is fixed.

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

- `TARGET` always includes the domain name and, when applicable,
  the repository name and snapshot id.
- `VERDICT` is one of the two enumerated values; never
  `ROOT_CAUSE_FOUND` (that is a different skill family).
- `REASON` names both the layer and the failing probe; "verification
  failed" alone is not enough — name the missing permission or the
  wrong configuration.
- `LAYER` is one of the 14 enumerated values.
- `EVIDENCE` always includes (a) the symptom, (b) the failing probe
  output, and (c) at least one passing probe ruling out a competing
  layer.
- `REMEDIATION` lists specific CLI or API actions, never "fix the
  IAM role" without naming the role and the action to add.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`PUT _snapshot`, `DELETE _snapshot/<repo>`,
  `_snapshot/<repo>/<snap>/_restore`, `update-domain-config`,
  `s3api put-bucket-lifecycle-configuration`), emit and await
  operator approval. Do NOT execute the CLI or curl until the
  operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-domain`, `get-bucket-policy`,
  `simulate-principal-policy`, `_snapshot/_status`, `_cat/recovery`,
  `lookup-events`). Do not perform state-changing operations as
  diagnostic probes.

- **`DELETE _snapshot/<repo>/<snap>`** removes the snapshot from
  the repository; it does NOT delete the S3 blobs (segments are
  deduplicated). Still, confirm before deleting — a deleted snapshot
  cannot be re-referenced without re-taking it.

- **`_snapshot/<repo>/<snap>/_restore`** opens the snapshot's
  indices on the target cluster. If a same-named index exists, the
  restore either skips or fails. Confirm the target cluster state
  before issuing restore.

- **`update-domain-config` to enable UltraWarm / Cold** triggers a
  blue/green deployment. Plan outside traffic peaks; the domain
  endpoint does NOT change but query latency can spike during the
  rolling restart.

- **`s3api put-bucket-lifecycle-configuration`** overwrites the
  existing lifecycle configuration. Always read the current config
  first (`get-bucket-lifecycle-configuration`) and merge the snapshot
  rule rather than overwrite.

- **Re-registering a repository (`PUT _snapshot/<repo>` with the
  same name)** overwrites the prior settings. If the prior
  repository had snapshots, the new registration must point at the
  same S3 bucket + prefix or those snapshots become orphaned.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple repositories (e.g., a missing
  `kms:Decrypt` after a key rotation), batch remediation into
  groups of at most 5 repositories, emit a single CONFIRM per
  batch, and verify between batches.

## Remediation guidance

### For REPOSITORY_REGISTRATION — repository not registered

```bash
# Re-register with the correct body
curl -X PUT "https://$ENDPOINT/_snapshot/<repo>" \
  -H 'Content-Type: application/json' -d '
{
  "type": "s3",
  "settings": {
    "bucket": "<bucket>",
    "region": "<bucket-region>",
    "base_path": "<prefix>",
    "iam_role_arn": "arn:aws:iam::<account>:role/<role>",
    "compress": true
  }
}'
```

Verify:

```bash
curl -sS "https://$ENDPOINT/_snapshot/<repo>" | jq '.'
```

### For REPOSITORY_VERIFICATION — verification failed

1. Update the bucket policy to grant the snapshot role the required
   S3 actions (see IAM_ROLE_S3_ACCESS remediation if the issue is
   IAM).
2. Re-run verification:
   ```bash
   curl -X POST "https://$ENDPOINT/_snapshot/<repo>/_verify?verbose=true"
   ```
3. If verification still fails, delete and re-register the
   repository (CONFIRM before deleting).

### For IAM_ROLE_S3_ACCESS — role or bucket policy missing

Add the minimum-scope permission to the role's identity policy OR
to the bucket policy. Prefer bucket policy for cross-account.

```bash
# Bucket policy granting the snapshot role
aws s3api put-bucket-policy --bucket <bucket> --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenSearchSnapshotRoleAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::<bucket>"
    },
    {
      "Sid": "OpenSearchSnapshotObjectAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"
    }
  ]
}'

# If SSE-KMS, also add kms:Decrypt and kms:GenerateDataKey to the role
aws iam put-role-policy --role-name <role-name> \
  --policy-name KmsAccessForSnapshot \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "<kms-key-arn>"
    }]
  }'
```

Verify with `simulate-principal-policy` (the authoritative check).

### For SNAPSHOT_TIMEOUT — snapshot stuck

1. Resolve the underlying cluster health (red → yellow → green).
2. Raise snapshot thread pool if saturated (advanced setting
   `thread_pool.snapshot.size`).
3. Stop competing snapshots in the same repository.
4. If the snapshot cannot complete because of an unassigned shard,
   either assign the shard or cancel the snapshot:
   ```bash
   curl -X DELETE "https://$ENDPOINT/_snapshot/<repo>/<snap>"
   ```

### For RESTORE_VERSION_CONFLICT — target version too low

1. Upgrade the target domain to the same engine version or higher
   than the source snapshot.
   ```bash
   aws opensearch update-domain-config --domain-name <domain> \
     --engine-version OpenSearch_<target> --profile <p>
   ```
2. Wait for `UpgradeStatus: Succeeded` (cross-version upgrades can
   take hours).
3. Retry the restore after upgrade.

### For RESTORE_ALIAS_CONFLICT — alias or index exists

1. Rename on restore:
   ```bash
   curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore" \
     -H 'Content-Type: application/json' -d '{
     "indices": "<pattern>",
     "rename_pattern": "<from>",
     "rename_replacement": "<to>"
   }'
   ```
2. Or delete the conflicting alias/index (CONFIRM first):
   ```bash
   curl -X DELETE "https://$ENDPOINT/<index-or-alias>"
   ```

### For COLD_STORAGE_MIGRATION — warm/cold misconfig

1. Enable / size the warm tier:
   ```bash
   aws opensearch update-domain-config --domain-name <domain> \
     --cluster-config WarmEnabled=true,WarmCount=3,WarmType=ultrawarm1.medium.search \
     --profile <p>
   ```
2. Raise replicas on the index to at least 1 and wait for green:
   ```bash
   curl -X PUT "https://$ENDPOINT/<index>/_settings" \
     -H 'Content-Type: application/json' -d '{"index": {"number_of_replicas": 1}}'
   ```
3. Retry the migration via ISM policy or the migrate API.

### For S3_LIFECYCLE_DELETION — lifecycle expires snapshots

1. Read the current lifecycle config:
   ```bash
   aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json > lifecycle.json
   ```
2. Remove or scope the offending rule (CONFIRM before applying).
3. Apply the merged config:
   ```bash
   aws s3api put-bucket-lifecycle-configuration --bucket <bucket> \
     --lifecycle-configuration file://lifecycle-merged.json
   ```
4. Re-take snapshots that were lost if a restore-target is missing.

### For CROSS_REGION_REPLICATION — async replication stall

1. Verify leader settings: `index.plugins.replication.enabled: true`.
2. Verify follower write block is off.
3. Verify follower engine version >= leader.
4. Restart replication:
   ```bash
   curl -X POST "https://$FOLLOWER/_plugins/_replication/<index>/_resume"
   ```

### For SHARD_ALLOCATION_RESTORE — recovery throttling

1. Raise `cluster.routing.allocation.node_concurrent_recoveries`
   (advanced setting; default 2).
2. Raise `indices.recovery.max_bytes_per_sec` if network allows.
3. Wait for `_cat/recovery` to show 100% for all shards.

### For MANIFEST_CORRUPTION — corrupt blob

1. Identify the corrupt blob from the snapshot failure detail.
2. Delete the snapshot that references the corrupt blob
   (`DELETE _snapshot/<repo>/<snap>`).
3. Re-take a fresh snapshot; the new snapshot will use healthy
   segments.
4. If the repository metadata itself is corrupt, re-register the
   repository against a clean prefix and re-take all snapshots.

### For CONCURRENT_SNAPSHOT_LIMIT — second snapshot blocked

1. Wait for the in-flight snapshot to complete, OR cancel it
   (CONFIRM before cancelling).
2. Reschedule the manual snapshot cadence to avoid the automated
   snapshot hour, or use a different repository / prefix.

### For CUR_AUDIT_LOG_CONFIG — audit logs missing

1. Enable audit log publishing on the domain:
   ```bash
   aws opensearch update-domain-config --domain-name <domain> \
     --log-publishing-options AuditLogsEnabled=true,CloudWatchLogsLogGroupArn="<log-group-arn>" \
     --profile <p>
   ```
2. Configure the CloudWatch Logs → S3 export (subscription filter
   to Kinesis Firehose, or periodic export).
3. Update the audit bucket policy to grant the delivery role.

## Deep reference: OpenSearch snapshot layer model

### Symptom → layer decision matrix (offline classification)

```
Error string                                        → Layer
repository_verification_exception                    → REPOSITORY_VERIFICATION / IAM_ROLE_S3_ACCESS
PUT _snapshot 4xx                                    → REPOSITORY_REGISTRATION
SnapshotException ConcurrentSnapshotExecutionException → CONCURRENT_SNAPSHOT_LIMIT
snapshot stuck IN_PROGRESS; unassigned shards        → SNAPSHOT_TIMEOUT
restore 400 version_not_supported                    → RESTORE_VERSION_CONFLICT
restore resource_already_allocated_exception         → RESTORE_ALIAS_CONFLICT
migration_failed to warm/cold                        → COLD_STORAGE_MIGRATION
SnapshotMissingException after N days                → S3_LIFECYCLE_DELETION
plugins/replication status SYNCING lag rising        → CROSS_REGION_REPLICATION
cat/recovery stuck at 5%                             → SHARD_ALLOCATION_RESTORE
CorruptedIndexException index-N                      → MANIFEST_CORRUPTION
audit bucket empty; LogPublishingOptions.AuditLogs DISABLED → CUR_AUDIT_LOG_CONFIG
```

### Snapshot role trust policy template (same-account)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "opensearchservice.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "<account-id>"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:es:<region>:<account-id>:domain/<domain-name>"
        }
      }
    }
  ]
}
```

### Snapshot role trust policy template (cross-account)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "opensearchservice.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "<source-account-id>"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:es:<source-region>:<source-account-id>:domain/<source-domain>"
        }
      }
    }
  ]
}
```

### Bucket policy minimum (grant the snapshot role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketForSnapshot",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::<bucket>"
    },
    {
      "Sid": "ReadWriteSnapshotObjects",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"
    }
  ]
}
```

### Engine-version compatibility matrix (snapshot restore)

| Source engine | Target engine | Direct restore? |
|---|---|---|
| Elasticsearch 6.x | ES 7.x | Yes (one major up) |
| ES 7.0–7.9 | ES 7.x same or higher | Yes |
| ES 7.0–7.10 | OpenSearch 1.x | Yes |
| ES 7.0–7.10 | OpenSearch 2.x | No — needs intermediate 1.x |
| OpenSearch 1.x | OpenSearch 1.x same or higher | Yes |
| OpenSearch 1.x | OpenSearch 2.x | Yes (one major up) |
| OpenSearch 2.x | OpenSearch 2.y ≥ 2.x | Yes |
| OpenSearch 2.x | OpenSearch 2.y < 2.x | No — `version_not_supported` |
| OpenSearch 2.x | OpenSearch 1.x | No |

### UltraWarm / Cold tier node-count matrix (managed OpenSearch)

| Tier | Minimum node count | Default node type | Notes |
|---|---|---|---|
| Hot (data) | 2 (HA) | r6g.large.search | Required always |
| Warm (UltraWarm) | 3 | ultrawarm1.medium.search | Added via `update-domain-config` |
| Cold | 1 (with warm) | ultrawarm1.large.search | Requires warm tier enabled first |

Cold storage indices are searchable via the `cold-search` plugin;
queries are slower (disk-backed). Migration to cold requires the
index to have a replica on warm first.

### Snapshot state transitions

| State | Meaning |
|---|---|
| `INIT` | Snapshot request accepted, shards not yet started |
| `STARTED` | Shard snapshots in progress |
| `TRANSLOCATING` | Lucene segments being moved to repository |
| `FINALIZE` | Writing snapshot manifest (`snap-*.dat`) |
| `SUCCESS` | Snapshot metadata written; usable for restore |
| `FAILED` | One or more primary shards failed; snapshot NOT usable |
| `PARTIAL` | Some shards failed; snapshot usable for the successful shards |
| `IN_PROGRESS` | Visible in `_snapshot/_status` while active |

### Snapshot thread pool sizing

| Setting | Default | Effect |
|---|---|---|
| `thread_pool.snapshot.size` | 1 (per node, approximately #CPUs/4) | Concurrent shard-snapshot operations per node |
| `thread_pool.snapshot.queue_size` | 350 | Queue depth before rejects |
| `indices.recovery.max_bytes_per_sec` | 40mb (managed) | Restore shard-recovery throttle |

## Recent AWS features (2024-2026)

- **OpenSearch cross-Region async replication (2024-2025):**
  Index-level async replication via `_plugins/_replication` API.
  Replication stalls when the leader takes a snapshot; this is
  expected, not a bug. Diagnostically, watch
  `last_updated_lag_seconds` rather than `last_replication_completion`.
- **Cold storage GA (2024):** Searchable cold tier via
  `cold-search` plugin. Migration to cold requires warm tier
  enabled and the index to have a warm replica. Operators who "set
  the ISM policy to cold" without enabling warm see
  `migration_failed`.
- **OpenSearch Serverless snapshot (2024-2025):** Serverless
  collections use the managed `cs-automated-aws-owned` repository;
  manual snapshot to a customer S3 bucket is supported via the
  Serverless API. The IAM model differs from managed OpenSearch;
  this skill does not cover Serverless.
- **Snapshot upgrade flow (2024):** OpenSearch 1.x intermediate
  domains can read 7.x snapshots and emit 1.x snapshots for 2.x
  targets. Operators restoring directly from 7.x to 2.x without
  the intermediate step see `version_not_supported`.
- **Managed OpenSearch 2.13+ (2025):** Snapshot repository now
  supports `server_side_encryption` setting explicitly. Bucket-side
  SSE-KMS still requires the role to have `kms:GenerateDataKey`.

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
- **Cross-cluster replication (OpenSearch)** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/replication.html
- **Monitoring OpenSearch Service with CloudWatch metrics** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/monitoring.html
- **Configuring audit logs in OpenSearch Service** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/audit-logs.html
- **S3 bucket policy for OpenSearch snapshots** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/s3-access.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
