# Advanced Patterns — OpenSearch Migration Operator
Edge-case catalogs, expert-knowledge deep dives, and recent AWS features, moved verbatim from SKILL.md.

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
