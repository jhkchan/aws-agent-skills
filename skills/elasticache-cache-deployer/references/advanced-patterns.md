# Advanced Patterns — ElastiCache Cache Deployer

Expert-knowledge deep dives moved verbatim from SKILL.md. Loaded on demand.

## Mindset misconceptions — full reasoning (from SKILL.md § Mindset)

- **"Memcached is the simple default; pick Redis only if you need
  persistence."** This is backwards for modern workloads. Redis supports
  Multi-AZ failover, encryption at rest and in transit, AUTH, TLS,
  clustering (sharded writes), pub/sub, sorted sets, and Global
  Datastore. Memcached supports NONE of these. Pick Redis unless the
  workload is a genuinely simple, ephemeral, multi-threaded key-value
  cache AND the operator explicitly accepts no failover, no encryption,
  no persistence, no snapshots.

- **"Cluster mode disabled with one replica is the safe default."** A
  cluster-mode-disabled Redis replication group supports at most 5
  replicas per shard and **cannot scale writes horizontally** — all
  writes hit one node. The moment write throughput exceeds one node's
  capacity, the only path forward is migrate to cluster mode enabled
  (create-new → backfill → cutover). For any workload whose write rate
  may grow, default to cluster mode enabled up front.

- **"Multi-AZ is a checkbox; pick one AZ for the replica."** Multi-AZ
  with automatic failover requires the replica in a DIFFERENT AZ than
  the primary. ElastiCache enforces this at creation for Redis, but a
  subnet group with only one AZ silently blocks Multi-AZ. Verify the
  subnet group spans at least 2 AZs before `create-replication-group`.

## Reasoning framework — why provisioning order matters (from SKILL.md)

ElastiCache configurations have **dependency and immutability
semantics** that make the provisioning order non-trivial. Wrong-order or
wrong-time decisions either cannot be reversed or require a full
cluster migration:

1. **Engine BEFORE the first write** — Redis and Memcached are NOT
   interchangeable. Memcached has no persistence, no replication, no
   failover, no encryption, no pub/sub. Migrating Memcached → Redis
   means a cache-miss cold-start window and application client
   rewrite (different APIs). Decide at provisioning.

2. **Cluster mode BEFORE write-rate growth** — Redis cluster-mode
   disabled caps writes at one node. To switch to cluster mode enabled
   later, you create a new replication group and repoint clients (full
   cutover). Default to cluster mode enabled for any workload whose
   write rate may grow.

3. **Multi-AZ + encryption BEFORE the first production write** —
   enabling encryption in transit on an existing Redis cluster requires
   a full `modify-replication-group` with a rolling node replacement
   that disconnects clients. Enable at creation. Encryption at rest
   CANNOT be added to a non-encrypted cluster without dump-and-restore.

4. **Subnet group BEFORE Multi-AZ** — Multi-AZ Redis requires the
   subnet group to span at least 2 AZs. Create the subnet group first
   with `--subnet-ids` covering multiple AZs.

5. **Node type BEFORE production traffic** — changing node type later
   requires a `modify` with rolling replacement (or for cluster mode
   enabled, a `modify-replication-group-shard-configuration` + upgrade).
   Size up front; scale testing pre-production is mandatory.

6. **Parameter group + maxmemory-policy EARLY** — a wrong
   maxmemory-policy causes silent write failures (`noeviction` returns
   OOM on writes when memory fills; `allkeys-lru` silently evicts).
   Pick at provisioning based on cache-vs-store semantics.

## Configuration dependency graph — deep-dive notes (from SKILL.md)

**The four immutable-or-near-immutable rows are the ones a baseline
model misses.** Engine, cluster-mode write-scaling, encryption at rest,
and AUTH-without-TLS are decided at creation time. The procedure below
forces an explicit decision on each before the `create` call.

**Cross-dependency gotchas** (not visible in the table):
- Enabling encryption in transit on an existing Redis cluster triggers
  a rolling node replacement that **disconnects every client** for
  30-90 seconds per node. Enable at creation, not in production.
- AUTH tokens require TLS — enabling AUTH without TLS sends the
  password in plaintext over the wire.
- A cluster-mode-disabled Redis with 5 replicas has **no horizontal
  write scaling**: all writes go to the single primary. Adding replicas
  scales reads only.
- Global Datastore does NOT replicate encryption configuration — each
  region's cluster manages its own KMS key. A missing key in a region
  blocks cluster creation there.
- Memcached `create-cache-cluster` accepts `AZMode` (`single-az` or
  `cross-az`), but `cross-az` only distributes nodes across AZs — it
  does NOT provide failover. A failed Memcached node loses its data.

## Step 5 — missing security group mistake (from SKILL.md)

**Common mistake:** forgetting to attach the security group at
creation. ElastiCache accepts `--security-group-ids` on
`create-replication-group` / `create-cache-cluster`. A missing SG
defaults to the VPC's default SG, which typically allows no inbound —
the cluster is unreachable.

## Step 6 — encryption at rest semantics (from SKILL.md)

- Apply at creation via `--at-rest-encryption-enabled`.
- CANNOT be added to an existing cluster without dump-and-restore.
- Uses AWS-managed KMS key by default; customer CMK via
  `--kms-key-id`.

## Step 6 — TLS enablement semantics (from SKILL.md)

- Apply at creation via `--transit-encryption-enabled`.
- Can be added post-creation via `modify-replication-group` — but
  this triggers a rolling node replacement that DISCONNECTS every
  client for 30-90 seconds per node.
- Default: AWS-generated cert. Custom certs via ACM are NOT supported
  on ElastiCache (use the AWS-generated cert and pin via
  `--transit-encryption-enabled`).

## Step 6 — AUTH token rules (from SKILL.md)

- Apply at creation via `--auth-token` (or `MODIFY` post-creation).
- Requires TLS (`--transit-encryption-enabled=true`) — without TLS,
  the AUTH token traverses the network in plaintext.
- Token rules: 16-128 chars, printable, non-whitespace.
- Generate via `openssl rand -base64 24`.

## Step 6 — Redis 6+ ACL and AUTH-without-TLS mistake (from SKILL.md)

**Redis 6+ ACL (user-based access control):**
- ElastiCache supports Redis 6.x ACLs via `--user-group-id`.
- Pre-defined user groups: `default` (full access + AUTH token),
  `readonly` (read-only), `readwrite` (read-write).
- Use ACLs to scope application vs analytics clients.

**Common mistake:** enabling AUTH without TLS. The token traverses
the wire in plaintext — sniffable. ALWAYS pair AUTH with
`--transit-encryption-enabled=true`.

## Step 9 — ElastiCache Serverless, Global Datastore, Outposts (from SKILL.md)

**ElastiCache Serverless (2023-2024):**
- No capacity management. AWS scales automatically based on traffic.
- VPC-only; creates its own security group and endpoint.
- Charged per request + storage (similar to DynamoDB on-demand).
- Does NOT support: cluster mode configuration, Global Datastore,
  Outposts, custom parameter groups (limited set).
- Use when the workload is unknown / bursty and the operator does not
  want to size nodes or shards.

```bash
aws elasticache create-serverless-cache \
  --serverless-cache-name prod-serverless-cache \
  --engine redis \
  --description "Serverless Redis cache" \
  --security-group-ids sg-0aaa \
  --subnet-ids subnet-0aaa subnet-0bbb \
  --user-group-id default \
  --data-storage Maximum 5000 \
  --daily-storage- retention-period 7
```

**Global Datastore (cross-region replication):**
- Redis-only; requires cluster mode enabled in primary region.
- Replicates from a primary cluster to 1+ secondary clusters in other
  regions. Writes go to primary; secondaries serve local reads.
- Typical replication lag: < 1 second (depends on inter-region latency).
- Each region's cluster has its own node type, encryption, KMS key.
- Use for: cross-region low-latency reads, DR, geo-distributed apps.

```bash
# Create the primary (must be cluster-mode enabled)
aws elasticache create-global-replication-group \
  --global-replication-group-id-suffix prod-global-cache \
  --global-replication-group-description "Global Redis cache" \
  --primary-replication-group-id prod-cache-us-east-1

# Add a secondary region
aws elasticache create-global-replication-group-member \
  --global-replication-group-id fgid:prod-global-cache \
  --replication-group-id prod-cache-eu-west-1 \
  --replication-group-region eu-west-1
```

**Outposts support:**
- Redis only; subset of node types (cache.m5, cache.r5, cache.t3).
- Data residency / on-prem latency workloads.
- Uses Outpost-local hardware; capacity subject to Outpost sizing.

**Common mistake:** provisioning a cluster-mode-disabled Redis then
trying to add Global Datastore. Global Datastore requires cluster mode
enabled in the primary. Decide at creation.

## Recent AWS features 2023-2026 (from SKILL.md)

- **ElastiCache Serverless (2023-2024):** AWS manages capacity, scaling,
  and shard count automatically. Charged per request + storage. Use for
  unknown / bursty workloads where the operator does not want to size
  nodes. Provisioning tip: VPC-only; limited parameter group support.
- **Global Datastore enhancements (2023-2024):** Cross-region replication
  with sub-second typical lag. Now supports up to 5 secondary regions.
  Provisioning tip: primary must be cluster-mode-enabled; each region
  uses its own KMS key.
- **Valkey engine support (2024-2025):** Redis fork (after Redis license
  change); drop-in replacement, fully supported by AWS. Use
  `--engine valkey` if license-permissive alternative is preferred.
- **Outposts support (2023-2024):** Redis on Outposts for on-prem
  latency / data sovereignty. Subset of node types (cache.m5, cache.r5,
  cache.t3).
- **Graviton (g-series) node types (2022-2024):** `cache.r6g`,
  `cache.m6g`, `cache.t4g` offer ~20% better price/performance over
  previous gen. Default to Graviton for new clusters.
- **Redis 7.x support (2023-2024):** ACLs, sharded pub/sub, functions
  (Lua enhancement). Provisioning tip: use Redis 6+ ACLs to scope
  application vs analytics clients.
- **AWS-managed service updates (rolling):** ElastiCache applies engine
  upgrades during the maintenance window. Provisioning tip: set
  maintenance window explicitly; do NOT use the default random window.
