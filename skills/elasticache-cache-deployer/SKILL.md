---
name: elasticache-cache-deployer
description: >-
  Provisions ElastiCache (Redis OSS / Memcached) clusters with production
  defaults: engine selection (Redis for persistence, clustering, pub/sub,
  TLS vs Memcached for simple key-value, multi-threaded, no persistence),
  cluster mode enabled vs disabled, node type sizing, Multi-AZ failover
  (Redis only), VPC-only networking, encryption at-rest + in-transit +
  AUTH (Redis only), subnet group, parameter group maxmemory-policy,
  snapshot retention, ElastiCache Serverless, Global Datastore. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when creating
  an ElastiCache cluster, choosing between Redis and Memcached, designing
  a Multi-AZ Redis failover topology, sizing cache nodes, or generating
  provisioning CLI commands / IaC templates. Triggers: create
  ElastiCache, provision Redis, provision Memcached, ElastiCache cluster
  mode, Redis replication group, Global Datastore, ElastiCache
  Serverless, cache node type sizing.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with elasticache, ec2, kms, and
  iam access. Works with Terraform aws_elasticache_cluster /
  aws_elasticache_replication_group resources and CloudFormation
  AWS::ElastiCache::* templates.
keywords:
  - aws
  - elasticache
  - redis
  - memcached
  - cloudops
  - deploy
  - provisioning
  - cache
  - replication group
  - cluster mode
  - multi-az
  - failover
  - encryption at rest
  - encryption in transit
  - auth token
  - tls
  - subnet group
  - parameter group
  - maxmemory-policy
  - allkeys-lru
  - noeviction
  - snapshot
  - backup
  - global datastore
  - elasticache serverless
  - outposts
tags:
  - aws
  - elasticache
  - redis
  - memcached
  - cloudops
  - deploy
  - databases
  - cache
  - provisioning
  - replication-group
  - multi-az
  - encryption
  - global-datastore
  - serverless
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - elasticache
    - redis
    - memcached
    - cloudops
    - deploy
    - databases
    - cache
    - provisioning
    - replication-group
    - multi-az
    - encryption
    - global-datastore
    - serverless
  dependencies:
    - aws-orchestrator
  keywords:
    - create elasticache
    - provision redis cluster
    - provision memcached cluster
    - elasticache replication group
    - elasticache cluster mode
    - multi-az redis
    - redis failover
    - elasticache encryption
    - elasticache auth token
    - elasticache subnet group
    - elasticache parameter group
    - elasticache snapshot
    - global datastore
    - elasticache serverless
    - cache node type
  when_to_use: >-
    Invoke when the user wants to create a new ElastiCache cluster (Redis or
    Memcached), design a Multi-AZ Redis failover topology, choose between
    Redis and Memcached, size cache nodes for a workload, harden an existing
    cluster before production (TLS, AUTH, encryption at rest), set up a
    Global Datastore for cross-region replication, provision an ElastiCache
    Serverless cache, or generate provisioning CLI commands / IaC templates.
    Do NOT invoke for auditing existing cluster posture (use
    elasticache-cluster-auditor), or for non-ElastiCache caches (DynamoDB
    DAX, MemoryDB for Redis, self-managed Redis on EC2).
---

# ElastiCache Cache Deployer

An AWS CloudOps agent skill that provisions ElastiCache (Redis OSS /
Memcached) clusters with correct defaults. The skill walks the operator
through a 10-step provisioning procedure, captures the operator's
engine, topology, security, and capacity decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create ElastiCache, provision Redis, provision Memcached, ElastiCache
deployment, replication group, cluster mode enabled, cluster mode
disabled, Multi-AZ Redis, automatic failover, encryption at rest,
encryption in transit, AUTH token, TLS, subnet group, parameter group,
maxmemory-policy, allkeys-lru, noeviction, snapshot retention,
Global Datastore, ElastiCache Serverless, Outposts, cache node type,
cache.t3, cache.r6g, cache.x2g.

## Invocation contract (hard requirement)

When this skill is invoked with a cache-provisioning request (cluster
name, engine choice, workload shape, region, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
§"Output format" using the literal all-caps labels `CACHE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Mindset

**One-line takeaway:** ElastiCache correctness is decided at creation
time. Engine choice (Redis vs Memcached), cluster-mode topology, node
type, and the Multi-AZ + encryption bundle are impossible or disruptive
to change later — the provisioning procedure treats each as a one-way
door and forces an explicit decision before the `create` call.

Three misconceptions dominate ElastiCache misdesign at provisioning time:

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

## Quick navigation

| Section | When to read |
|---|---|
| §"Prerequisites" | Always — verify before provisioning |
| §"Step 1 — Engine selection" | Picking Redis vs Memcached |
| §"Step 2 — Cluster mode decision" | Single-shard vs sharded Redis |
| §"Step 3 — Node type sizing" | Picking cache.t3 / r6g / x2g |
| §"Step 4 — Multi-AZ + failover" | Production Redis topology |
| §"Step 5 — Network + security" | VPC, subnet group, SG, ports |
| §"Step 6 — Encryption + AUTH + TLS" | Redis-only security bundle |
| §"Step 7 — Parameter groups" | maxmemory-policy, timeout |
| §"Step 8 — Snapshots / backups" | Redis-only automated backups |
| §"Step 9 — Serverless / Global Datastore" | Latest 2023-2026 features |
| §"Step 10 — CloudWatch alarms" | Operational hygiene |
| §"NEVER do these things" | Review before signing off |
| §"Output format" | The literal checklist template |
| references/engine-and-topology.md | Deep Redis-vs-Memcached + cluster-mode math |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Reasoning framework (why provisioning order matters)

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

## ElastiCache configuration dependency graph (novel heuristic)

ElastiCache configurations are NOT independent. Many are immutable
after creation, others silently downgrade. Use this graph both to
sequence provisioning and to debug "why can't I add this?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Engine (Redis / Memcached) | none — `create` argument | **IMMUTABLE** — migration = full cluster swap + client rewrite | persistence, replication, clustering, encryption, pub/sub (Redis only) |
| Cluster mode (enabled / disabled) | Redis engine | **IMMUTABLE for write scaling** — switching disabled → enabled requires new group + cutover | horizontal write scaling, up to 500 shards |
| Node type | none — `create` argument | changeable via `modify` with rolling node replacement (disconnects clients) | memory budget, CPU, network |
| Multi-AZ with automatic failover | Redis engine + subnet group spanning >=2 AZs + >=1 replica | failover promoted only if replica is in a different AZ than primary | primary-AZ-failure resilience |
| Number of replicas | Redis engine | 0-5 per shard (cluster mode enabled); 0-5 total (cluster mode disabled) | read scaling + failover |
| Encryption at rest | Redis engine + must enable at creation | **CANNOT be added post-creation** without dump-and-restore; Memcached: NOT supported | compliance (PCI-DSS, HIPAA) |
| Encryption in transit (TLS) | Redis engine + must enable at creation + AUTH token recommended | can be enabled via `modify` with rolling replacement (client disconnects); Memcached: NOT supported | TLS-only clients, network sniffing defense |
| AUTH token | Redis engine + encryption in transit strongly recommended | AUTH requires TLS — without TLS the token traverses network in plaintext | password-protected Redis |
| Subnet group (CacheSubnetGroupName) | VPC + >=1 subnet; >=2 AZs for Multi-AZ | **subnets CANNOT be removed** once added; can only add | VPC-only addressing |
| Security group | VPC | port 6379 (Redis) or 11211 (Memcached) inbound from application SG | network isolation |
| Parameter group | none — `create` argument | changes apply on next reboot (parameter group modifications are not immediate) | maxmemory-policy, timeout, tcp-keepalive |
| Snapshot retention (automated) | Redis engine + `snapshotRetentionLimit > 0` | Memcached: NOT supported; restore creates a NEW cluster | point-in-time recovery for Redis |
| Snapshot window | Redis engine + snapshots enabled | maintenance / snapshot windows must NOT overlap | deterministic backup timing |
| Maintenance window | none | ElastiCache applies engine upgrades in this window | controlled upgrade timing |
| Global Datastore | Redis engine + cluster mode enabled + >=2 regions + each region's cluster already provisioned | primary cluster must be cluster-mode-enabled; each region uses its own KMS key / node type | cross-region low-latency reads, DR |
| ElastiCache Serverless | none — separate API (`create-serverless-cache`) | NOT compatible with cluster mode, Global Datastore, Outposts; VPC-only | no capacity management, automatic scaling |
| Outposts | Redis engine + Outpost in account | subset of node types only; data residency constraint | on-prem latency, data-sovereign workloads |

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

## Expert heuristic: effective memory calculator

ElastiCache markets a node type by total memory, but the usable memory
for application data is significantly less. A baseline model quotes
the spec-sheet number; this heuristic gives the real figure.

**Formula for Redis (cluster mode enabled, no replicas):**

```text
usable_per_shard = node_memory_bytes × 0.50
# 50% rule: Redis reserves ~50% for overhead, COPY-on-write fork
# during BGSAVE, and the QUERY/Sort buffer. Going above 50% risks
# OOM during snapshot / failover.

total_usable = usable_per_shard × number_of_shards
max_item_size = 512 MB per single value (Redis hard limit, NOT node-size-dependent)
```

**Formula for Redis (cluster mode disabled, with replicas):**

```text
usable_total = node_memory_bytes × 0.50
# Replicas do NOT add usable memory — they hold a copy of the same data.
# Multi-AZ replicas add availability, NOT capacity.
```

**Formula for Memcached (multi-threaded, no replication):**

```text
usable_per_node = node_memory_bytes × 0.90
# Memcached has minimal overhead (no persistence, no replication, no fork).

total_usable = usable_per_node × number_of_nodes
max_item_size = 1 MB default (configurable via parameter group `max-item-size`,
                               max 1024 MB)
```

**Concrete example — cache.r6g.2xlarge (62.34 GiB nominal):**

| Topology | Calculation | Usable for application data |
|---|---|---|
| Redis cluster mode disabled, 1 primary + 1 replica | 62.34 × 0.50 | **31.17 GiB** (replica holds copy, no extra) |
| Redis cluster mode enabled, 3 shards × 1 primary + 1 replica each | 62.34 × 0.50 × 3 | **93.51 GiB** |
| Memcached, 3 nodes | 62.34 × 0.90 × 3 | **168.32 GiB** |

**Implication:** for the SAME node type and node count, Memcached
exposes ~3-5x the usable memory of Redis cluster-mode-disabled.
Redis's overhead is the price of persistence + replication + failover.
Choose the engine knowing this overhead, not by comparing spec-sheet
numbers.

## Expert heuristic: cluster mode shard count estimator

Redis cluster mode enabled distributes writes across shards. Each shard
is a separate primary; the cluster hash-slots data across 16,384 slots
(0-16383) sharded by key. The number of shards is the horizontal-write
scaling factor.

**Rule:** for write-heavy workloads (more than 50,000 writes/sec
sustained), size shards so that per-shard write rate stays under 60% of
the node's published baseline.

**Quick check formula:**

```text
required_shards = ceil(sustained_writes_per_sec / (node_write_baseline × 0.60))
max_shards = 500   # ElastiCache hard limit (250 soft, 500 via support ticket)

# cache.r6g.2xlarge baseline: ~100,000 writes/sec per primary
# Example: 200,000 writes/sec sustained
# required_shards = ceil(200000 / (100000 × 0.60)) = ceil(3.33) = 4 shards
```

**Why 60%:** ElastiCache node baselines are measured with pipelined
`SET` on small values. Real-world workloads have larger values,
non-pipelined patterns, and `EVAL`/`SORT` that consume CPU. Leaving
40% headroom is the threshold observed in production incident
post-mortems, not a documented AWS limit.

**Read-scaling note:** replicas per shard scale READS, not writes. A
4-shard cluster with 2 replicas per shard has 4 primaries (write
capacity) and 8 replicas (read capacity in addition to primaries).

**Common scenarios:**
- **Low write, high read session store** (1k writes/sec, 50k reads/sec):
  2 shards × 3 replicas each → 2 write paths, 6 read paths + primaries.
- **High-write real-time leaderboard** (300k writes/sec): 5 shards × 1
  replica each → 5 write paths, 5 read paths. Verify per-shard rate.
- **Globally distributed geo-cache**: 3 shards in primary region +
  Global Datastore to 2 secondary regions. Writes go to primary;
  secondary regions serve local reads.

## Expert heuristic: failover promotion semantics

A baseline model says "Multi-AZ gives you failover" without explaining
what gets promoted and how long it takes. This is the load-bearing
detail for production SLAs.

**Redis cluster mode disabled + Multi-AZ + automatic failover:**
- The replica in a different AZ is promoted to primary on primary
  failure.
- Promotion time: typically **10-30 seconds** (DNS update +
  replica-promotion sequence).
- Existing client connections drop; clients must reconnect to the new
  primary endpoint (the replication group's PrimaryEndpoint is stable
  and updates automatically).
- Data loss window: writes that were in-flight to the old primary but
  not yet replicated to the promoted replica are LOST. This is
  asynchronous replication — there is no synchronous Redis option in
  ElastiCache.

**Redis cluster mode enabled + Multi-AZ + automatic failover:**
- The replica in a different AZ is promoted PER SHARD. A 5-shard
  cluster can have up to 5 simultaneous shard failovers.
- Promotion time: typically **10-30 seconds** per shard; the
  ConfigurationEndpoint stays stable.
- Cross-shard operations (`MGET`, `MULTI` on multi-key transactions)
  may fail transiently during failover.

**Memcached with `AZMode=cross-az`:**
- **NO automatic failover.** A failed node is gone — clients must
  rehash or remove it from the consistent-hash ring.
- Data on the failed node is LOST (no persistence, no replication).
- This is the most commonly missed detail: "cross-AZ Memcached" sounds
  like Multi-AZ but is NOT.

**Practical implication:** if the workload's SLA cannot tolerate a
30-second client reconnect or any data loss window, Redis alone is
insufficient — the application must handle retry/idempotency, and
critical state must live in a durable store (DynamoDB, RDS) with Redis
as a cache in front. ElastiCache Redis is NOT a primary database.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with ElastiCache access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Cache nodes, subnet groups, snapshots are region-scoped | `aws configure get region` |
| VPC ID + at least 2 subnets in different AZs (for Multi-AZ Redis) | ElastiCache is VPC-only; Multi-AZ requires multi-AZ subnet group | `aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc>"` — confirm >=2 distinct `AvailabilityZone` values |
| Cluster name unique in this region | Names are region-unique | `aws elasticache describe-replication-groups --replication-group-id <name>` returns `ReplicationGroupNotFound` |
| KMS key ARN (if encryption at rest with customer CMK) | Custom encryption requires a CMK in the same region | `aws kms describe-key --key-id <cmk-id>` |
| Security group with correct port (6379 Redis / 11211 Memcached) inbound from application SG | Network isolation; wrong port = silent connectivity failure | `aws ec2 describe-security-groups --group-ids <sg>` — verify inbound rule on 6379 or 11211 |
| AUTH token strength (if Redis AUTH) | Must be 16-128 chars, printable, non-whitespace | Generate via `openssl rand -base64 24` |
| Workload description (cache vs store, write rate, data size) | Drives engine, cluster mode, node type, replica count, maxmemory-policy decisions | Captured in the prompt or follow-up question |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Engine selection (immutable — decide BEFORE create)

The engine decision is the highest-impact ElastiCache design choice
and is **immutable** without a full migration.

**Decision tree:**

```text
Does the workload need ANY of: persistence, replication, failover,
encryption, pub/sub, sorted sets, Lua scripts, Global Datastore,
cross-region replication?
├── YES → Redis OSS  (the only engine that supports these)
│         Note: ElastiCache also offers Valkey (Redis fork) — same
│         APIs, drop-in replacement, fully supported by AWS.
└── NO → Is the workload a genuinely simple, ephemeral,
         multi-threaded key-value cache where the operator explicitly
         accepts no failover, no persistence, no encryption?
    ├── YES → Memcached
    └── NO  → Redis OSS  (default; the safest choice)
```

**Feature comparison:**

| Feature | Redis OSS | Memcached |
|---|---|---|
| Data types | strings, lists, sets, sorted sets, hashes, streams, bitmaps, hyperloglog | strings only |
| Persistence (RDB snapshots / AOF) | YES | NO |
| Replication | YES (primary + replicas) | NO |
| Multi-AZ failover | YES (automatic) | NO (`AZMode=cross-az` distributes nodes only) |
| Clustering / sharded writes | YES (cluster mode enabled, up to 500 shards) | NO (multi-threaded single node, scale-up only) |
| Encryption at rest | YES | NO |
| Encryption in transit (TLS) | YES | NO |
| AUTH password | YES | NO |
| pub/sub | YES | NO |
| Lua scripting | YES | NO |
| Streams | YES | NO |
| Multi-AZ | YES | NO |
| Global Datastore (cross-region) | YES | NO |
| Max item size | 512 MB | 1 MB default (1024 MB max via `max-item-size`) |
| Multi-threading | NO (single-threaded per shard; scale via shards) | YES (multi-threaded per node) |
| Eviction policies | configurable (LRU, LFU, TTL, noeviction) | LRU only |
| Snapshot / backup | YES (automated + manual) | NO |

**Common mistake:** picking Memcached for "simplicity" then needing
encryption or failover later. Memcached → Redis migration is a full
application client rewrite (different APIs) plus a cache-miss
cold-start window. Default to Redis unless Memcached's specific
properties (multi-threading, simple strings, no overhead) are
explicitly required.

### Step 2 — Cluster mode decision (immutable for write scaling — decide BEFORE create)

For Redis, cluster mode determines whether writes scale horizontally.
This is the second-highest-impact decision and is **effectively
immutable** without a full cluster migration.

**Decision tree:**

```text
Is the Redis write rate expected to grow beyond a single primary's capacity?
├── YES → Cluster mode ENABLED (sharded; up to 500 shards; hash-slot
│         partitioned; horizontal write scaling)
└── NO  → Is the workload stable and modest (< 50k writes/sec)?
    ├── YES → Cluster mode DISABLED (single primary + up to 5 replicas)
    │         Simpler client configuration; no cross-slot restrictions.
    └── NO  → Cluster mode ENABLED (default for any growing workload)

Is multi-key transactional consistency (MULTI/EXEC across keys) required?
├── YES → Cluster mode DISABLED  (all keys on one primary; transactions trivial)
│         OR cluster mode ENABLED with hash-tag keys ({tag}) to force
│         co-location. Accept the operational overhead of hash tags.
└── NO  → Cluster mode ENABLED is safe
```

**Cluster mode enabled specifics:**
- Hash slots: 16,384 total, distributed across shards.
- Key distribution: `SLOT = CRC16(key) mod 16384`. Use hash tags
  `{user1000}:cart`, `{user1000}:profile` to force co-location.
- Cross-slot operations (`MGET`, `MULTI` on different slots) fail with
  `CROSSSLOT` error. Application must use hash tags or fan out.
- Shard count: 1-500 shards per cluster.
- Replicas per shard: 0-5.

**Cluster mode disabled specifics:**
- Single primary, up to 5 replicas.
- Writes go to the single primary only — no horizontal write scaling.
- Multi-key transactions trivial (all keys on one primary).
- Supports Multi-AZ with failover (replica promoted on primary loss).

**Common mistake:** picking cluster mode disabled for a "simpler"
setup, then needing write scaling later. Migrating from disabled to
enabled requires creating a new replication group and repointing all
clients (full cutover). Default to cluster mode enabled for any
workload whose write rate may grow.

### Step 3 — Node type sizing

ElastiCache offers cache.node-type families. Choose based on workload
shape.

**Node family selection:**

| Family | Optimized for | Use when |
|---|---|---|
| `cache.r7g`, `cache.r6g` | Memory | General-purpose Redis; large datasets; production |
| `cache.x2g` | Memory (max) | Very large datasets; dense packing |
| `cache.m7g`, `cache.m6g` | Balanced (memory + compute) | Mixed workloads; mid-size datasets |
| `cache.c7g`, `cache.c6g` | Compute | Computed-heavy (Lua scripts, SORT) |
| `cache.t4g`, `cache.t3` | Burst | Dev / test / low-traffic; non-production |
| `cache.t1`, `cache.m1`, `cache.m2` | Legacy | DO NOT USE — end-of-life |

**Size by workload:**

- **Dev / test / prototype:** `cache.t3.micro` (0.5 GiB) or
  `cache.t3.small` (1.37 GiB). Free-tier compatible; burst CPU.
- **Small production (cache, < 5 GiB data):** `cache.r6g.large`
  (13.13 GiB nominal → 6.5 GiB usable per shard).
- **Mid production (10-50 GiB data):** `cache.r6g.2xlarge`
  (62.34 GiB nominal → 31 GiB usable per shard).
- **Large production (50-200 GiB data):** `cache.r6g.4xlarge`
  (124.66 GiB) or sharded cluster mode enabled with smaller nodes.
- **Very large (200+ GiB):** `cache.r6g.8xlarge` (249.32 GiB) per
  shard; cluster mode enabled with N shards.

**Sizing rules:**
- Plan for 50% memory utilization on Redis (see §"Expert heuristic:
  effective memory calculator"). 50% of nominal is the operating budget.
- Plan for 90% on Memcached.
- For Redis with replicas, replicas do NOT add usable memory — they
  hold a copy of the same data.
- For Redis cluster mode enabled, multiply usable memory per shard by
  shard count.

**Common mistake:** sizing by spec-sheet memory. Redis needs ~50%
overhead for fork-on-BGSAVE, query buffers, and copy-on-write. Memcached
runs close to spec-sheet.

### Step 4 — Multi-AZ + automatic failover (Redis only)

Multi-AZ with automatic failover is the primary resilience control for
Redis. Memcached does NOT support Multi-AZ.

**Requirements:**
- Redis engine.
- Cluster mode enabled OR disabled (both support Multi-AZ).
- At least 1 replica in a different AZ than the primary.
- Subnet group spanning at least 2 AZs.
- `AutomaticFailoverEnabled=true` on `create-replication-group`.

**Behavior on primary failure:**
- ElastiCache detects primary failure (health check).
- A replica in a different AZ is promoted to primary (10-30 seconds).
- The replication group's PrimaryEndpoint (cluster mode disabled) or
  ConfigurationEndpoint (cluster mode enabled) updates to the new primary.
- Clients reconnect automatically through the stable endpoint.
- Data loss window: writes in-flight to the old primary but not yet
  replicated are LOST (asynchronous replication).

**Topology examples:**

```text
# Cluster mode DISABLED, Multi-AZ:
#   Primary in us-east-1a, 1 replica in us-east-1b
#   Promotes on primary failure (10-30s)

# Cluster mode ENABLED, Multi-AZ, 3 shards:
#   Shard 1: primary us-east-1a, replica us-east-1b
#   Shard 2: primary us-east-1b, replica us-east-1c
#   Shard 3: primary us-east-1c, replica us-east-1a
#   Promotes per-shard on failure (10-30s per shard)
```

**Common mistake:** subnet group with only one AZ. Multi-AZ fails
silently — ElastiCache cannot place the replica in a different AZ.
Verify subnet group spans >=2 AZs before `create-replication-group`.

### Step 5 — Network + security (VPC, subnet group, security group)

ElastiCache is **VPC-only** — there is no public IP option (unlike
RDS). All clusters live inside a VPC.

**Subnet group creation:**

```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name prod-cache-subnet \
  --cache-subnet-group-description "Multi-AZ subnet group for prod cache" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --tags Key=Environment,Value=production
```

Verify the subnets span >=2 AZs:

```bash
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZs for Multi-AZ
```

**Security group rules:**

```bash
# Inbound: allow the application's SG to reach the cache port
# Redis: port 6379
# Memcached: port 11211
aws ec2 authorize-security-group-ingress \
  --group-id sg-cache123 \
  --protocol tcp \
  --port 6379 \
  --source-security-group-id sg-app456
```

**NEVER** open the cache port to `0.0.0.0/0` — even with AUTH, this
exposes the cluster to internet scanning. Always scope inbound to the
application's SG.

**Common mistake:** forgetting to attach the security group at
creation. ElastiCache accepts `--security-group-ids` on
`create-replication-group` / `create-cache-cluster`. A missing SG
defaults to the VPC's default SG, which typically allows no inbound —
the cluster is unreachable.

### Step 6 — Encryption + AUTH + TLS (Redis only)

Encryption and AUTH are Redis-only. Memcached has NO encryption
support — if compliance requires encryption, the answer is Redis.

**Encryption at rest:**
- Apply at creation via `--at-rest-encryption-enabled`.
- CANNOT be added to an existing cluster without dump-and-restore.
- Uses AWS-managed KMS key by default; customer CMK via
  `--kms-key-id`.

**Encryption in transit (TLS):**
- Apply at creation via `--transit-encryption-enabled`.
- Can be added post-creation via `modify-replication-group` — but
  this triggers a rolling node replacement that DISCONNECTS every
  client for 30-90 seconds per node.
- Default: AWS-generated cert. Custom certs via ACM are NOT supported
  on ElastiCache (use the AWS-generated cert and pin via
  `--transit-encryption-enabled`).

**AUTH token:**
- Apply at creation via `--auth-token` (or `MODIFY` post-creation).
- Requires TLS (`--transit-encryption-enabled=true`) — without TLS,
  the AUTH token traverses the network in plaintext.
- Token rules: 16-128 chars, printable, non-whitespace.
- Generate via `openssl rand -base64 24`.

**Redis 6+ ACL (user-based access control):**
- ElastiCache supports Redis 6.x ACLs via `--user-group-id`.
- Pre-defined user groups: `default` (full access + AUTH token),
  `readonly` (read-only), `readwrite` (read-write).
- Use ACLs to scope application vs analytics clients.

**Common mistake:** enabling AUTH without TLS. The token traverses
the wire in plaintext — sniffable. ALWAYS pair AUTH with
`--transit-encryption-enabled=true`.

### Step 7 — Parameter groups (maxmemory-policy, timeout)

Parameter groups control Redis / Memcached runtime behavior. Changes
apply on next reboot (not immediate).

**Redis maxmemory-policy decision (load-bearing):**

| Policy | Behavior when memory fills | Use when |
|---|---|---|
| `allkeys-lru` | Evict least-recently-used key | General cache (data is disposable; LRU is optimal) |
| `allkeys-lfu` | Evict least-frequently-used key | Cache with skewed access (long-tail popular keys) |
| `volatile-lru` | Evict LRU among keys with TTL only | Mixed store + cache (TTL'd items evicted, persistent kept) |
| `volatile-ttl` | Evict closest-to-expiry TTL'd key | Priority-based cache (soon-to-expire items go first) |
| `noeviction` | Return OOM error on writes | Session store, persistent store (NEVER silently evict) |
| `allkeys-random` | Evict random key | Uniform-access cache (rarely optimal) |
| `volatile-random` | Evict random TTL'd key | Rare; use volatile-lru instead |

**Decision rule:**
- Workload is a CACHE (data is disposable; cache-miss is acceptable):
  `allkeys-lru` (or `allkeys-lfu` for skewed access).
- Workload is a STORE (data loss breaks the application; e.g.,
  session store, rate-limiter): `noeviction`. Plan capacity so memory
  never fills (Redis will return OOM errors instead of evicting).
- Workload is a MIX (some persistent, some disposable): `volatile-lru`
  with TTL on disposable keys.

**Other Redis parameters worth setting:**

```text
timeout 300          # Close idle clients after 5 min (default 0 = never)
tcp-keepalive 60     # Send TCP keepalive every 60s (default 300)
maxmemory-policy allkeys-lru  # Per above table
```

**Memcached parameters:**

```text
max-item-size 4194304   # 4 MB max (default 1 MB; max 1024 MB)
chunk_size_growth_factor 1.25  # Slab allocator tuning (rarely changed)
```

**Common mistake:** using `noeviction` for a cache (data is disposable
— `allkeys-lru` is correct), or `allkeys-lru` for a session store
(silent eviction breaks sessions — `noeviction` is correct).

### Step 8 — Snapshots / backups (Redis only)

Redis supports automated snapshots (RDB files) for point-in-time
recovery. Memcached does NOT support snapshots.

**Enable automated snapshots at creation:**

```bash
aws elasticache create-replication-group ... \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --snapshot-name prod-cache-snapshot
```

- `snapshot-retention-limit`: days to keep automated snapshots (1-35).
- `snapshot-window`: daily backup window (UTC). Avoid overlap with the
  maintenance window.
- Snapshots are stored in S3 (AWS-managed bucket, not customer-visible).

**Manual snapshot:**

```bash
aws elasticache create-snapshot \
  --cache-cluster-id prod-cache \
  --snapshot-name prod-cache-2026-08-05-preupgrade
```

**Restore from snapshot creates a NEW cluster:**

```bash
aws elasticache create-replication-group \
  --replication-group-id prod-cache-restored \
  --replication-group-description "Restored from snapshot" \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --snapshot-arns arn:aws:elasticache:us-east-1:123456789012:snapshot:prod-cache-snapshot
```

**Common mistake:** setting retention limit to 0 (snapshots disabled).
For production Redis, set retention 7-35 days. For dev, 1-3 days is fine.

### Step 9 — ElastiCache Serverless / Global Datastore (latest features)

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

### Step 10 — CloudWatch alarms (operational hygiene)

Recommended CloudWatch alarms on every production cluster:

```bash
# CPU utilization > 90% for 5 min
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-cpu-high" \
  --namespace AWS/ElastiCache \
  --metric-name CPUUtilization \
  --dimensions Name=CacheClusterId,Value=prod-cache \
  --statistic Average --period 60 --threshold 90 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions <sns-arn>

# Memory: swap usage > 0 (Redis should never swap)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-swap" \
  --namespace AWS/ElastiCache \
  --metric-name SwapUsage \
  --dimensions Name=CacheClusterId,Value=prod-cache \
  --statistic Average --period 60 --threshold 0 \
  --comparison-operator GreaterThan --evaluation-periods 1 \
  --alarm-actions <sns-arn>

# Evictions > threshold (cache is full and evicting — capacity issue)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-evictions" \
  --namespace AWS/ElastiCache \
  --metric-name Evictions \
  --dimensions Name=CacheClusterId,Value=prod-cache \
  --statistic Sum --period 60 --threshold 1000 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions <sns-arn>

# Replication lag (Redis replication groups)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-repl-lag" \
  --namespace AWS/ElastiCache \
  --metric-name ReplicationLag \
  --dimensions Name=CacheClusterId,Value=prod-cache \
  --statistic Average --period 60 --threshold 30 \
  --comparison-operator GreaterThan --evaluation-periods 3 \
  --alarm-actions <sns-arn>
```

## NEVER do these things

1. **NEVER pick Memcached for a workload that may need persistence,
   failover, encryption, or pub/sub.** Memcached → Redis is a full
   migration: application client rewrite + cache-miss cold-start. Pick
   Redis unless Memcached's specific properties are explicitly required.

2. **NEVER enable AUTH without TLS.** AUTH without TLS sends the
   password in plaintext over the network. Always pair
   `--auth-token` with `--transit-encryption-enabled=true`.

3. **NEVER use a single-AZ subnet group for Multi-AZ Redis.** Multi-AZ
   requires the replica in a different AZ than the primary. Verify
   `aws ec2 describe-subnets` shows >=2 distinct AZs in the subnet
   group before `create-replication-group`.

4. **NEVER open the cache security group to `0.0.0.0/0`.** Even with
   AUTH, internet exposure invites scanning and exploit attempts.
   Always scope inbound to the application's SG.

5. **NEVER use `noeviction` maxmemory-policy for a cache.** `noeviction`
   returns OOM on writes when memory fills — use `allkeys-lru` (or
   `allkeys-lfu` for skewed access). `noeviction` is for STORES, not
   caches.

6. **NEVER use `allkeys-lru` maxmemory-policy for a session store.**
   Silent eviction breaks sessions. Use `noeviction` and plan capacity
   so memory never fills.

7. **NEVER assume Memcached `AZMode=cross-az` provides failover.** It
   only distributes nodes across AZs — a failed node's data is LOST
   (no persistence, no replication). Only Redis has true Multi-AZ.

8. **NEVER add encryption in transit to an existing production Redis
   cluster without a maintenance window.** The rolling node replacement
   disconnects every client for 30-90 seconds per node. Enable at
   creation.

9. **NEVER plan to "switch to cluster mode later."** Migrating
   cluster-mode-disabled → cluster-mode-enabled requires a full cluster
   migration (new group + client repoint). For any workload whose write
   rate may grow, default to cluster mode enabled up front.

10. **NEVER size Redis nodes by spec-sheet memory.** Redis needs ~50%
    overhead for fork-on-BGSAVE, query buffers, copy-on-write. Plan
    for 50% of nominal; for Memcached, plan for 90%.

11. **NEVER set `snapshot-retention-limit` to 0 on a production Redis
    cluster.** Disabling snapshots means no point-in-time recovery.
    Use 7-35 days for production, 1-3 for dev.

12. **NEVER assume replicas add memory capacity.** Redis replicas hold
    a copy of the same data — they add READ capacity and availability,
    NOT storage. To add memory, add shards (cluster mode enabled) or
    larger nodes.

13. **NEVER mix maintenance and snapshot windows.** ElastiCache will
    reject overlapping windows, or worse, silently skip one. Set them
    at least 2 hours apart.

14. **NEVER use end-of-life node families** (`cache.t1`, `cache.m1`,
    `cache.m2`, `cache.r3` and older). Use Graviton (g-series:
    `cache.r6g`, `cache.m6g`, `cache.t4g`) for best price/performance.

## Output format

```text
CACHE: <cluster-or-replication-group-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Engine: redis | valkey | memcached
  [✓|✗] Cluster mode: ENABLED (<N> shards) | DISABLED (single primary)
  [✓|✗] Node type: cache.<family>.<size> (<memory> GiB nominal; <usable> GiB usable)
  [✓|✗] Replicas: <N> per shard | None (Memcached)
  [✓|✗] Multi-AZ with automatic failover: Enabled (replica in different AZ) | Disabled (Memcached N/A)
  [✓|✗] Subnet group: <name> (spans <N> AZs)
  [✓|✗] Security group: <sg-id> (inbound port 6379 Redis / 11211 Memcached from <app-sg>)
  [✓|✗] Encryption at rest: Enabled (customer CMK <key-arn> | AWS-managed) | Disabled (Memcached N/A)
  [✓|✗] Encryption in transit (TLS): Enabled | Disabled (Memcached N/A)
  [✓|✗] AUTH token: Enabled (16+ chars) | Disabled
  [✓|✗] Parameter group: <name> (maxmemory-policy=<policy>, timeout=<s>)
  [✓|✗] Snapshot retention: <N> days (window: <UTC-range>) | Disabled (Memcached N/A)
  [✓|✗] Maintenance window: <UTC-range>
  [✓|✗] Global Datastore: members in <regions> | Single-region
  [✓|✗] ElastiCache Serverless: Yes | No
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id <name>
  aws elasticache describe-cache-clusters --cache-cluster-id <name> --show-cache-node-info
  aws elasticache describe-cache-parameter-groups --cache-parameter-group-name <pg>
  aws ec2 describe-subnets --subnet-ids <subnet-ids>
  aws kms describe-key --key-id <cmk-id>
```

### Worked example — production Redis cluster mode enabled

```text
CACHE: prod-cache
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: redis
  [✓] Cluster mode: ENABLED (3 shards)
  [✓] Node type: cache.r6g.2xlarge (62.34 GiB nominal; 31.17 GiB usable per shard; 93.51 GiB total usable)
  [✓] Replicas: 1 per shard (3 total) — read scaling + Multi-AZ failover
  [✓] Multi-AZ with automatic failover: Enabled (replica in different AZ per shard)
  [✓] Subnet group: prod-cache-subnet (spans 3 AZs: us-east-1a/b/c)
  [✓] Security group: sg-cache123 (inbound port 6379 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-cache-kms)
  [✓] Encryption in transit (TLS): Enabled
  [✓] AUTH token: Enabled (24-char base64, stored in Secrets Manager)
  [✓] Parameter group: prod-redis-pg (maxmemory-policy=allkeys-lru, timeout=300, tcp-keepalive=60)
  [✓] Snapshot retention: 7 days (window: 03:00-05:00 UTC)
  [✓] Maintenance window: sun:05:00-sun:07:00
  [✓] Global Datastore: Single-region (us-east-1)
  [✓] ElastiCache Serverless: No
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id prod-cache
  aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
  aws elasticache describe-cache-parameter-groups --cache-parameter-group-name prod-redis-pg
  aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc
  aws kms describe-key --key-id alias/prod-cache-kms
```

## Decision tree: Redis cluster mode enabled vs disabled

```text
Is the workload write-heavy (> 50,000 writes/sec sustained)?
├── YES → Cluster mode ENABLED
│         (single primary cannot keep up; need horizontal write scaling)
└── NO → Is the write rate expected to grow beyond ~100k writes/sec?
    ├── YES → Cluster mode ENABLED (default for growing workloads)
    └── NO → Is multi-key transactional consistency (MULTI/EXEC across keys)
            required?
        ├── YES → Cluster mode DISABLED
        │         (all keys on one primary; transactions trivial)
        │         OR cluster mode ENABLED with hash-tag keys ({tag})
        └── NO → Is the workload stable and modest (< 50k writes/sec)?
            ├── YES → Cluster mode DISABLED (simpler client config)
            └── NO → Cluster mode ENABLED
```

## Decision tree: Redis vs Memcached

```text
Does the workload need ANY of:
  persistence, replication, failover, encryption, pub/sub,
  sorted sets, Lua, streams, Global Datastore?
├── YES → Redis OSS (or Valkey)
└── NO → Is genuinely simple, ephemeral, multi-threaded key-value cache
         acceptable WITH no failover, no persistence, no encryption?
    ├── YES → Memcached
    │         (multi-threading per node; LRU only; max 1 MB items)
    └── NO → Redis OSS  (default; the safest choice)
```

## Error handling

### Cluster name already exists (`ReplicationGroupAlreadyExists`)

```bash
aws elasticache describe-replication-groups --replication-group-id <name>
```

- If configuration matches intent: the cluster is already provisioned
  correctly. Skip to verification and emit READY_TO_DEPLOY.
- If configuration differs: decide whether to `modify-replication-group`
  (mutable settings: node type, parameter group, snapshots, maintenance
  window, security groups, AUTH token) or create a NEW cluster.
  Engine, cluster-mode, and at-rest-encryption CANNOT be changed
  post-creation — those require a new cluster + client repoint.

### Multi-AZ create fails (`CacheSubnetGroup does not span multiple AZs`)

The subnet group has all subnets in one AZ. Multi-AZ Redis requires
the subnet group to span at least 2 AZs.

**Fix:**

```bash
# Add a subnet in a different AZ to the subnet group
# (ElastiCache does not allow removing subnets, only adding)
aws elasticache modify-cache-subnet-group \
  --cache-subnet-group-name prod-cache-subnet \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc   # now spans >=2 AZs
```

**Verify** with `aws ec2 describe-subnets --subnet-ids ...` — confirm
distinct `AvailabilityZone` values.

### AUTH enable fails (`Encryption in transit is not enabled`)

AUTH requires TLS. Without `--transit-encryption-enabled=true`,
ElastiCache rejects `--auth-token`.

**Fix:** enable both together:

```bash
aws elasticache modify-replication-group \
  --replication-group-id prod-cache \
  --auth-token "$(aws secretsmanager get-secret-value ...)" \
  --transit-encryption-enabled true \
  --apply-immediately
```

Note: enabling TLS post-creation triggers a rolling node replacement
that disconnects every client for 30-90 seconds per node. Plan a
maintenance window.

### Snapshot restore creates cluster with wrong node type

Snapshot restore uses the node type specified at restore time, NOT the
source's node type. Verify `--cache-node-type` on the
`create-replication-group` call.

```bash
aws elasticache create-replication-group \
  --replication-group-id prod-cache-restored \
  --cache-node-type cache.r6g.2xlarge \   # specify explicitly
  --snapshot-arns arn:aws:elasticache:...:snapshot:prod-cache-snap
```

### Cluster stuck in `MODIFYING` after `apply-immediately`

A rolling node replacement on a large cluster (many shards + replicas)
can take 30+ minutes. Use `--apply-immediately` only for emergencies;
otherwise schedule modifications in the maintenance window.

```bash
aws elasticache describe-replication-groups --replication-group-id <name> \
  --query 'ReplicationGroups[0].Status'
# Wait for "available" before issuing the next modify.
```

### Cluster mode enabled → disabled migration is NOT a modify

There is NO `modify-replication-group` flag to switch cluster mode.
Migration requires:

1. Create a NEW replication group with `--num-node-groups 1`
   (cluster mode disabled equivalent) or no cluster config.
2. Repoint clients to the new endpoint.
3. Delete the old cluster.

NEVER attempt to "downgrade" cluster mode by reducing shard count to
1 — the cluster remains in cluster-mode-enabled state.

## Worked example — provisioned Redis cluster mode enabled with Multi-AZ

A production 3-shard Redis cluster with 1 replica per shard, Multi-AZ,
TLS + AUTH, customer CMK, snapshots, and CloudWatch alarms. This is
the canonical production pattern.

```bash
# 1. Create the subnet group (must span >=2 AZs)
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name prod-cache-subnet \
  --cache-subnet-group-description "Multi-AZ subnet group for prod cache" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc

# 2. Create the parameter group
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name prod-redis-pg \
  --cache-parameter-group-family redis6.x \
  --description "Production Redis parameter group"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name prod-redis-pg \
  --parameter-name-values \
    ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
    ParameterName=timeout,ParameterValue=300 \
    ParameterName=tcp-keepalive,ParameterValue=60

# 3. Generate AUTH token and store in Secrets Manager
AUTH_TOKEN=$(openssl rand -base64 24)
aws secretsmanager create-secret \
  --name prod-cache-auth-token \
  --secret-string "$AUTH_TOKEN"

# 4. Create the replication group with cluster mode enabled + Multi-AZ + TLS + AUTH
aws elasticache create-replication-group \
  --replication-group-id prod-cache \
  --replication-group-description "Production Redis cluster" \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --cache-parameter-group-name prod-redis-pg \
  --cache-subnet-group-name prod-cache-subnet \
  --security-group-ids sg-cache123 \
  --num-node-groups 3 \
  --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-cache-kms \
  --auth-token "$AUTH_TOKEN" \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --maintenance-window "sun:05:00-sun:07:00" \
  --tags Key=Environment,Value=production Key=Workload,Value=cache

# 5. Wait for the replication group to become available
aws elasticache wait replication-group-available --replication-group-id prod-cache

# 6. Verify
aws elasticache describe-replication-groups --replication-group-id prod-cache
aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
aws kms describe-key --key-id alias/prod-cache-kms

# 7. CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-cpu-high" \
  --namespace AWS/ElastiCache \
  --metric-name CPUUtilization \
  --dimensions Name=CacheClusterId,Value=prod-cache-0001 \
  --statistic Average --period 60 --threshold 90 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cache-alerts

aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-swap" \
  --namespace AWS/ElastiCache \
  --metric-name SwapUsage \
  --dimensions Name=CacheClusterId,Value=prod-cache-0001 \
  --statistic Average --period 60 --threshold 0 \
  --comparison-operator GreaterThan --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cache-alerts
```

The checklist for this cluster:

```text
CACHE: prod-cache
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: redis
  [✓] Cluster mode: ENABLED (3 shards)
  [✓] Node type: cache.r6g.2xlarge (62.34 GiB nominal; 31.17 GiB usable per shard; 93.51 GiB total usable)
  [✓] Replicas: 1 per shard (3 total) — Multi-AZ failover
  [✓] Multi-AZ with automatic failover: Enabled
  [✓] Subnet group: prod-cache-subnet (3 AZs)
  [✓] Security group: sg-cache123 (inbound 6379 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-cache-kms)
  [✓] Encryption in transit (TLS): Enabled
  [✓] AUTH token: Enabled (24-char base64 in Secrets Manager)
  [✓] Parameter group: prod-redis-pg (maxmemory-policy=allkeys-lru)
  [✓] Snapshot retention: 7 days (03:00-05:00 UTC)
  [✓] Maintenance window: sun:05:00-sun:07:00
  [✓] Global Datastore: Single-region
  [✓] ElastiCache Serverless: No
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id prod-cache
  aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
  aws elasticache describe-cache-parameter-groups --cache-parameter-group-name prod-redis-pg
  aws kms describe-key --key-id alias/prod-cache-kms
```

## Recent AWS features (2023-2026)

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

## Domain

AWS CloudOps / ElastiCache Provisioning & Cache Topology Design.

## AWS documentation

- **Amazon ElastiCache User Guide** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Welcome.html
- **Redis replication groups** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.html
- **Memcached clusters** — https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/WhatIs.html
- **ElastiCache cluster mode** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/ClusterMode.html
- **Encryption and AUTH** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/encryption.html
- **ElastiCache Serverless** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/serverless.html
- **Global Datastore** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Redis-Global-Datastore.html
- **Choosing a node type** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/nodes-select-size.html
