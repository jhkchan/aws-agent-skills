# Advanced Patterns — ElastiCache Cluster Deployer

Expert-knowledge deep dives moved verbatim from SKILL.md. Loaded on demand.

## Mindset misconceptions — full reasoning (from SKILL.md § Mindset)

- **"Encryption can be enabled later."** It CANNOT. At-rest encryption
  (KMS) and in-transit encryption (TLS) are creation-time-only settings
  for Redis replication groups. If you need encryption, you must enable
  it when creating the replication group. Existing non-encrypted
  clusters require migration (create new encrypted cluster, seed from
  backup or application-level replication).

- **"Cluster mode and non-cluster mode are interchangeable."** They are
  NOT. Non-cluster mode uses a single primary with up to 5 read
  replicas — simple, but limited to the memory of one node. Cluster
  mode enabled shards data across multiple primaries (1-500 shards),
  each with its own replicas — horizontally scalable, but requires
  cluster-aware client libraries. Switching modes requires migration.

- **"Memcached and Redis are the same to provision."** They are NOT.
  Memcached is a flat cache (no replication, no persistence, no
  encryption, no multi-AZ failover, no snapshots). Redis supports all
  of these. Choose Memcached only for simple, ephemeral, multi-
  threaded caching with no durability requirements.

## Configuration dependency graph — deep-dive notes (from SKILL.md)

**The encryption-at-creation row is the one a baseline model misses.**
A model may suggest "enable encryption after creating the cluster."
This is IMPOSSIBLE for Redis replication groups. The procedure forces
an explicit encryption decision before the create call.

**Cross-dependency gotchas:**
- AUTH token requires in-transit encryption (TLS). AUTH without TLS
  sends the token in cleartext.
- Multi-AZ automatic failover requires at least one replica per shard.
- Cluster mode and non-cluster mode use different API parameters
  (`--num-node-groups` vs `--num-cache-clusters`). Client libraries
  must be cluster-aware for cluster mode.
- Online resharding is supported ONLY on cluster-mode-enabled groups.
- Global Datastore requires matching engine versions across regions.
- Snapshot window and maintenance window must NOT overlap.

## Step 13 — Recent AWS features 2023-2026 (from SKILL.md)

- **Graviton3 (r7g) node types (2023-2024):** Significant price/
  performance improvements over r6g. Recommended for new clusters.
- **Serverless ElastiCache (2023-2024):** Auto-scaling without cluster
  management. Currently in preview for Redis.
- **TLS 1.3 support (2023-2024):** Enhanced in-transit encryption.
- **Global Datastore improvements (2023-2024):** Higher throughput,
  lower lag, more regions.
- **Online vertical scaling (2024-2025):** Change node type without
  downtime for cluster-mode groups.
- **Enhanced CloudWatch metrics (2024-2025):** Per-shard metrics and
  replication lag tracking.
