---
name: opensearch-index-deployer
description: 'Provisions Amazon OpenSearch Service indices with production defaults: index creation with explicit mappings (dynamic vs strict), shard count (primary + replica) sizing targeting 10-50 GB per shard, ILM policies with hot/warm/cold tiering, force merge for read-only indices, snapshot management (automated + manual to S3), alias management for zero-downtime reindexing, index templates and component templates, rollover aliases, data streams for time-series, search pipeline configuration, k-NN vector search index configuration, and field type mapping (keyword vs text, nested vs object). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an OpenSearch index, configuring shard count, setting up ILM, managing aliases, creating index templates, or configuring data streams. Triggers: create opensearch index, opensearch shard sizing, opensearch ilm policy, opensearch alias reindex, opensearch index template, opensearch knn vector, opensearch data stream.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with opensearch access (sigv4 or basic auth), or the OpenSearch Dev Tools console. Works with Terraform opensearch_index / opensearch_domain resources and CloudFormation AWS::OpenSearchService::Domain templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, opensearch, index-management, cloudops, deploy, analytics, provisioning, ilm, shard-sizing, alias-reindex, knn-vector, data-stream
  dependencies: aws-orchestrator
  keywords: aws, opensearch, elasticsearch, index management, cloudops, deploy, provisioning, shard sizing, ilm, index lifecycle, hot warm cold, force merge, snapshot, alias reindex, index template, component template, rollover, data stream, knn vector, search pipeline
  when_to_use: Invoke when the user wants to create an OpenSearch Service index with mappings and shard sizing, configure ILM policies for hot/warm/cold storage tiering, set up aliases for zero-downtime reindexing, deploy index templates or component templates, configure data streams for time-series data, deploy k-NN vector search indices, configure search pipelines, or manage snapshots to S3. Do NOT invoke for OpenSearch domain-level provisioning (use opensearch-domain-deployer), OpenSearch Serverless (use opensearch-serverless-deployer), or OpenSearch domain auditing (use opensearch-domain-auditor).
---

# OpenSearch Index Deployer

An AWS CloudOps agent skill that provisions Amazon OpenSearch Service
indices with production-grade defaults. The skill walks the operator
through index mapping decisions (dynamic vs strict), shard sizing
(primary + replica for read throughput), ILM policy configuration for
storage tiering (hot/warm/cold), alias management for zero-downtime
reindexing, index and component templates, data streams for time-series
workloads, k-NN vector search configuration, search pipeline setup, and
snapshot management, captures all configuration decisions, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create OpenSearch index, OpenSearch shard sizing, OpenSearch ILM policy,
OpenSearch alias reindex, OpenSearch index template, OpenSearch k-NN
vector, OpenSearch data stream, OpenSearch snapshot repository.

## STRICT output contract

When this skill is invoked with an OpenSearch index-provisioning
request (create an index, configure shards, set up ILM, manage aliases
for reindexing, create index templates, deploy k-NN vector search,
configure data streams, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels
`OPENSEARCH_INDEX:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Domain connectivity and auth | Connecting to the cluster |
| Step 2 — Index mappings (dynamic vs strict) | Schema design |
| Step 3 — Shard sizing (primary + replica) | Performance + cost |
| Step 4 — ILM policies (hot/warm/cold tiering) | Storage lifecycle |
| Step 5 — Alias management for zero-downtime reindex | Reindex workflow |
| Step 6 — Index templates and component templates | Blueprint for new indices |
| Step 7 — Rollover aliases and data streams | Time-series workloads |
| Step 8 — k-NN vector search configuration | Semantic / similarity search |
| Step 9 — Search pipeline configuration | Query-time processing |
| Step 10 — Snapshot management (S3) | Backup and recovery |
| Step 11 — Force merge for read-only indices | Storage optimization |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/shard-sizing-and-ilm.md | Shard + ILM deep dive |
| references/templates-and-data-streams.md | Template + data stream detail |

## Mindset

**One-line takeaway:** An OpenSearch index's performance, cost, and
operability are determined at creation time. Shard count (target 10-50
GB per shard), replica count (read throughput + HA), ILM rollover
(automatic tiering), and mapping strictness (dynamic vs strict) are
the four levers. Getting them wrong at creation means expensive
reindexing later.

Three misconceptions dominate OpenSearch index misdesign at provisioning
time:

- **"Use the default 5 primary shards for every index."** Default shard
  counts are rarely right. A 1 GB index with 5 primaries creates 200 MB
  shards — far below the 10-50 GB sweet spot, wasting resources and
  overhead. A 500 GB index with 5 primaries creates 100 GB shards — too
  large, causing slow searches and recovery. Shard count must match data
  volume.

- **"Replicas are only for high availability."** Replicas ALSO scale
  read throughput. Each replica shard can serve search queries
  independently. If read QPS is high, adding replicas (1 to 2 to 3) is
  often more cost-effective than larger instances.

- **"Dynamic mappings are fine for production."** Dynamic mapping
  (default) lets OpenSearch auto-guess field types. This leads to
  keyword fields being treated as text, nested objects being flattened,
  and numbers being mapped as float. In production, use
  `"dynamic": "strict"` to reject unmapped fields, or explicitly map
  every field.

## Configuration dependency graph (novel heuristic)
> Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
> Read it only when this section applies.


## Expert heuristic: shard sizing (10-50 GB per shard)
> Moved verbatim to [references/shard-sizing-and-ilm.md](references/shard-sizing-and-ilm.md) — load on demand.
> Read it only when this section applies.


## Expert heuristic: replica count for read throughput
> Moved verbatim to [references/shard-sizing-and-ilm.md](references/shard-sizing-and-ilm.md) — load on demand.
> Read it only when this section applies.


## Expert heuristic: ILM rollover for storage tiering
> Moved verbatim to [references/shard-sizing-and-ilm.md](references/shard-sizing-and-ilm.md) — load on demand.
> Read it only when this section applies.


## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| OpenSearch domain endpoint reachable | Index APIs require domain connectivity | `GET _cluster/health` |
| Auth credentials (sigv4 or basic auth) | Domain requires authenticated access | Verify IAM policy or master user credentials |
| Cluster health yellow or green | Red cluster may reject index creation | `GET _cluster/health` |
| Estimated data volume known | Determines primary shard count (10-50 GB target) | Estimate from source data size |
| Node count supports replica placement | Replicas need separate nodes from primaries | `GET _cat/nodes` |
| Disk space available (50%+ free) | OpenSearch recommends 50% free disk | `GET _cat/allocation?v` — `disk.percent` < 50 |
| Snapshot S3 bucket exists (if snapshots) | Manual snapshot repository needs S3 | `aws s3 ls s3://<bucket>` |
| k-NN plugin enabled (if k-NN index) | k-NN requires the plugin on the domain | `GET _plugins/_knn/stats` |

## Step 1 — Domain connectivity and auth

Amazon OpenSearch Service supports IAM sigv4 (recommended) and master-
user basic auth (fine-grained access control).

**Verify cluster health before index creation:**

```bash
curl -s "https://<endpoint>/_cluster/health?pretty" -u "user:pass"
# Expected: "status": "green" or "yellow"
# If "red": resolve cluster health before creating indices
```

For IAM sigv4, use the opensearch-py client with AWS4Auth or the
`aws opensearch` CLI commands. For basic auth, use `-u "user:pass"`.

## Step 2 — Index mappings (dynamic vs strict)

Mappings define field types and analyzers. They are IMMUTABLE after
creation.

| Setting | Behavior | Use case |
|---|---|---|
| `"dynamic": true` (default) | Auto-guesses field types | Dev, exploration |
| `"dynamic": "runtime"` | New fields become runtime fields | Flexible, slower queries |
| `"dynamic": "strict"` | Rejects unmapped fields | Production |
| `"dynamic": false` | New fields ignored (not indexed) | Known schema |

**Critical field type decisions:**

| Decision | Wrong choice | Right choice | Why |
|---|---|---|---|
| ID fields | `text` | `keyword` | Text is analyzed; keyword is exact-match |
| Names for sorting | `text` only | `text` + `.keyword` sub-field | Sort/aggregation needs keyword |
| Nested objects | `object` | `nested` | Object flattens keys; nested preserves relationships |
| Decimal values | `float` | `double` | Float loses precision for financial data |

## Step 3 — Shard sizing (primary + replica)

Shard count is set at index creation and CANNOT be changed without
reindex (split API for more shards, shrink for fewer).

```json
PUT /logs-app-v1
{
  "settings": { "index": { "number_of_shards": 5, "number_of_replicas": 1 } },
  "mappings": { "dynamic": "strict", "properties": { "message": { "type": "text" }, "level": { "type": "keyword" } } }
}
```

Replica count CAN be changed at runtime:

```json
PUT /logs-app-v1/_settings
{ "index": { "number_of_replicas": 2 } }
```

## Step 4 — ILM policies (hot/warm/cold tiering)

ILM automates index lifecycle: rollover, force merge, migrate to
warm/cold nodes, and delete.

**Create ILM policy and attach via rollover alias:**

```json
PUT _ilm/policy/logs-ilm-policy
{
  "policy": {
    "default_state": "hot",
    "states": [
      { "name": "hot", "actions": [], "transitions": [{ "state_name": "warm", "conditions": { "min_index_age": "7d" } }] },
      { "name": "warm", "actions": [{ "force_merge": { "max_num_segments": 1 } }], "transitions": [{ "state_name": "delete", "conditions": { "min_index_age": "90d" } }] },
      { "name": "delete", "actions": [{ "delete": {} }], "transitions": [] }
    ],
    "ism_template": { "index_patterns": ["logs-app-*"], "priority": 100 }
  }
}
```

```json
PUT /logs-app-000001
{
  "settings": { "index": { "number_of_shards": 5, "number_of_replicas": 1, "plugins.index_state_management.rollover_alias": "logs-app-write" } },
  "aliases": { "logs-app-write": { "is_write_index": true } }
}
```

**Critical:** the rollover alias must have `"is_write_index": true`.
Without it, the rollover action fails.

## Step 5 — Alias management for zero-downtime reindexing

Aliases enable zero-downtime reindexing: create a new index with
updated mappings, reindex, then swap the alias atomically.

**Atomic alias swap (zero downtime):**

```json
POST _aliases
{
  "actions": [
    { "remove": { "index": "products-v1", "alias": "products" } },
    { "add": { "index": "products-v2", "alias": "products" } }
  ]
}
```

**Background reindex:**

```json
POST _reindex?wait_for_completion=false
{ "source": { "index": "products-v1" }, "dest": { "index": "products-v2" } }
```

The alias swap is atomic — clients reading from the alias experience no
downtime. See `references/templates-and-data-streams.md` for the full
workflow.

## Step 6 — Index templates and component templates

Index templates apply settings and mappings to new indices matching a
pattern. Component templates are reusable building blocks.

```json
PUT _component_template/common-mappings
{ "template": { "mappings": { "properties": { "@timestamp": { "type": "date" }, "env": { "type": "keyword" } } } } }

PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": { "settings": { "number_of_shards": 3, "number_of_replicas": 1 } },
  "composed_of": ["common-mappings"],
  "priority": 200,
  "version": 1
}
```

**Critical:** index templates apply ONLY to new indices. Existing
indices are not updated when the template changes. Always create
templates BEFORE creating matching indices.

## Step 7 — Rollover aliases and data streams

Data streams are designed for time-series, append-only data. Each data
stream is backed by hidden indices managed by the lifecycle.

```json
PUT _index_template/logs-ds-template
{ "index_patterns": ["logs-ds*"], "data_stream": {}, "template": { "settings": { "number_of_shards": 3, "number_of_replicas": 1 } }, "priority": 500 }

PUT _data_stream/logs-ds

POST logs-ds/_doc
{ "@timestamp": "2026-08-05T10:00:00.000Z", "message": "App started", "level": "INFO" }
```

| Feature | Rollover alias | Data stream |
|---|---|---|
| Write pattern | Append to alias | Append-only (no IDs) |
| Lifecycle | Manual ILM rollover | Automatic backing index rollover |
| Best for | Semi-structured (products, events) | Pure time-series (logs, metrics) |

## Step 8 — k-NN vector search configuration

k-NN (k-nearest neighbors) enables vector similarity search for
semantic search and ML use cases.

```json
PUT /vector-search-v1
{
  "settings": { "index": { "knn": true, "knn.algo_param.ef_search": 512, "number_of_shards": 3, "number_of_replicas": 1 } },
  "mappings": { "properties": {
    "embedding": { "type": "knn_vector", "dimension": 768,
      "method": { "name": "hnsw", "space_type": "cosinesimil", "engine": "nmslib",
        "parameters": { "ef_construction": 512, "m": 48 } } } } }
}
```

| Method | Space type | Engine | Best for |
|---|---|---|---|
| `hnsw` | `l2`, `cosinesimil`, `innerproduct` | `nmslib` | General-purpose, high-recall |
| `hnsw` | `l2`, `cosinesimil`, `innerproduct` | `faiss` | Filtered search, better recall |
| `ivf` | `l2`, `cosinesimil` | `faiss` | Very large datasets |

**Critical:** `"index.knn": true` and method/space_type are IMMUTABLE —
set at creation. Dimension must match your embedding model output.

## Step 9 — Search pipeline configuration

Search pipelines apply processing steps to search results.

```json
PUT _search/pipeline/product-search-pipeline
{
  "description": "Normalize scores and filter inactive",
  "request_processors": [{ "filter_query": { "query": { "term": { "is_active": true } } } }],
  "response_processors": [{ "normalize_score": { "technique": "min_max" } }]
}
```

Use via `GET products/_search?search_pipeline=product-search-pipeline`
or set as index default via
`"index.search.default_search_pipeline"`.

## Step 10 — Snapshot management (S3)

**Automated snapshots:** AWS takes daily snapshots to
`cs-automated-enclosure-[domain-id]`. No operator action needed.

**Manual snapshot repository:**

```json
PUT _snapshot/my-manual-snapshots
{ "type": "s3", "settings": { "bucket": "my-opensearch-snapshots", "region": "us-east-1", "base_path": "snapshots" } }

PUT _snapshot/my-manual-snapshots/snapshot-2026-08-05
{ "indices": "products-v1,logs-app-*", "ignore_unavailable": true }
```

The IAM role for manual snapshots needs `s3:PutObject`, `s3:GetObject`,
`s3:DeleteObject`, and `s3:ListBucket` on the snapshot bucket.

## Step 11 — Force merge for read-only indices

Force merge reduces segment count to speed up searches and reduce
resource usage. Only do this on READ-ONLY indices.

```json
PUT /logs-app-2026.07.01/_settings
{ "index": { "blocks": { "write": true } } }

POST /logs-app-2026.07.01/_forcemerge?max_num_segments=1
```

**Critical:** force merge on a write-active index creates a single
large segment that cannot be re-merged as new documents arrive. Always
block writes first.

## Step 12 — Recent features
> Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
> Read it only when this section applies.


## NEVER do these things

1. **NEVER use the default 5 primary shards without checking data
   volume.** Shard count must target 10-50 GB per shard. Over-sharding
   is the #1 OpenSearch performance killer.

2. **NEVER assume mappings can be changed after creation.** Field
   types are IMMUTABLE. Changing a field type requires creating a new
   index and reindexing all data. Use `"dynamic": "strict"` in
   production.

3. **NEVER configure ILM without a rollover alias having
   `"is_write_index": true`.** The rollover action fails without it.
   Verify the alias is set as the write index before attaching ILM.

4. **NEVER enable k-NN on an existing index.** `"index.knn": true`,
   the method, and space_type are set at creation and CANNOT be
   changed. k-NN must be configured in the index creation request.

5. **NEVER force merge a write-active index.** Force merge creates a
   single large segment that cannot be re-merged. Always block writes
   before force merging.

6. **NEVER create an index without checking cluster health and disk
   space.** A red cluster or >85% disk usage causes shard allocation
   failures. Verify green/yellow health and <50% disk usage.

7. **NEVER assume index templates apply retroactively.** Templates
   only apply to NEWLY created indices. Create templates BEFORE creating
   matching indices.

8. **NEVER use `object` type for arrays-of-objects where relationship
   matters.** The `object` type flattens nested keys, breaking cross-
   object queries. Use `"type": "nested"`.

9. **NEVER set replica count to 0 in production.** Zero replicas means
   no HA and no read scaling. The cluster goes yellow. Use at least 1
   replica for production indices.

10. **NEVER forget snapshot repository registration for manual
    snapshots.** Automated snapshots use the AWS-managed repository,
    but manual snapshots require a separately registered S3 repository.

## Output format

```text
OPENSEARCH_INDEX: <index-name> (<domain-endpoint>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Domain endpoint: <endpoint>
  [✓|✗] Cluster health: green | yellow | red
  [✓|✗] Index name: <index-name>
  [✓|✗] Dynamic mapping: strict | true | runtime | false
  [✓|✗] Primary shards: <count> (target: <est-size-per-shard> GB/shard)
  [✓|✗] Replica shards: <count> (read throughput: <n>x | HA: yes|no)
  [✓|✗] ILM policy: <policy-name> (rollover: <max_size> | <max_age>)
  [✓|✗] Rollover alias: <alias> (is_write_index: true)
  [✓|✗] Index template: <template-name> (pattern: <pattern>)
  [✓|✗] Data stream: enabled | disabled
  [✓|✗] k-NN vector search: enabled (dimension: <d>, method: <m>, space: <s>) | disabled
  [✓|✗] Search pipeline: <pipeline-name> | none
  [✓|✗] Snapshot repository: <repo-name> | automated-only
  [✓|✗] Force merge: read-only index merged | not applicable
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  curl -s "<endpoint>/<index-name>" -u "user:pass"
  curl -s "<endpoint>/_cat/indices/<index-name>?v" -u "user:pass"
  curl -s "<endpoint>/_cluster/health/<index-name>?pretty" -u "user:pass"
```

### Worked example — production logs index with ILM

```text
OPENSEARCH_INDEX: logs-app-000001 (search-mydomain-abc123.us-east-1.es.amazonaws.com)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain endpoint: search-mydomain-abc123.us-east-1.es.amazonaws.com
  [✓] Cluster health: green
  [✓] Index name: logs-app-000001
  [✓] Dynamic mapping: strict
  [✓] Primary shards: 5 (target: 30 GB/shard, estimated 150 GB total)
  [✓] Replica shards: 1 (read throughput: 2x, HA: yes)
  [✓] ILM policy: logs-ilm-policy (rollover: 50gb | 1d)
  [✓] Rollover alias: logs-app-write (is_write_index: true)
  [✓] Index template: logs-template (pattern: logs-app-*)
  [✓] Data stream: disabled (using rollover alias)
  [✓] k-NN vector search: disabled
  [✓] Search pipeline: none
  [✓] Snapshot repository: my-manual-snapshots (S3: my-opensearch-snapshots)
  [✓] Force merge: not applicable (active write index)
  [✓] Tags: Environment=production, Application=app-logs
VERIFICATION_COMMANDS:
  curl -s "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/logs-app-000001" -u "user:pass"
  curl -s "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/_cat/indices/logs-app-000001?v" -u "user:pass"
  curl -s "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/_cluster/health/logs-app-000001?pretty" -u "user:pass"
```

## Error handling
> Moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.
> Read it only when this section applies.


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — configuration dependency graph, recent features, expert deep dives
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives for index operations
- [references/shard-sizing-and-ilm.md](references/shard-sizing-and-ilm.md) — shard sizing, replica count, ILM rollover heuristics
- [references/templates-and-data-streams.md](references/templates-and-data-streams.md) — template and data stream detail
## Domain

AWS CloudOps / Amazon OpenSearch Service Index Management & Analytics
Search Infrastructure.

## AWS documentation

- **OpenSearch Service Guide** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html
- **Index APIs** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/indexing.html
- **Index State Management** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html
- **Index Templates** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/index-templates.html
- **Data Streams** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/data-streams.html
- **k-NN Vector Search** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/knn.html
- **Search Pipelines** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/search-pipelines.html
- **Snapshot Management** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html
- **Sizing guide** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html
