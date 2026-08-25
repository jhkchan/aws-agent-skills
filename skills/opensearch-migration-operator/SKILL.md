---
name: opensearch-migration-operator
description: Operates Elasticsearch to OpenSearch migration workflows safely — version compatibility assessment (ES 5.x/6.x/7.x to OpenSearch 1.x/2.x), index migration via snapshot/restore to S3 repository and reindex-from-remote, plugin compatibility (remove ES-only plugins before migration), client compatibility (OpenSearch client vs ES client, compatibility mode), _search API compatibility mode, cluster migration path (in-place upgrade vs new cluster + reindex), snapshot repository setup (S3 repository plugin), downtime planning (blue/green strategy), and OpenSearch 2.x features (neural search, vector DB, flow frameworks). Runs deterministic pre-checks (version compatibility, plugin inventory, snapshot repository health, index mapping compatibility), executes behind a CONFIRM gate, and emits READY, BLOCKED, or COMPLETED per operation with the exact CLI and API sequence. Use for ES-to-OpenSearch migration planning, snapshot repository setup, index reindex, or post-migration verification.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws opensearch describe-domain, aws opensearch describe-domain-config, aws opensearch update-domain-config, aws es describe-elasticsearch-domain (for legacy ES domains), aws es update-elasticsearch-domain-config, aws s3 ls/head for snapshot repository buckets, and curl against the OpenSearch/Elasticsearch _cluster/ health...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Planning or executing an Elasticsearch to OpenSearch migration, assessing version compatibility, setting up S3 snapshot repositories, migrating indices via snapshot/restore or reindex-from-remote, removing ES-only plugins, evaluating in-place upgrade vs new cluster, planning blue/green downtime strategy, configuring OpenSearch client compatibility mode, or verifying post-migration cluster health.
  when_not_to_use: OpenSearch security audits or IAM policy reviews (use opensearch-domain- auditor), OpenSearch performance tuning beyond migration scope (use query and shard analysis directly), building new OpenSearch clusters from scratch (use opensearch-domain-deployer), or OpenSearch index mapping design (application-level work). This skill focuses on the migration operation — not security posture or greenfield deployment.
  activation_triggers: migrate Elasticsearch to OpenSearch, ES to OpenSearch migration, OpenSearch version compatibility, OpenSearch snapshot repository S3, reindex from remote OpenSearch, OpenSearch plugin compatibility, OpenSearch client compatibility mode, in-place upgrade OpenSearch, blue/green migration OpenSearch, OpenSearch 2.x migration, OpenSearch neural search, OpenSearch vector DB, OpenSearch flow frameworks, post-migration verification OpenSearch, Elasticsearch deprecation migration
  invocation_schema: 'Input: either (a) an Elasticsearch/OpenSearch domain configuration with the intended migration operation (assess, snapshot-setup, in-place-upgrade, new-cluster-reindex, blue-green, verify), OR (b) a domain endpoint + API health output for live-account execution. Output: a deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  invocation_example: "# Minimal valid input (offline plan classification):\nDomain: prod-search-cluster\nRegion: us-east-1\nCurrent: Elasticsearch 7.10 (AWS managed)\nTarget: OpenSearch 2.x (AWS managed)\nOperation: assess-migration-readiness\n\nCluster configuration:\n  - ES version: 7.10\n  - Node count: 6 (3 master, 3 data)\n  - Instance type: r6g.large.search\n  - Plugins: analysis-icu, analysis-phonetic, ingest-attachment\n  - Indices: 45 (12 TB total)\n  - Snapshot repository: not configured\n  - Custom plugins: none\n\nEmit the standard VERDICT block."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: OpenSearch, Elasticsearch, migration, version compatibility, snapshot, reindex, S3 repository, plugin compatibility, client compatibility, compatibility mode, blue/green, in-place upgrade, neural search, vector DB, flow frameworks
  tags: opensearch, elasticsearch, analytics, migration, snapshot, reindex, blue-green
---

# OpenSearch Migration Operator

## What this skill does

Executes Elasticsearch to OpenSearch migration operations correctly and
safely. Runs deterministic pre-checks before any state-changing operation,
executes the migration behind a CONFIRM gate, and verifies the result.
Every migration involves version compatibility assessment, plugin
inventory, snapshot repository setup, index migration strategy selection,
and client compatibility verification. A wrong migration path causes
data loss, broken queries, or client connection failures.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order | Before any operation |
| **STRICT output contract** | Mandatory output block format | Before emitting any response |
| **Mindset** | Version compatibility model, snapshot vs reindex, client compatibility | Understanding the migration model |
| **Pre-flight** | Domain metadata gate — version, plugins, snapshot, indices | Before executing any CLI |
| **Process** | Per-operation planning: assess, snapshot, in-place, new-cluster, blue/green, verify | When choosing which operation to run |
| **Expert heuristic** | Non-obvious ES-to-OpenSearch migration behaviours | Review before complex decisions |
| **NEVER** | Anti-patterns that cause data loss, broken clients, or failed migrations | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (incompatible version, ES-only plugin, no snapshot repository, broken index mappings) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI/API sequence, wait for operator yes |
| `COMPLETED` | Migration finished and post-verification passed | Emit new cluster info, verification results, client notes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Version compatibility** — source ES version must be supported for
   the target OpenSearch version. ES 7.x -> OpenSearch 1.x/2.x is
   supported. ES 5.x/6.x requires intermediate upgrade.
2. **Plugin inventory** — all installed plugins must have OpenSearch
   equivalents. ES-only plugins (e.g., commercial X-Pack plugins) must
   be removed or replaced before migration.
3. **Snapshot repository health** — S3 snapshot repository must be
   registered and writable. Required for snapshot/restore migration.
4. **Index mapping compatibility** — index mappings and settings must be
   compatible with the target OpenSearch version.
5. **Client compatibility** — application clients must support OpenSearch
   or use compatibility mode (`compatible=40`).

**Migration timing baselines (2026):**

- Version compatibility assessment: immediate (API check).
- Snapshot repository setup: 5-15 minutes.
- Full snapshot to S3: 10-120 minutes per TB (depends on network and S3
  write throughput).
- In-place upgrade (ES 7.10 -> OpenSearch 1.x): 30-120 minutes (blue/green
  deployment, AWS-managed).
- Reindex from remote: 1-10 hours per TB (depends on network bandwidth,
  index size, and mapping complexity).
- Blue/green new cluster migration: 2-8 hours total (provision new cluster
  + reindex + cutover).

## STRICT output contract

Every migration response MUST emit this block per target domain. No prose
before or after the block; the block is the entire actionable output.

```text
OPERATION: <assess | snapshot-setup | in-place-upgrade | new-cluster-reindex | blue-green | verify>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <domain-name, source-version, target-version>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI or API command with parameters populated>
  2. <wait command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ENDPOINT: <OpenSearch endpoint behavior>
CLIENT_NOTES: <compatibility mode, client library, connection string updates>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <operation> on <domain> in <region>.
  Proceed? (yes/no)"
```

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason.

## Mindset

**One-line takeaway:** ES-to-OpenSearch migration is not a version bump —
it is a fork migration. OpenSearch 1.x derives from ES 7.10.2 (the last
Apache 2.0 licensed version). OpenSearch 2.x diverges further. The
migration path depends on the source version, installed plugins, and
client library.

Driven by four migration realities:

- **Version compatibility determines the path.** ES 7.x can upgrade
  in-place to OpenSearch 1.x (same codebase lineage). ES 5.x/6.x must
  upgrade to 7.x first, then to OpenSearch. Skipping versions requires
  a new cluster + reindex migration. AWS-managed ES domains support
  in-place upgrade to OpenSearch for eligible versions only.

- **Snapshot/restore is the safest migration method.** Register an S3
  repository on both source and target, take a snapshot on the source,
  and restore on the target. This preserves index mappings, settings,
  and data without reindexing. Reindex-from-remote is the fallback when
  snapshot/restore is not possible (e.g., cross-version with breaking
  mapping changes).

- **Plugins are the #1 migration blocker.** ES-only plugins (commercial
  X-Pack features: security, ML, SQL, alerting) do not exist in
  OpenSearch. OpenSearch has its own equivalents (security plugin,
  anomaly detection, SQL plugin, alerting plugin), but their APIs and
  configurations differ. Inventory plugins before planning the migration.

- **Client compatibility mode bridges the gap.** OpenSearch servers can
  respond with `compatible=40` header to mimic ES 7.x responses. This
  allows existing ES client libraries (elasticsearch-py, elasticsearch-js,
  Spring Data Elasticsearch) to work without code changes. But it is a
  bridge, not a permanent solution — migrate to the OpenSearch client
  library for long-term compatibility.

## Pre-flight: domain metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws opensearch describe-domain --domain-name <name>` — confirm
   domain status, EngineVersion, ClusterConfig (instance type, node
   count, dedicated masters), EBSOptions, EncryptionAtRestOptions,
   VPCOptions, SnapshotOptions.
2. `aws es describe-elasticsearch-domain --domain-name <name>` (for
   legacy ES domains) — capture the ES version, cluster config, and
   snapshot configuration.
3. `curl -s https://<endpoint>/ _cluster/health` — cluster status
   (green/yellow/red), number of nodes, active shards, relocating
   shards.
4. `curl -s https://<endpoint>/ _cat/indices?v` — index list, document
   counts, store sizes.
5. `curl -s https://<endpoint>/ _cat/plugins?v` — installed plugins.
6. `curl -s https://<endpoint>/ _nodes/plugins` — detailed plugin info
   per node.
7. `curl -s https://<endpoint>/ _snapshot` — registered snapshot
   repositories.
8. `curl -s https://<endpoint>/ _mapping` — index mappings for
   compatibility assessment.

**Malformed input:** if the input is invalid or missing required fields,
emit `VERDICT: BLOCKED` with `REASON: Domain/operation configuration is
not valid or is missing required fields — cannot plan.`

| Domain attribute | Effect on migration |
|---|---|
| `EngineVersion: Elasticsearch_7.10` | Can upgrade in-place to OpenSearch 1.x or 2.x. |
| `EngineVersion: Elasticsearch_6.x or 5.x` | Must upgrade to 7.x first or use new-cluster + reindex. |
| `EngineVersion: OpenSearch_2.x` | Already on OpenSearch — verify post-migration. |
| ES-only plugins installed | Must remove or replace before migration. |
| No snapshot repository configured | BLOCKED for snapshot/restore migration — set up S3 repository first. |
| Cluster status `red` | BLOCKED — fix cluster health before migration. |
| Cluster status `yellow` | Warn — replica shards unavailable; migration proceeds but verify. |
| Dedicated masters enabled | AWS manages blue/green deployment; in-place upgrade is smoother. |
| EncryptionAtRest enabled | KMS key follows the domain; no migration impact. |
| VPC-only domain | Endpoint is internal; client access requires VPC connectivity. |

## Process — operation planning (apply in order)

### Step 0: Expert heuristic — non-obvious ES-to-OpenSearch migration behaviours

These behaviours are easy to misjudge without migration experience. Each
changes a plan if ignored:

- **OpenSearch 1.x is a direct fork of ES 7.10.2.** Index format, Lucene
  version, and mappings are compatible. An in-place upgrade from ES 7.10
  to OpenSearch 1.x is the lowest-risk path. OpenSearch 2.x introduces
  breaking changes in some APIs and requires careful testing.

- **Snapshot format compatibility is version-dependent.** Snapshots taken
  on ES 7.x can be restored on OpenSearch 1.x. Snapshots from ES 6.x
  cannot be restored on OpenSearch 2.x directly — they need an
  intermediate restore on ES 7.x or OpenSearch 1.x first. Always verify
  snapshot version compatibility before planning restore.

- **AWS-managed domains upgrade via blue/green deployment.** When you
  update the engine version on an AWS OpenSearch domain, AWS provisions
  a new set of nodes with the target version, migrates data, and switches
  traffic. The domain endpoint does NOT change. There is brief
  degradation during the switch (increased latency, possible dropped
  connections). Plan for 30-120 minutes of degraded performance.

- **Reindex-from-remote requires the remote cluster to be network-
  accessible.** The target OpenSearch cluster must reach the source ES
  cluster's endpoint. For VPC-only domains, this requires VPC peering,
  Transit Gateway, or a VPN. Reindex-from-remote does NOT preserve
  index settings — you must create the target index with the correct
  settings and mappings before reindexing.

- **The `compatible=40` query parameter enables ES 7.x compatibility
  mode.** Append `?compatible=40` to API requests, and OpenSearch responds
  with ES 7.x-compatible JSON. This is a bridge for existing ES clients.
  OpenSearch 2.11+ supports this. It does NOT enable ES-specific features
  like `_xpack` APIs — it only adjusts response format.

- **OpenSearch security plugin replaces X-Pack security.** If the ES
  domain uses X-Pack security (roles, users, index-level permissions),
  the OpenSearch security plugin provides equivalent features but uses
  a different configuration format (config.yml, internal_users.yml,
  roles.yml). Plan for security configuration migration.

- **OpenSearch SQL plugin has a different API endpoint.** ES SQL uses
  `_xpack/sql`; OpenSearch SQL uses `_plugins/_sql`. Applications that
  call ES SQL endpoints must update their API paths.

- **The OpenSearch Java high-level REST client is deprecated.** Use the
  `opensearch-java` client (the new Java client) or the `opensearch-rest-client`.
  The old `elasticsearch-rest-high-level-client` works with compatibility
  mode but is no longer maintained.

- **Index settings may need adjustment.** ES 7.x allows some index-level
  settings that OpenSearch handles differently (e.g., `index.codec`).
  When restoring snapshots across versions, OpenSearch may reject unknown
  settings. Strip incompatible settings before restore.

- **AWS OpenSearch Serverless is NOT a migration target for existing
  provisioned clusters.** Serverless has different indexing and search
  behavior (no `_all` field, different collection model). Migrate to
  provisioned OpenSearch first, then evaluate Serverless separately.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is BLOCKED
with the failed checks enumerated in PRE_CHECKS. Do NOT execute.

**For ALL migration operations:**
1. Domain status is `Active` (not `Processing`, `Upgrading`).
2. Cluster health is `green` or `yellow` (not `red`).
3. No active index creation, shard relocation, or recovery in progress.
4. IAM role for the operator holds `es:ESHttp*` and
   `opensearch:ESHttp*` permissions.

**For version compatibility assessment:**
5. Source ES version is identified (5.x, 6.x, 7.x, or OpenSearch 1.x).
6. Target OpenSearch version is identified (1.x or 2.x).
7. Version compatibility matrix is checked (see § Version compatibility
   matrix below).

**For snapshot/restore migration:**
5. S3 bucket exists and is accessible.
6. IAM role has `s3:ListBucket`, `s3:GetObject`, `s3:PutObject` on the
   bucket.
7. Snapshot repository plugin is installed (repository-s3 for
   self-managed; automatic for AWS-managed).
8. Repository is registered on both source and target clusters.
9. Test snapshot write/read succeeds.

**For in-place upgrade:**
5. Source version is ES 7.10 (the only version eligible for direct
   in-place upgrade to OpenSearch on AWS).
6. No ES-only commercial plugins installed.
7. Domain has dedicated masters enabled (recommended for blue/green
   deployment).
8. EBS volume size has headroom for reindexing during upgrade.

**For new-cluster + reindex migration:**
5. Target OpenSearch domain is provisioned and accessible.
6. Network connectivity exists between source and target (especially for
   VPC-only domains).
7. Target indices created with correct mappings and settings.
8. Reindex-from-remote is enabled on the target cluster
   (`"reindex.remote.whitelist": "<source-endpoint>:443"`).

**For client compatibility verification:**
5. Application client library version is identified.
6. Compatibility mode (`compatible=40`) tested against target cluster.
7. All application API calls tested against OpenSearch endpoints.

### Step 2: Version compatibility matrix

| Source version | Target version | Migration path | Risk |
|---|---|---|---|
| ES 5.x | OpenSearch 1.x | Upgrade to ES 6.x -> 7.x -> OS 1.x (multiple steps) | HIGH |
| ES 5.x | OpenSearch 2.x | New cluster + reindex (no direct path) | HIGH |
| ES 6.x | OpenSearch 1.x | Upgrade to ES 7.x -> OS 1.x | MEDIUM |
| ES 6.x | OpenSearch 2.x | New cluster + reindex | MEDIUM |
| ES 7.x | OpenSearch 1.x | In-place upgrade (direct fork lineage) | LOW |
| ES 7.x | OpenSearch 2.x | In-place to OS 1.x -> upgrade to OS 2.x | LOW-MEDIUM |
| OpenSearch 1.x | OpenSearch 2.x | In-place upgrade | LOW |
| OpenSearch 2.x | OpenSearch 2.x (newer) | In-place upgrade | LOW |

### Step 3: Plugin compatibility assessment

| ES plugin | OpenSearch equivalent | Action |
|---|---|---|
| analysis-icu, phonetic, kuromoji, smartcn | Built-in | No action — pre-installed on OpenSearch |
| ingest-attachment | Built-in | No action — pre-installed |
| mapper-murmur3, annotated-text | Built-in | No action — pre-installed |
| x-pack-security | OpenSearch security plugin | Migrate security config (config.yml, roles.yml) |
| x-pack-ml | OpenSearch anomaly detection | Reconfigure ML jobs |
| x-pack-sql | OpenSearch SQL plugin | Update API paths (`_plugins/_sql`) |
| x-pack-alerting | OpenSearch alerting plugin | Reconfigure monitors and destinations |
| x-pack-monitoring | OpenSearch performance analyzer | Reconfigure monitoring |

### Step 4: Snapshot repository setup (S3)

If the migration uses snapshot/restore, the S3 repository must be set up
on both source and target.

**For AWS-managed domains:** the S3 repository is configured via the
domain's snapshot configuration. AWS automatically manages the
repository-s3 plugin.

```json
PUT _snapshot/s3-migration-repo
{
  "type": "s3",
  "settings": {
    "bucket": "migration-snapshots-bucket",
    "region": "us-east-1",
    "base_path": "opensearch-migration",
    "role_arn": "arn:aws:iam::111111111111:role/OpenSearchSnapshotRole"
  }
}
```

**Verify the repository:**
```
POST _snapshot/s3-migration-repo/_verify
```

Returns the list of nodes that can write to the repository. All data
nodes must report `success`.

### Step 5: Snapshot and restore migration

On the source cluster, create a snapshot:
```
PUT _snapshot/s3-migration-repo/snapshot_1?wait_for_completion=true
{"indices":"index1,index2,index3","ignore_unavailable":true,"include_global_state":false}
```

On the target cluster, register the same repository, then restore:
```
POST _snapshot/s3-migration-repo/snapshot_1/_restore?wait_for_completion=false
{"indices":"index1,index2,index3","ignore_unavailable":true,"include_global_state":false,"rename_pattern":"(.+)","rename_replacement":"$1"}
```

Monitor restore progress: `GET _cat/recovery?v` and
`GET _cluster/health?wait_for_status=green&timeout=60s`.

### Step 6: Reindex-from-remote migration

When snapshot/restore is not possible (cross-major-version, incompatible
mappings), use reindex-from-remote.

On the target cluster, reindex from the remote source:
```
POST _reindex?wait_for_completion=false
{"source":{"remote":{"host":"https://search-source-es-cluster.us-east-1.es.amazonaws.com:443"},"index":"source-index","size":5000},"dest":{"index":"target-index"}}
```

**IMPORTANT:** The target index must be created with the correct mappings
and settings BEFORE reindexing. Reindex does NOT copy mappings or
settings from the source.

**For AWS-managed VPC domains:** the target domain's security group must
allow inbound HTTPS from the source domain's VPC, or use VPC peering /
Transit Gateway for cross-VPC connectivity.

### Step 7: In-place upgrade (ES 7.10 to OpenSearch)

For AWS-managed domains, the in-place upgrade is triggered via:

```bash
aws opensearch update-domain-config \
  --domain-name prod-search-cluster \
  --engine-version OpenSearch_2.11 \
  --region us-east-1
```

AWS performs a blue/green deployment:
1. Provisions new nodes with OpenSearch.
2. Migrates data from old nodes to new nodes.
3. Routes traffic to the new nodes.
4. Decommissions the old nodes.

The domain endpoint does NOT change. Monitor the upgrade status:

```bash
aws opensearch describe-domain \
  --domain-name prod-search-cluster \
  --query 'DomainStatus.{Status:Processing, UpgradeProcessing:UpgradeProcessing, EngineVersion:EngineVersion}' \
  --output json
```

### Step 8: Blue/green new cluster migration

For complex migrations (multiple version jumps, plugin incompatibilities),
provision a new OpenSearch domain and migrate indices.

**Strategy:**
1. Provision new OpenSearch domain.
2. Register S3 snapshot repository on both clusters.
3. Snapshot all indices from the source.
4. Restore on the target.
5. Verify data completeness (document counts, mapping fidelity).
6. Update application connection strings to the new endpoint.
7. Decommission the source cluster after a verification window.

**Downtime:** Near-zero if the source cluster remains read-write during
the migration. Applications write to the source; reindex or snapshot-
restore copies data; final cutover requires a brief write freeze for
delta sync.

### Step 9: Client compatibility verification

After migration, verify that application clients work correctly against
the OpenSearch endpoint.

| Client library | Compatibility | Action |
|---|---|---|
| elasticsearch-py/js/go 7.x | Works with `compatible=40` | Long-term: migrate to opensearch-* equivalent |
| Spring Data Elasticsearch | Works with `compatible=40` | Long-term: migrate to Spring Data OpenSearch |
| opensearch-py / @opensearch-project/opensearch | Native OpenSearch | No action needed |

**Testing procedure:** Point the application at the OpenSearch endpoint
with `?compatible=40`. Run the integration test suite. Verify search
results match the ES baseline. Test index, update, and delete operations.
Aggregation queries are the most likely to differ — test them first.

### Step 10: Post-verification — COMPLETED

After the migration finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. Cluster health is `green` on the target OpenSearch domain.
2. Document counts match between source and target indices.
3. Index mappings are preserved or correctly migrated.
4. All application search queries return correct results.
5. Client compatibility mode (`compatible=40`) works for existing ES
   clients.
6. Snapshot repository is registered and functional on the target.
7. No red shards or unassigned replicas.
8. Monitoring and alerting are configured on the target domain.

If ANY verification fails, emit `VERDICT: ERROR` with failure details —
do not claim COMPLETED.

## Output format

See § STRICT output contract for the mandatory block. Worked examples
below.

### Worked example — migration readiness assessment (READY)

```text
OPERATION: assess
VERDICT: READY
TARGET: prod-search-cluster (ES 7.10 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] Domain status is Active
  - [PASS] Cluster health is green (45 indices, 12 TB)
  - [PASS] Source version Elasticsearch_7.10 is eligible for in-place upgrade
  - [PASS] All installed plugins (analysis-icu, analysis-phonetic, ingest-attachment) have OpenSearch equivalents
  - [PASS] No ES-only commercial plugins detected
  - [PASS] No active shard relocation or recovery in progress
STEPS:
  1. Set up S3 snapshot repository (if not already configured):
     PUT _snapshot/s3-migration-repo {"type":"s3","settings":{"bucket":"migration-snapshots","region":"us-east-1","base_path":"opensearch-migration"}}
  2. Take a pre-upgrade full snapshot:
     PUT _snapshot/s3-migration-repo/pre-upgrade-snapshot?wait_for_completion=true {"indices":"*","ignore_unavailable":true,"include_global_state":true}
  3. CONFIRM: About to update-domain-config on prod-search-cluster to OpenSearch_2.11. Blue/green deployment will take 30-120 minutes. Proceed? (yes/no)
  4. aws opensearch update-domain-config --domain-name prod-search-cluster --engine-version OpenSearch_2.11 --region us-east-1
  5. Monitor: aws opensearch describe-domain --domain-name prod-search-cluster --query 'DomainStatus.{Processing:Processing,EngineVersion:EngineVersion}'
POST_VERIFY: (pending execution)
ENDPOINT: https://search-prod-search-cluster.us-east-1.es.amazonaws.com (unchanged — AWS blue/green preserves the endpoint)
CLIENT_NOTES:
  - OpenSearch 2.11 supports compatible=40 for ES 7.x clients.
  - Test all application search queries with compatibility mode before full cutover.
  - Plan to migrate client libraries from elasticsearch-* to opensearch-* within 3-6 months.
```

### Worked example — migration BLOCKED (ES-only plugin)

```text
OPERATION: assess
VERDICT: BLOCKED
TARGET: legacy-search-cluster (ES 6.8 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] Domain status is Active
  - [PASS] Cluster health is green
  - [FAIL] Source version Elasticsearch_6.8 is NOT eligible for direct in-place upgrade. Must upgrade to ES 7.10 first, or use new-cluster + reindex migration path.
  - [FAIL] ES-only plugin x-pack-ml is installed. No direct OpenSearch equivalent (OpenSearch anomaly detection uses a different API). Must remove and reconfigure before migration.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ENDPOINT: N/A — migration blocked
CLIENT_NOTES:
  - BLOCKED: Remediation required before migration can proceed.
  - Option A: Upgrade ES 6.8 to 7.10 (if supported), remove x-pack-ml, then migrate to OpenSearch.
  - Option B: Provision new OpenSearch 2.x cluster, reindex from remote, reconfigure ML jobs as OpenSearch anomaly detectors.
  - Reindex-from-remote requires network connectivity between the ES 6.8 domain and the new OpenSearch domain.
```

### Worked example — COMPLETED (blue/green migration verified)

```text
OPERATION: blue-green
VERDICT: COMPLETED
TARGET: prod-search-cluster (ES 7.10 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] (all pre-checks passed before execution)
STEPS:
  1. Pre-upgrade snapshot taken at 2026-08-10T08:00:00Z
  2. aws opensearch update-domain-config executed at 2026-08-10T08:15:00Z
  3. Blue/green deployment completed at 2026-08-10T09:45:00Z (90 min)
POST_VERIFY:
  - [PASS] Cluster health is green
  - [PASS] Document counts match (45 indices, 2.1B docs)
  - [PASS] Index mappings preserved correctly
  - [PASS] Application search queries return correct results (100% match)
  - [PASS] compatible=40 mode works for elasticsearch-py 7.17 clients
  - [PASS] Snapshot repository s3-migration-repo is registered
  - [PASS] No red shards or unassigned replicas
  - [PASS] OpenSearch plugins confirmed: analysis-icu, analysis-phonetic, ingest-attachment
ENDPOINT: https://search-prod-search-cluster.us-east-1.es.amazonaws.com (unchanged)
CLIENT_NOTES:
  - Blue/green migration completed (90 min). compatible=40 is active for ES 7.x clients.
  - Plan to migrate client libraries to opensearch-* within 3-6 months.
  - Test neural search and vector DB features available in OpenSearch 2.11.
```

### Worked example — snapshot setup and migration (READY)

```text
OPERATION: snapshot-setup
VERDICT: READY
TARGET: staging-search-cluster (ES 7.10 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] Domain status is Active
  - [PASS] Cluster health is green
  - [PASS] S3 bucket migration-snapshots exists and is writable
  - [PASS] IAM role OpenSearchSnapshotRole has s3:PutObject, s3:GetObject, s3:ListBucket
  - [PASS] No existing repository named s3-migration-repo
STEPS:
  1. Register S3 repo: PUT _snapshot/s3-migration-repo {"type":"s3","settings":{"bucket":"migration-snapshots","region":"us-east-1","base_path":"staging-migration","role_arn":"arn:aws:iam::111111111111:role/OpenSearchSnapshotRole"}}
  2. Verify: POST _snapshot/s3-migration-repo/_verify
  3. Take full snapshot: PUT _snapshot/s3-migration-repo/staging-full-snapshot?wait_for_completion=true {"indices":"*","ignore_unavailable":true,"include_global_state":false}
  4. Confirm: GET _snapshot/s3-migration-repo/staging-full-snapshot
POST_VERIFY: (pending execution)
ENDPOINT: N/A (snapshot setup — no client impact)
CLIENT_NOTES: N/A (snapshot setup — no client impact)
```

## Expert heuristic — non-obvious ES-to-OpenSearch migration behaviours

| Heuristic | Impact on plan |
|---|---|
| OpenSearch 1.x is a direct fork of ES 7.10.2 | In-place upgrade from ES 7.10 to OS 1.x is the lowest-risk path |
| Snapshots from ES 6.x cannot restore on OpenSearch 2.x | Use intermediate restore or reindex-from-remote for ES 6.x sources |
| AWS blue/green deployment preserves the domain endpoint | No connection-string change for in-place upgrades |
| Reindex-from-remote requires network connectivity | VPC-only domains need VPC peering or Transit Gateway |
| compatible=40 is a bridge, not permanent | Plan client library migration within 3-6 months |
| OpenSearch SQL uses _plugins/_sql, not _xpack/sql | Update API paths in application code |
| OpenSearch security plugin replaces X-Pack security | Migrate roles and users to config.yml format |
| Index settings may need stripping before cross-version restore | Remove unknown settings that OpenSearch rejects |
| Neural search, vector DB, flow frameworks are OS 2.x features | Evaluate post-migration for ML-powered search and automated pipelines |

## Anti-Patterns — NEVER (top 5)

1. NEVER start a migration without a verified snapshot. If the migration
   fails or corrupts data, the snapshot is the only rollback path. Always
   take a full snapshot before any in-place upgrade or reindex operation.
   Verify the snapshot repository with `_verify` before trusting it.

2. NEVER attempt an in-place upgrade with ES-only commercial plugins
   installed. X-Pack plugins (security, ML, SQL, alerting) do not exist
   in OpenSearch. The upgrade will fail or produce a broken cluster.
   Inventory plugins with `_cat/plugins` and remove or replace ES-only
   plugins before migration.

3. NEVER skip the version compatibility matrix check. ES 5.x/6.x cannot
   upgrade directly to OpenSearch — skipping versions requires a new
   cluster + reindex migration. Attempting an unsupported version jump
   results in a failed upgrade or data format incompatibility.

4. NEVER assume client compatibility without testing. The `compatible=40`
   header makes OpenSearch respond like ES 7.x, but it does NOT replicate
   ES-specific API endpoints (`_xpack/*`). Test every application API
   call against the target before cutover. Aggregation queries are the
   most likely to differ.

5. NEVER decommission the source cluster immediately after migration.
   Keep the source running for a verification window (minimum 7 days
   recommended). If post-migration issues are discovered, the source
   cluster is the fallback. Decommission only after all verification
   checks pass and the team confirms the new cluster handles production
   traffic.

## Pre-flight safety checks (run before any migration CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing migration
  operation (`update-domain-config`, `_snapshot`, `_restore`, `_reindex`),
  emit the CONFIRM prompt. Do NOT execute until the operator confirms.
- **Snapshot before upgrade.** Take a full snapshot to the S3 repository
  before any in-place upgrade. This is the rollback path.
- **Verify snapshot repository.** `POST _snapshot/<repo>/_verify` must
  show all data nodes reporting success.
- **Check cluster health.** Cluster must be `green` (or `yellow` with
  documented reason). `red` means data loss risk — BLOCK.
- **Inventory plugins.** `_cat/plugins` must show no ES-only commercial
  plugins for in-place upgrade path.
- **Test network connectivity.** For reindex-from-remote, verify the
  target can reach the source endpoint on port 443.
- **Verify IAM permissions.** The migration role needs `es:ESHttp*` or
  `opensearch:ESHttp*` plus `s3:*` on the snapshot bucket.
- **Schedule during low-traffic windows.** Blue/green deployment causes
  degraded performance (30-120 minutes). Plan for off-peak.
- **One domain per CONFIRM gate.** Do NOT batch multiple domain
  migrations — a systematic issue cascades across domains.

## Recent AWS features (2024-2026)

- **OpenSearch 2.11+ compatible mode (2024):** The `compatible=40` query
  parameter makes OpenSearch respond with ES 7.x-compatible JSON. Bridges
  existing ES clients without code changes. Does NOT replicate ES-specific
  API endpoints — only adjusts response format.

- **Neural search plugin (2024-2025):** ML-powered semantic search using
  text embeddings. Available as a processor in search pipelines. Requires
  an ML model deployed via the OpenSearch ML Commons plugin.

- **Vector DB engine (2024-2025):** Native vector storage and approximate
  nearest neighbor (ANN) search using the k-NN plugin. Supports FAISS,
  NMSLIB, and Lucene engines. Enables LLM-powered RAG applications
  directly on OpenSearch.

- **Flow frameworks (2024-2025):** Automated ML pipeline creation for
  ingestion and search. Templates for common workflows (neural search
  setup, RAG pipeline, anomaly detection). Reduces setup complexity for
  AI-powered search use cases.

- **OpenSearch 2.13+ segment replication (2024):** Segment-level
  replication instead of document-level. Reduces CPU on primary shards
  during heavy write workloads. Available as an index-level setting.

- **AWS OpenSearch Serverless (2024-2025):** Auto-scaling serverless
  OpenSearch with simplified capacity management. NOT a direct migration
  target for provisioned clusters — different indexing and search behavior.

- **OpenSearch 2.15+ stored fields compression (2025):** Improved
  compression for stored fields reduces storage costs by 10-30%.

- **Cross-cluster replication (2024-2025):** Active-active and active-
  passive replication between OpenSearch clusters. Useful for DR and
  multi-region search.

## References

- `references/migration-procedures.md` — detailed CLI/API scripts for
  snapshot setup, reindex-from-remote, plugin inventory, and
  post-migration verification

## Domain

AWS CloudOps / Elasticsearch to OpenSearch Migration Operations.

## AWS documentation

- **Amazon OpenSearch Service Developer Guide** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html
- **Upgrading Amazon OpenSearch Service** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-maturity.html
- **Migrating to Amazon OpenSearch Service** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/migration.html
- **Snapshot management in OpenSearch Service** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html
- **OpenSearch-compatible APIs** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/use-casees.html
- **OpenSearch Plugin Reference** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/supported-plugins.html
- **OpenSearch documentation** — https://opensearch.org/docs/latest/
- **OpenSearch version compatibility** — https://opensearch.org/docs/latest/upgrade-to/upgrade-to/
- **OpenSearch neural search** — https://opensearch.org/docs/latest/search-plugins/neural-search/
- **OpenSearch k-NN (vector DB)** — https://opensearch.org/docs/latest/search-plugins/knn/index/
- **OpenSearch flow frameworks** — https://opensearch.org/docs/latest/observing-your-data/flow-framework/
- **AWS CLI OpenSearch reference** — https://docs.aws.amazon.com/cli/latest/reference/opensearch/
- **AWS Well-Architected Framework — Operational Excellence** — https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html
