# Engine and Topology Guide — ElastiCache Cache Deployer

Deep reference on Redis-vs-Memcached feature tradeoffs, cluster-mode
shard math, replica-vs-shard scaling decisions, Multi-AZ failover
internals, encryption/AUTH/TLS interactions, and Global Datastore
topology. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Redis vs Memcached — full feature matrix

The single highest-impact ElastiCache decision is the engine. It is
**immutable** without a full application client rewrite (different
APIs) plus a cache-miss cold-start window.

| Feature / property | Redis OSS | Valkey | Memcached |
|---|---|---|---|
| Data types | strings, lists, sets, sorted sets, hashes, streams, bitmaps, hyperloglog | same as Redis | strings only |
| Persistence (RDB snapshots / AOF) | YES | YES | NO |
| Replication (primary + replicas) | YES | YES | NO |
| Multi-AZ failover | YES (automatic) | YES (automatic) | NO (`AZMode=cross-az` distributes nodes only) |
| Clustering / sharded writes | YES (cluster mode enabled, up to 500 shards) | YES | NO (multi-threaded single node) |
| Encryption at rest | YES | YES | NO |
| Encryption in transit (TLS) | YES | YES | NO |
| AUTH password | YES (also ACLs in Redis 6+) | YES | NO |
| pub/sub | YES (incl. sharded pub/sub in 7.x) | YES | NO |
| Lua scripting | YES | YES | NO |
| Streams | YES | YES | NO |
| Global Datastore (cross-region) | YES | YES (where supported) | NO |
| Max item size | 512 MB | 512 MB | 1 MB default (1024 MB max via `max-item-size`) |
| Multi-threading | NO (single-threaded per shard) | NO (mostly; per-shard threads in 8.x) | YES (per node) |
| Eviction policies | LRU, LFU, random, TTL, noeviction (configurable) | same | LRU only |
| Snapshot / backup | YES (automated + manual) | YES | NO |
| Serverless (managed scaling) | YES | YES | NO |
| Outposts support | YES (subset of node types) | YES | NO |

**Decision rule (when in doubt):** pick Redis (or Valkey). Memcached
is the right answer ONLY when the workload is a genuinely simple,
ephemeral, multi-threaded key-value cache AND the operator explicitly
accepts no failover, no persistence, no encryption. Memcached's
multi-threading is its one real advantage — but a sharded Redis cluster
achieves similar horizontal scale via shards.

### Valkey note (2024-2025)

After Redis OSS changed its license (SSPL in 7.x), AWS introduced
Valkey as a Redis fork under the BSD license. The APIs and protocols
are compatible — clients work without modification. Use Valkey
(`--engine valkey`) if the workload needs a license-permissive engine
or the operator prefers the open-source fork.

## Cluster mode enabled vs disabled — write-scaling math

Redis cluster mode enabled distributes writes across shards via hash
slots. This is the **only** way to scale Redis writes horizontally.

### Hash slot mechanics

- Total slots: 16,384 (0-16383).
- Slot for a key: `CRC16(key) mod 16384`.
- Each shard owns a contiguous range of slots (e.g., shard 1 owns
  0-5460, shard 2 owns 5461-10922, shard 3 owns 10923-16383).
- Keys are distributed across shards based on their slot.

### Hash tags for key co-location

When the workload needs multi-key transactions (MULTI/EXEC) or
cross-key operations (MGET, SUNION) on related keys, force
co-location with hash tags:

```text
# Without hash tags:
SET user1000:cart "..."    # slot = CRC16("user1000:cart") mod 16384
SET user1000:profile "..." # slot = CRC16("user1000:profile") mod 16384
# These might land on DIFFERENT shards → CROSSSLOT error on MULTI/EXEC.

# With hash tags:
SET {user1000}:cart "..."    # slot = CRC16("user1000") mod 16384
SET {user1000}:profile "..." # slot = CRC16("user1000") mod 16384 (SAME slot)
# Both keys land on the SAME shard → MULTI/EXEC works.
```

The `{...}` syntax tells Redis to use only the tagged portion for slot
computation. Use when transactions or multi-key ops matter.

### Shard count estimator

```text
required_shards = ceil(sustained_writes_per_sec / (node_write_baseline × 0.60))

# Reference baselines (pipelined SET on small values):
#   cache.t3.medium:    ~15,000 writes/sec
#   cache.r6g.large:    ~50,000 writes/sec
#   cache.r6g.2xlarge: ~100,000 writes/sec
#   cache.r6g.4xlarge: ~180,000 writes/sec
#   cache.r6g.8xlarge: ~300,000 writes/sec

# 60% headroom rule: real workloads have larger values, non-pipelined
# patterns, SORT/EVAL — leave 40% headroom.
```

**Examples:**
- 50k writes/sec, `cache.r6g.large`: `ceil(50000 / (50000 × 0.6)) = 2 shards`.
- 200k writes/sec, `cache.r6g.2xlarge`: `ceil(200000 / (100000 × 0.6)) = 4 shards`.
- 500k writes/sec, `cache.r6g.4xlarge`: `ceil(500000 / (180000 × 0.6)) = 5 shards`.

### Replica count per shard

Replicas scale READS, not writes. A 4-shard cluster with 2 replicas
per shard has:
- 4 primaries (write capacity: 4 × baseline).
- 8 replicas (read capacity: 8 × baseline, in addition to primaries).
- Total nodes: 4 + 8 = 12 nodes.

**Rule:** add replicas when read rate > primary's read capacity OR when
Multi-AZ failover is required (minimum 1 replica per shard in a
different AZ).

## Multi-AZ failover internals

A baseline model says "Multi-AZ gives you failover" without explaining
the mechanics. This is the load-bearing detail for production SLAs.

### Redis cluster mode DISABLED + Multi-AZ

- Topology: 1 primary in AZ-a, 1+ replicas in AZ-b/c.
- Promotion: the highest-priority replica in a different AZ becomes
  primary on primary failure.
- Time: typically 10-30 seconds (DNS update +
  replica-promotion sequence).
- Endpoint: the replication group's `PrimaryEndpoint` is stable —
  it updates to point to the new primary automatically.
- Data loss: writes in-flight to the old primary but not yet replicated
  are LOST. This is asynchronous replication.

### Redis cluster mode ENABLED + Multi-AZ

- Topology: per-shard primary + replica(s) in different AZs.
- Promotion: per-shard. A 5-shard cluster can have up to 5 simultaneous
  failovers.
- Time: typically 10-30 seconds per shard.
- Endpoint: the `ConfigurationEndpoint` is stable and routes to the
  correct shard after failover.
- Cross-shard ops (`MGET`, `MULTI` across slots) may fail transiently
  during failover — clients must retry.

### Memcached `AZMode=cross-az` — NOT failover

- Distributes nodes across AZs for AZ-spread.
- A failed node is GONE — clients must rehash or remove it.
- Data on the failed node is LOST (no persistence, no replication).
- This is the most commonly missed detail: "cross-AZ Memcached" is NOT
  Multi-AZ in the Redis sense.

### Promotion priority

Redis replicas have a `Priority` (1-100, lower = higher priority).
Priority 0 means "never promote." Use to control failover order:

```bash
# Set replica priority (1 = highest, 0 = never promote)
aws elasticache modify-replication-group-shard-configuration \
  --replication-group-id prod-cache \
  --node-group-id 0001 \
  --replica-configuration \
    NodeGroupId=0001,NewReplicaCount=1,ReplicaAvailabilityZones=us-east-1b
```

## Encryption / AUTH / TLS interactions

| Feature | Memcached | Redis without TLS | Redis with TLS |
|---|---|---|---|
| Encryption at rest | NO | YES (AWS-managed or CMK) | YES |
| Encryption in transit | NO | NO | YES |
| AUTH password | NO | possible but INSECURE (plaintext) | YES (recommended) |
| ACLs (user-based) | NO | possible but INSECURE | YES |

**Hard rule:** AUTH requires TLS. Without TLS, the AUTH token traverses
the network in plaintext — sniffable. ElastiCache does NOT enforce this
at the API level (you CAN set AUTH without TLS), but doing so is a
security anti-pattern.

### Enabling TLS on an existing cluster

```bash
aws elasticache modify-replication-group \
  --replication-group-id prod-cache \
  --transit-encryption-enabled true \
  --apply-immediately
```

This triggers a rolling node replacement. Each node is replaced
one at a time; clients connected to the replaced node disconnect for
30-90 seconds. Total time: ~N × 60 seconds for N nodes. Plan a
maintenance window.

**For production:** enable TLS at creation, not post-creation.

### Customer CMK for encryption at rest

```bash
# Create a CMK
aws kms create-key --description "Customer CMK for ElastiCache prod-cache"

# Create an alias
aws kms create-alias \
  --alias-name alias/prod-cache-kms \
  --target-key-id <key-id>

# Use at cluster creation
aws elasticache create-replication-group \
  --replication-group-id prod-cache \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-cache-kms \
  ...
```

The CMK's key policy must grant the ElastiCache service principal
`kms:GenerateDataKey` and `kms:Decrypt`. ElastiCache adds these
grants automatically when you reference the CMK at creation.

### Adding encryption at rest post-creation

**You CANNOT.** Encryption at rest is a creation-time-only setting.
To encrypt an existing unencrypted cluster:

1. Create a new encrypted cluster.
2. Dump data from old cluster (`--snapshot` + restore to encrypted, or
   application-level dump-and-load).
3. Repoint clients to the new cluster.
4. Delete the old cluster.

This is a full migration. Plan for it; enable at creation.

## Snapshot internals (Redis only)

### Automated snapshots

- `--snapshot-retention-limit`: days to keep (1-35). 0 = disabled.
- `--snapshot-window`: UTC window (e.g., `03:00-05:00`). Avoid overlap
  with maintenance window.
- Stored in AWS-managed S3 (not customer-visible).
- Format: RDB (Redis Database) file.

### Manual snapshots

```bash
aws elasticache create-snapshot \
  --cache-cluster-id prod-cache-0001 \
  --snapshot-name prod-cache-2026-08-05-preupgrade
```

Manual snapshots persist until explicitly deleted. Use for pre-upgrade
checkpoints and long-term retention beyond the automated limit.

### Restore creates a NEW cluster

```bash
aws elasticache create-replication-group \
  --replication-group-id prod-cache-restored \
  --cache-node-type cache.r6g.2xlarge \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --snapshot-arns arn:aws:elasticache:us-east-1:123456789012:snapshot:prod-cache-snap \
  --snapshot-retention-limit 7
```

- Node type at restore time (NOT source's type).
- Cluster mode topology preserved from snapshot.
- Encryption configuration NOT inherited — specify at restore time.
- Parameter group NOT inherited — specify at restore time.

## Global Datastore topology

Cross-region replication with sub-second typical lag. Redis only,
cluster mode enabled in primary.

```text
┌─────────────────────────────────────────┐
│  Primary Region (us-east-1)             │
│  prod-cache (3 shards × 1 replica each) │
│  WRITES go here                         │
└────────────┬────────────────────────────┘
             │ Global Datastore replication
             │ (< 1 sec typical lag)
   ┌─────────┴─────────┐
   ▼                   ▼
┌──────────────┐  ┌──────────────┐
│ eu-west-1    │  │ ap-southeast │
│ prod-cache   │  │ prod-cache   │
│ READS only   │  │ READS only   │
└──────────────┘  └──────────────┘
```

**Rules:**
- Primary cluster must be cluster-mode-enabled.
- Each region's cluster has its OWN node type, encryption, KMS key.
- Secondary clusters are READ-ONLY (writes to secondary fail).
- Failover: promote a secondary to primary via
  `failover-global-replication-group` (manual; ~1-2 minutes).
- Up to 5 secondary regions.

**Provisioning sequence:**
1. Create the primary cluster in region 1 (cluster mode enabled).
2. Wait for `Status=available`.
3. Create the Global Datastore referencing the primary.
4. Create secondary clusters in each target region.
5. Add each secondary as a Global Datastore member.

**Common mistake:** provisioning the primary cluster-mode-DISABLED,
then trying to add Global Datastore. Global Datastore requires
cluster-mode-enabled primary. Decide at creation.

## Node type families — when to pick which

| Family | Examples | Optimized for | When to pick |
|---|---|---|---|
| `cache.r7g`, `cache.r6g` | r6g.large (13 GiB), r6g.2xlarge (62 GiB), r6g.8xlarge (249 GiB) | Memory | General Redis; large datasets; production. DEFAULT CHOICE. |
| `cache.x2g` | x2g.large (33 GiB), x2g.4xlarge (132 GiB) | Memory (max) | Very large datasets; dense packing; cost-per-GB-sensitive. |
| `cache.m7g`, `cache.m6g` | m6g.large (6.7 GiB), m6g.2xlarge (29 GiB) | Balanced | Mixed workloads; mid-size datasets; CPU + memory balance. |
| `cache.c7g`, `cache.c6g` | c6g.large (3.6 GiB), c6g.2xlarge (15 GiB) | Compute | Compute-heavy (Lua scripts, SORT, complex aggregations). |
| `cache.t4g`, `cache.t3` | t3.micro (0.5 GiB), t3.small (1.4 GiB), t3.medium (3.2 GiB) | Burst | Dev / test / low-traffic; non-production. CPU credits burst. |
| Legacy (`cache.t1`, `cache.m1`, `cache.m2`, `cache.r3`) | — | — | DO NOT USE — end-of-life. |

**Default recommendation:** `cache.r6g.<size>` for production Redis.
Pick the size based on memory needed (§"Expert heuristic: effective
memory calculator" in SKILL.md).

**Pricing note:** Graviton (g-series) families are ~20% cheaper than
the equivalent Intel (no `-g` suffix) for the same memory/compute.
Always prefer Graviton for new clusters.

## AWS documentation references

- Choosing Between Redis and Memcached — https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SelectEngine.html
- Cluster Mode — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/ClusterMode.html
- Encryption and AUTH — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/encryption.html
- Replication and Multi-AZ — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.html
- Global Datastore — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Redis-Global-Datastore.html
- ElastiCache Serverless — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/serverless.html
- Node Type Sizing — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/nodes-select-size.html
