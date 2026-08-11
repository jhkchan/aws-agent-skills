---
name: opensearch-index-deployer
description: >-
  Provisions Amazon OpenSearch Service indices with production defaults:
  index creation with explicit mappings (dynamic vs strict),
  shard count (primary + replica) sizing, index lifecycle management
  (ILM) policies with hot/warm/cold tiering, force merge for read-only
  indices, snapshot management (automated + manual to S3), alias
  management for zero-downtime reindexing, index templates and
  component templates, rollover aliases, data streams for time-series
  workloads, search pipeline configuration (normalizers, processors),
  k-NN vector search index configuration, and field type mapping
  (keyword vs text, nested vs object). Emits a READY_TO_DEPLOY
  checklist with verification commands. Use when creating an
  OpenSearch index, configuring shard count, setting up ILM policies,
  managing aliases for zero-downtime reindex, creating index
  templates, deploying k-NN vector search, or configuring data
  streams. Triggers: create opensearch index, opensearch shard
  sizing, opensearch ilm policy, opensearch alias reindex, opensearch
  index template, opensearch knn vector, opensearch data stream,
  opensearch snapshot repository.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with opensearch
  access (sigv4 or basic auth), or the OpenSearch Dev Tools console.
  Works with Terraform opensearch_index / opensearch_domain resources
  and CloudFormation AWS::OpenSearchService::Domain templates.
keywords:
  - aws
  - opensearch
  - elasticsearch
  - index management
  - cloudops
  - deploy
  - provisioning
  - shard sizing
  - ilm
  - index lifecycle
  - hot warm cold
  - force merge
  - snapshot
  - alias reindex
  - index template
  - component template
  - rollover
  - data stream
  - knn vector
  - search pipeline
tags:
  - aws
  - opensearch
  - index-management
  - cloudops
  - deploy
  - analytics
  - provisioning
  - ilm
  - shard-sizing
  - alias-reindex
  - knn-vector
  - data-stream
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - opensearch
    - index-management
    - cloudops
    - deploy
    - analytics
    - provisioning
    - ilm
    - shard-sizing
    - alias-reindex
    - knn-vector
    - data-stream
  dependencies:
    - aws-orchestrator
  keywords:
    - create opensearch index
    - opensearch shard sizing
    - opensearch ilm policy
    - opensearch alias reindex
    - opensearch index template
    - opensearch knn vector
    - opensearch data stream
    - opensearch snapshot repository
  when_to_use: >-
    Invoke when the user wants to create an OpenSearch Service index
    with mappings and shard sizing, configure ILM policies for
    hot/warm/cold storage tiering, set up aliases for zero-downtime
    reindexing, deploy index templates or component templates,
    configure data streams for time-series data, deploy k-NN vector
    search indices, configure search pipelines, or manage snapshots
    to S3. Do NOT invoke for OpenSearch domain-level provisioning
    (use opensearch-domain-deployer), OpenSearch Serverless (use
    opensearch-serverless-deployer), or OpenSearch domain auditing
    (use opensearch-domain-auditor).
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

OpenSearch index configurations are NOT independent. The ILM policy
requires a rollover alias to exist. Index templates must be created
before indices that match the pattern. k-NN indices require specific
settings at creation time (method, space type). Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Index with mappings | Domain reachable; cluster health yellow+ | mapping is IMMUTABLE after creation (field types cannot change without reindex) | searchable data |
| Replica count | Enough data nodes to host primaries + replicas | 0 replicas = no HA; cluster yellow | read throughput + HA |
| ILM policy | Policy created (PUT _ilm/policy); rollover alias attached | rollover requires `"is_write_index": true` on the alias | automatic shard rollover + tier transition |
| Rollover alias | Index created with `"aliases": {"<alias>": {"is_write_index": true}}` | alias without is_write_index — rollover fails | write endpoint abstraction |
| Index template | Template created BEFORE matching indices | existing indices are NOT updated by template changes | consistent schema for new indices |
| Component template | Component template referenced by index template | order determines merge priority when multiple components match | reusable mapping/settings blocks |
| Data stream | Data stream template (backing index template + `data_stream` object) created; `"index_mode": "standard"` | cannot PUT mapping on a data stream directly | append-only time-series ingestion |
| k-NN index | `"index.knn": true` at creation; knn_vector field type; method + space_type | k-NN settings are IMMUTABLE; cannot enable knn after creation | approximate nearest neighbor search |
| Search pipeline | Pipeline created (PUT _search/pipeline); referenced in query or index settings | pipeline is optional per-query; default pipeline set via index setting | query-time normalization, filtering |
| Snapshot repository | S3 bucket registered (PUT _snapshot/repo); domain IAM role has s3 access | repository registration is per-cluster; automated snapshots use a different repo | manual + automated backups |
| Force merge | Index is READ-ONLY (writes blocked first) | force merge on a write-active index creates a single large segment that cannot be merged again | reduced segment count, faster reads |

**The mapping-is-immutable row is the one a baseline model misses.**
Field types, analyzer assignments, and dynamic settings are set at index
creation and CANNOT be changed later without a full reindex. The
rollover-alias-before-ILM dependency is the second most common gotcha.
The procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- ILM rollover requires the rollover alias to have `"is_write_index":
  true`. Without it, the rollover action fails with
  `illegal_argument_exception`.
- Index templates only apply to NEWLY created indices. Changing a
  template does NOT update existing indices.
- k-NN `"index.knn": true` must be set at creation. You cannot enable
  k-NN on an existing index.
- Force merge to `max_num_segments=1` should only be done on read-only
  indices. Merging on a write-active index creates a segment that
  cannot be re-merged as new documents arrive.
- Data streams require backing indices managed by the data stream
  lifecycle; you cannot directly PUT a mapping on the data stream.

## Expert heuristic: shard sizing (10-50 GB per shard)

A baseline model says "use the default 5 shards." The correct heuristic
sizes shards to the 10-50 GB range, adjusting primary count to data
volume.

```text
Estimated index size (primary data, no replicas):
  ├── < 10 GB  → 1 primary shard (1 shard at <10 GB is efficient)
  ├── 10-50 GB → 1 primary shard (1 shard at 10-50 GB is the sweet spot)
  ├── 50-100 GB → 2 primary shards (25-50 GB each)
  ├── 100-250 GB → 5 primary shards (20-50 GB each)
  ├── 250-500 GB → 10 primary shards (25-50 GB each)
  ├── 500 GB-1 TB → 20 primary shards (25-50 GB each)
  └── 1 TB+ → use data streams + ILM rollover (avoid single huge index)

Replica count decision:
  ├── HA requirement → minimum 1 replica (cluster survives 1 node loss)
  ├── Read QPS is high → 2-3 replicas (each replica serves search)
  └── Cost-sensitive dev/staging → 0 replicas (cluster yellow, no HA)
```

**Key implication:** over-sharding is the #1 OpenSearch performance
killer. Too many small shards create overhead in cluster state, merge
scheduling, and memory (each shard has its own data structures). Target
10-50 GB per shard. When in doubt, fewer larger shards is better than
many small shards.

## Expert heuristic: replica count for read throughput

Replicas serve two purposes: high availability AND read scaling. Each
replica shard can independently serve search queries.

```text
Write QPS: limited by primary shard count (writes go to primary first)
Read QPS: limited by primary + replica shard count (search hits all shards)

Read scaling with replicas:
  1 primary + 0 replicas = 1x read capacity (no HA)
  1 primary + 1 replica  = 2x read capacity (survives 1 node loss)
  1 primary + 2 replicas = 3x read capacity (survives 2 node loss)
  1 primary + 3 replicas = 4x read capacity

Cost trade-off:
  Each replica = full copy of the data → doubles, triples, quadruples
  storage cost. Use for read-heavy workloads where search latency
  matters more than storage cost.
```

**Key implication:** for read-heavy workloads (e.g., product search,
log dashboards), adding replicas is cheaper than scaling instances. For
write-heavy workloads (e.g., ingestion pipelines), invest in more
primary shards or larger instances instead.

## Expert heuristic: ILM rollover for storage tiering

ILM automates the transition of indices through hot → warm → cold →
delete phases, reducing cost for time-series data.

```text
ILM lifecycle phases:
  HOT phase:   active write index, SSD storage, high-compute nodes
    → rollover when: index reaches max_age (e.g., 1d) OR max_size (e.g., 50gb)
    → action: create new index, point alias to new index

  WARM phase:  read-only, SSD or HDD, fewer compute resources
    → transition when: index is rollover'd (age-based, e.g., 7d after rollover)
    → action: force merge, shrink, or move to warm nodes

  COLD phase:  rarely searched, minimal compute, cheapest storage
    → transition when: age-based (e.g., 30d after rollover)
    → action: move to cold nodes (searchable cold storage)

  DELETE phase: permanently remove
    → delete when: age-based (e.g., 90d after rollover)
    → action: delete index
```

**Key implication:** without ILM, indices accumulate on hot nodes
forever, driving cost. ILM rollover + tiering can cut OpenSearch costs
by 50-70% for time-series workloads by moving old data to cheaper
storage tiers.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| OpenSearch domain endpoint reachable | Index APIs require domain connectivity | `curl -s <endpoint>/_cluster/health` |
| Auth credentials (sigv4 or basic auth) | Domain requires authenticated access | Verify IAM policy or master user credentials |
| Cluster health yellow or green | Red cluster may reject index creation | `GET _cluster/health` — `status: "yellow"` or `"green"` |
| Estimated data volume known | Determines primary shard count (10-50 GB target) | Estimate from source data size |
| Node count supports replica placement | Replicas need separate nodes from primaries | `GET _cat/nodes` — enough data nodes for primary + replica |
| Disk space available (50%+ free) | OpenSearch recommends 50% free disk for shard allocation | `GET _cat/allocation?v` — `disk.percent` < 50 |
| Snapshot S3 bucket exists (if snapshots needed) | Manual snapshot repository needs an S3 bucket | `aws s3 ls s3://<bucket>` |
| k-NN plugin enabled (if k-NN index) | k-NN requires the plugin installed on the domain | `GET _plugins/_knn/stats` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Domain connectivity and auth

Amazon OpenSearch Service supports two auth modes: IAM sigv4 (recommended)
and master-user basic auth (fine-grained access control).

**IAM sigv4 (recommended for AWS-native workflows):**

```bash
# Use aws-opensearch curl wrapper or signed requests
# The simplest: use the opensearch-py client with AWS auth
pip install opensearch-py requests-aws4auth

python3 -c "
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

host = 'https://search-mydomain-abc123.us-east-1.es.amazonaws.com'
region = 'us-east-1'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                   region, 'es', session_token=credentials.token)

client = OpenSearch(
    hosts=[{'host': host.replace('https://',''), 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    connection_class=RequestsHttpConnection
)
print(client.info())
"
```

**Basic auth (fine-grained access control):**

```bash
curl -XGET "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/_cluster/health" \
  -u "master-user:password"
```

**Verify cluster health before index creation:**

```bash
curl -s "https://<endpoint>/_cluster/health?pretty" -u "user:pass"
# Expected: "status": "green" or "yellow"
# If "red": resolve cluster health before creating indices
```

## Step 2 — Index mappings (dynamic vs strict)

Mappings define field types and analyzers. They are IMMUTABLE after
creation (field types cannot change without reindex).

| Setting | Behavior | Use case |
|---|---|---|
| `"dynamic": true` (default) | Auto-guesses field types for new fields | Dev, exploration, evolving schemas |
| `"dynamic": "runtime"` | New fields become runtime fields (not indexed) | Flexible but slower queries |
| `"dynamic": "strict"` | Rejects documents with unmapped fields | Production — forces explicit mapping |
| `"dynamic": false` | New fields are ignored (stored but not indexed) | Known schema, ignore unknown fields |

**Production mapping with strict dynamic and explicit field types:**

```json
PUT /products-v1
{
  "settings": {
    "index": {
      "number_of_shards": 3,
      "number_of_replicas": 1
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "product_id": { "type": "keyword" },
      "name": { "type": "text", "analyzer": "standard" },
      "name_keyword": { "type": "keyword" },
      "price": { "type": "double" },
      "category": { "type": "keyword" },
      "tags": { "type": "keyword" },
      "description": { "type": "text", "analyzer": "english" },
      "metadata": {
        "type": "nested",
        "properties": {
          "key": { "type": "keyword" },
          "value": { "type": "keyword" }
        }
      },
      "created_at": { "type": "date" },
      "is_active": { "type": "boolean" }
    }
  }
}
```

**Critical field type decisions:**

| Decision | Wrong choice | Right choice | Why |
|---|---|---|---|
| ID fields | `text` | `keyword` | Text is analyzed (tokenized); keyword is exact-match |
| Names for sorting | `text` only | `text` + `.keyword` sub-field | Sort/aggregation needs keyword; search needs text |
| Nested objects | `object` (flattened) | `nested` | Object flattens keys; nested preserves array-of-object relationships |
| Decimal values | `float` | `double` | Float loses precision for financial data |
| Tags/categories | `text` | `keyword` | Aggregations and term filters need keyword |

## Step 3 — Shard sizing (primary + replica)

Shard count is set at index creation and CANNOT be changed without
reindex (use the split API for a larger shard count, shrink API for
smaller).

**Primary shard count (target 10-50 GB per shard):**

```json
PUT /logs-app-v1
{
  "settings": {
    "index": {
      "number_of_shards": 5,
      "number_of_replicas": 1
    }
  }
}
```

**Adjusting replica count at runtime (this CAN be changed without reindex):**

```json
PUT /logs-app-v1/_settings
{
  "index": {
    "number_of_replicas": 2
  }
}
```

**Common mistake:** setting `number_of_shards` too high for a small
index. A 5 GB index with 5 shards = 1 GB per shard (below the 10 GB
minimum). Use 1 shard instead.

## Step 4 — ILM policies (hot/warm/cold tiering)

ILM automates index lifecycle: rollover, force merge, shrink, migrate
to warm/cold nodes, and delete.

**Create ILM policy:**

```json
PUT _ilm/policy/logs-ilm-policy
{
  "policy": {
    "description": "Logs lifecycle: rollover at 50GB/1day, warm after 7d, delete after 90d",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": {
              "min_index_age": "7d"
            }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          {
            "force_merge": { "max_num_segments": 1 }
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "90d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          { "delete": {} }
        ],
        "transitions": []
      }
    ],
    "ism_template": {
      "index_patterns": ["logs-app-*"],
      "priority": 100
    }
  }
}
```

**Attach ILM to an index via rollover alias:**

```json
PUT /logs-app-000001
{
  "settings": {
    "index": {
      "number_of_shards": 5,
      "number_of_replicas": 1,
      "plugins.index_state_management.rollover_alias": "logs-app-write"
    }
  },
  "aliases": {
    "logs-app-write": {
      "is_write_index": true
    }
  }
}
```

**Trigger rollover:**

```json
POST logs-app-write/_rollover
{
  "conditions": {
    "max_size": "50gb",
    "max_age": "1d",
    "max_docs": 100000000
  }
}
```

**Critical:** the rollover alias must have `"is_write_index": true` on
the initial index. Without it, the rollover action fails.

## Step 5 — Alias management for zero-downtime reindexing

Aliases enable zero-downtime reindexing: create a new index with updated
mappings, reindex data, then swap the alias.

**Step 1 — Create alias pointing to current index:**

```json
POST _aliases
{
  "actions": [
    {
      "add": {
        "index": "products-v1",
        "alias": "products"
      }
    }
  ]
}
```

**Step 2 — Create new index with updated mappings:**

```json
PUT /products-v2
{
  "settings": {
    "index": {
      "number_of_shards": 5,
      "number_of_replicas": 1
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "product_id": { "type": "keyword" },
      "name": { "type": "text", "analyzer": "standard" },
      "name_keyword": { "type": "keyword" },
      "price": { "type": "double" },
      "category": { "type": "keyword" },
      "tags": { "type": "keyword" },
      "description": { "type": "text", "analyzer": "english" },
      "sku": { "type": "keyword" },
      "metadata": {
        "type": "nested",
        "properties": {
          "key": { "type": "keyword" },
          "value": { "type": "keyword" }
        }
      },
      "created_at": { "type": "date" },
      "is_active": { "type": "boolean" }
    }
  }
}
```

**Step 3 — Reindex from old to new (in the background):**

```json
POST _reindex?wait_for_completion=false
{
  "source": { "index": "products-v1" },
  "dest": { "index": "products-v2" }
}
```

**Step 4 — Swap alias atomically (zero downtime):**

```json
POST _aliases
{
  "actions": [
    {
      "remove": {
        "index": "products-v1",
        "alias": "products"
      }
    },
    {
      "add": {
        "index": "products-v2",
        "alias": "products"
      }
    }
  ]
}
```

**Critical:** the alias swap is atomic. Clients reading from the
`products` alias experience no downtime — they are redirected from
v1 to v2 instantly.

## Step 6 — Index templates and component templates

Index templates apply settings and mappings to new indices that match
a pattern. Component templates are reusable building blocks.

**Create component template (reusable mappings block):**

```json
PUT _component_template/common-mappings
{
  "template": {
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "source": { "type": "keyword" },
        "env": { "type": "keyword" }
      }
    }
  }
}
```

**Create component template (reusable settings block):**

```json
PUT _component_template/common-settings
{
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "index.refresh_interval": "1s"
    }
  }
}
```

**Create index template referencing component templates:**

```json
PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "index.plugins.index_state_management.policy_id": "logs-ilm-policy",
      "index.plugins.index_state_management.rollover_alias": "logs-write"
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "message": { "type": "text" },
        "level": { "type": "keyword" },
        "service": { "type": "keyword" },
        "duration_ms": { "type": "integer" }
      }
    }
  },
  "composed_of": ["common-mappings", "common-settings"],
  "priority": 200,
  "version": 1
}
```

**Critical:** index templates apply ONLY to new indices. Existing
indices are not updated when the template changes. Always create
templates BEFORE creating indices that match the pattern.

## Step 7 — Rollover aliases and data streams

Data streams are designed for time-series, append-only data. Each data
stream is backed by a sequence of hidden indices.

**Create a data stream:**

```json
PUT _data_stream/logs-datastream
```

**Ingest into a data stream (append-only — no document ID):**

```json
POST logs-datastream/_doc
{
  "@timestamp": "2026-08-05T10:00:00.000Z",
  "message": "Application started",
  "level": "INFO",
  "service": "api-gateway"
}
```

**Data stream backing index template:**

```json
PUT _index_template/logs-ds-template
{
  "index_patterns": ["logs-datastream*"],
  "data_stream": {},
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1
    }
  },
  "priority": 500
}
```

**Key difference: rollover alias vs data stream:**

| Feature | Rollover alias | Data stream |
|---|---|---|
| Write pattern | Append to alias | Append-only (no IDs) |
| Updates/deletes | Supported on backing indices | Supported (by backing index) |
| Lifecycle | Manual ILM rollover | Automatic backing index rollover |
| Best for | Semi-structured indices (products, events) | Pure time-series (logs, metrics) |

## Step 8 — k-NN vector search configuration

k-NN (k-nearest neighbors) enables vector similarity search for
semantic search, recommendation, and ML use cases.

**Create k-NN index (must be set at creation time):**

```json
PUT /vector-search-v1
{
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 512,
      "number_of_shards": 3,
      "number_of_replicas": 1
    }
  },
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "title": { "type": "text" },
      "embedding": {
        "type": "knn_vector",
        "dimension": 768,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 512,
            "m": 48
          }
        }
      }
    }
  }
}
```

**k-NN method selection:**

| Method | Space type | Engine | Best for |
|---|---|---|---|
| `hnsw` | `l2`, `cosinesimil`, `innerproduct` | `nmslib` (default) | General-purpose, high-recall |
| `hnsw` | `l2`, `cosinesimil`, `innerproduct` | `faiss` | Filtered search, better recall with filters |
| `ivf` | `l2`, `cosinesimil` | `faiss` | Very large datasets, lower latency |

**Critical:** `"index.knn": true` and the method/space_type are
IMMUTABLE — set at creation. You CANNOT enable k-NN on an existing
index. Dimension must match your embedding model output.

## Step 9 — Search pipeline configuration

Search pipelines apply processing steps to search results (e.g.,
normalization, result filtering, score combination).

**Create search pipeline:**

```json
PUT _search/pipeline/product-search-pipeline
{
  "description": "Normalize scores and filter low-relevance results",
  "request_processors": [
    {
      "filter_query": {
        "query": {
          "term": { "is_active": true }
        }
      }
    }
  ],
  "response_processors": [
    {
      "normalize_score": {
        "technique": "min_max"
      }
    },
    {
      "rename_field": {
        "field": "_score",
        "target_field": "relevance_score"
      }
    }
  ]
}
```

**Use pipeline in a search query:**

```json
GET products/_search?search_pipeline=product-search-pipeline
{
  "query": {
    "match": {
      "name": "wireless headphones"
    }
  }
}
```

**Set default pipeline on an index:**

```json
PUT /products-v1/_settings
{
  "index": {
    "search.default_search_pipeline": "product-search-pipeline"
  }
}
```

## Step 10 — Snapshot management (S3)

Snapshots back up indices to S3. Two types: automated (AWS-managed) and
manual (operator-managed).

**Automated snapshots:** AWS OpenSearch Service automatically takes
daily snapshots to a pre-configured repository
`cs-automated-enclosure-[your-domain-id]`. No operator action needed.

**Manual snapshot repository registration:**

```json
PUT _snapshot/my-manual-snapshots
{
  "type": "s3",
  "settings": {
    "bucket": "my-opensearch-snapshots",
    "region": "us-east-1",
    "base_path": "snapshots",
    "compress": true
  }
}
```

**IAM role for manual snapshots** (trust policy for OpenSearch Service):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "es.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Take a manual snapshot:**

```json
PUT _snapshot/my-manual-snapshots/snapshot-2026-08-05
{
  "indices": "products-v1,logs-app-*",
  "ignore_unavailable": true,
  "include_global_state": false
}
```

**Restore from snapshot:**

```json
POST _snapshot/my-manual-snapshots/snapshot-2026-08-05/_restore
{
  "indices": "products-v1",
  "rename_pattern": "products-v1",
  "rename_replacement": "products-restored"
}
```

## Step 11 — Force merge for read-only indices

Force merge reduces segment count to speed up searches and reduce
resource usage on read-only indices (e.g., old logs in warm tier).

**Block writes first (critical):**

```json
PUT /logs-app-2026.07.01/_settings
{
  "index": {
    "blocks": {
      "write": true
    }
  }
}
```

**Force merge to a single segment:**

```json
POST /logs-app-2026.07.01/_forcemerge?max_num_segments=1
```

**Critical:** force merge should ONLY be done on read-only indices.
Force-merging a write-active index creates a single large segment that
cannot be re-merged as new documents arrive, leading to a
`Lucene merge does not make progress` error. Always block writes first.

## Step 12 — Recent features

**Recent AWS OpenSearch features (2023-2026):**

- **k-NN FAISS engine with filtering (2023-2024):** The FAISS engine
  for k-NN search provides better recall when combined with pre/post
  filters. Supports `l2`, `cosinesimil`, and `innerproduct` space
  types. Recommended for filtered vector search workloads.

- **Searchable cold storage (2023-2024):** Ultra-low-cost cold tier
  for rarely-searched data. Queries against cold indices are slower
  but cost is dramatically reduced. Integrates with ILM cold phase.

- **Data streams auto-roll and lifecycle (2023-2024):** Data streams
  now support automatic backing index rollover and ILM integration,
  eliminating the need for manual rollover alias management for pure
  time-series workloads.

- **Search pipelines GA (2023-2024):** Search pipelines with request
  and response processors are generally available, enabling query-time
  normalization, filtering, and result post-processing without client-
  side code.

- **Vector search performance improvements (2024-2025):** HNSW
  algorithm optimizations with `ef_construction` and `ef_search`
  tuning provide up to 3x latency improvement for large vector indices.

- **Semantic search with ML models (2024-2025):** OpenSearch ML
  Commons integration enables text-to-embedding transformation at
  ingestion and query time, supporting neural search pipelines without
  external model serving.

- **Index template priority resolution (2024-2025):** Enhanced
  template matching with explicit `priority` and `version` fields for
  predictable composition order when multiple templates match.

## NEVER do these things

1. **NEVER use the default 5 primary shards without checking data
   volume.** Shard count must target 10-50 GB per shard. Over-sharding
   is the #1 OpenSearch performance killer. Calculate expected index
   size and choose shard count accordingly.

2. **NEVER assume mappings can be changed after creation.** Field
   types are IMMUTABLE. Changing a field type requires creating a new
   index and reindexing all data. Always design mappings carefully at
   creation time, and use `"dynamic": "strict"` in production.

3. **NEVER configure ILM without a rollover alias having
   `"is_write_index": true`.** The rollover action fails without it.
   Always verify the alias is set as the write index before attaching
   the ILM policy.

4. **NEVER enable k-NN on an existing index.** `"index.knn": true`,
   the method, and space_type are set at creation and CANNOT be
   changed. k-NN must be configured in the index creation request.

5. **NEVER force merge a write-active index.** Force merge creates a
   single large segment that cannot be re-merged. Always block writes
   (`"blocks": {"write": true}`) before force merging.

6. **NEVER create an index without checking cluster health and disk
   space.** A red cluster or >85% disk usage causes shard allocation
   failures. Verify `GET _cluster/health` is green/yellow and
   `GET _cat/allocation` shows <50% disk usage.

7. **NEVER assume index templates apply retroactively.** Templates
   only apply to NEWLY created indices. Existing indices are not
   updated. Create templates BEFORE creating matching indices.

8. **NEVER use `object` type for arrays-of-objects where relationship
   matters.** The `object` type flattens nested keys, breaking cross-
   object queries. Use `"type": "nested"` when you need to query
   within individual array elements.

9. **NEVER set replica count to 0 in production.** Zero replicas means
   no high availability and no read scaling. The cluster goes yellow.
   Always use at least 1 replica for production indices.

10. **NEVER forget snapshot repository registration for manual
    snapshots.** Automated snapshots use the AWS-managed repository,
    but manual snapshots require a separately registered S3 repository
    with an IAM role that has s3 access.

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
  [✓] Index template: logs-template (pattern: logs-*)
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

### Index creation fails with "mapper_parsing_exception"
- The mapping JSON has a syntax error or invalid field type. Validate
  the JSON and check field type names. Use `GET /_mapping` on a
  similar index as a reference.

### Rollover fails with "illegal_argument_exception"
- The rollover alias does not have `"is_write_index": true`. Re-create
  the alias with the `is_write_index` flag on the write index.

### k-NN search returns "index knn is disabled"
- The index was created without `"index.knn": true`. k-NN must be set
  at creation time. Create a new index with k-NN enabled and reindex.

### Force merge hangs or fails
- The index is still receiving writes. Block writes first
  (`"blocks": {"write": true}`), then force merge. Never force merge
  a write-active index.

### Cluster goes red after creating a large index
- Not enough data nodes to allocate shards, or disk usage exceeded
  the flood-stage watermark. Add nodes, increase disk, or reduce shard
  count. Check `GET _cat/allocation?v` for disk usage.

### Snapshot fails with "repository not found"
- The S3 repository is not registered. Register it with
  `PUT _snapshot/<name>` pointing to the S3 bucket with the correct
  IAM role.

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
