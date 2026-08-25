# Advanced Patterns — OpenSearch Index Deployer
Edge-case catalogs, expert-knowledge deep dives, and recent AWS features, moved verbatim from SKILL.md.

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
| Data stream | Data stream template created; `"index_mode": "standard"` | cannot PUT mapping on a data stream directly | append-only time-series ingestion |
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

## Step 12 — Recent features
**Recent AWS OpenSearch features (2023-2026):**

- **k-NN FAISS engine with filtering (2023-2024):** Better recall when
  combined with pre/post filters. Supports `l2`, `cosinesimil`, and
  `innerproduct` space types.
- **Searchable cold storage (2023-2024):** Ultra-low-cost cold tier for
  rarely-searched data. Integrates with ILM cold phase.
- **Data streams auto-roll and lifecycle (2023-2024):** Automatic
  backing index rollover and ILM integration for time-series workloads.
- **Search pipelines GA (2023-2024):** Request and response processors
  for query-time normalization without client-side code.
- **Vector search performance improvements (2024-2025):** HNSW
  algorithm optimizations provide up to 3x latency improvement.
- **Semantic search with ML models (2024-2025):** ML Commons
  integration enables text-to-embedding at ingestion and query time.
- **Index template priority resolution (2024-2025):** Enhanced template
  matching with explicit `priority` and `version` fields.
