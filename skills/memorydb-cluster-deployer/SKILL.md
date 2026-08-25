---
name: memorydb-cluster-deployer
description: 'Provisions Amazon MemoryDB for Redis clusters with production defaults: cluster creation (node type, shard count, replica count), subnets (subnet group across AZs), security groups, encryption (TLS at-rest + in-transit — both on by default), ACLs (user-based access control via access lists), snapshots (automated + manual), multi-AZ (cluster mode with shard-level failover), data tiering (low-cost SSD tier for infrequently-accessed data), and multi- Region. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a MemoryDB cluster, sizing nodes and shards, designing a Multi-AZ Redis topology, hardening TLS/ACLs, or enabling data tiering / multi-Region. Triggers: create MemoryDB, provision MemoryDB, MemoryDB cluster, MemoryDB Redis, MemoryDB ACL, MemoryDB multi-AZ, MemoryDB data tiering, MemoryDB multi-Region, MemoryDB snapshots, MemoryDB TLS.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with memorydb, ec2, kms, and iam access. Works with Terraform aws_memorydb_cluster / aws_memorydb_subnet_group resources and CloudFormation AWS::MemoryDB::Cluster / AWS::MemoryDB::SubnetGroup templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, memorydb, redis, cloudops, deploy, databases, in-memory, provisioning, cluster-mode, multi-az, encryption, acl, data-tiering, multi-region
  dependencies: aws-orchestrator
  keywords: aws, memorydb, redis, cloudops, deploy, provisioning, in-memory database, cluster mode, multi-az, failover, encryption at rest, encryption in transit, tls, acl, access list, subnet group, parameter group, snapshot, data tiering, multi-region, shard count, replica count
  when_to_use: Invoke when the user wants to create a new Amazon MemoryDB for Redis cluster (durable in-memory database), size nodes / shards / replicas, design a Multi-AZ Redis cluster-mode topology with shard-level failover, harden TLS + ACLs, enable data tiering (SSD-backed cost optimization), enable multi-Region replication, configure snapshots, or generate provisioning CLI commands / IaC templates. Do NOT invoke for ElastiCache (cache, not durable database — use elasticache-cache-deployer), for self-managed Redis on EC2, or for non-Redis databases.
---

# MemoryDB Cluster Deployer

An AWS CloudOps agent skill that provisions Amazon MemoryDB for Redis
clusters (durable in-memory database) with correct defaults. The skill
walks the operator through a provisioning procedure, captures the
operator's topology, security, and capacity decisions, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create MemoryDB, provision MemoryDB, MemoryDB cluster, MemoryDB Redis,
MemoryDB ACL, MemoryDB access list, MemoryDB Multi-AZ, MemoryDB data
tiering, MemoryDB multi-Region, MemoryDB snapshots, MemoryDB TLS,
MemoryDB subnet group, MemoryDB shard count, MemoryDB replica count,
db.r6g.large, db.r6g.24xlarge.

## STRICT output contract

When this skill is invoked with a MemoryDB-provisioning request
(cluster name, node type, workload shape, region, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `MEMORYDB:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — MemoryDB vs ElastiCache | Boundary call (durable DB vs cache) |
| Step 2 — Node type + shard count + replica count | Sizing capacity + topology |
| Step 3 — Multi-AZ with shard-level failover | Production topology |
| Step 4 — Network + security (VPC, subnet group, SG) | VPC wiring |
| Step 5 — Encryption (TLS at-rest + in-transit, on by default) | Security bundle |
| Step 6 — ACLs (user-based access control) | Auth model |
| Step 7 — Parameter groups (maxmemory-policy) | Eviction semantics |
| Step 8 — Snapshots (automated + manual) | Point-in-time recovery |
| Step 9 — Data tiering (SSD cost optimization) | Large-data-set cost control |
| Step 10 — Multi-Region / recent features | Cross-region, latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/topology-and-tiering.md | Shard/replica math, tiering detail |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

**One-line takeaway:** MemoryDB is a durable in-memory DATABASE
(with Multi-AZ transactional durability), not a cache. The
distinction drives every default: TLS at-rest + in-transit are ON by
default, ACLs are REQUIRED (no open access), snapshots are
recommended, and the cluster topology must plan for durability from
the start.

→ Extended Mindset rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)

MemoryDB configurations are NOT independent. Many are immutable after
creation, others silently downgrade. Use this graph both to sequence
provisioning and to debug "why can't I add this?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Engine version | none — `create` argument | engine upgrades apply in maintenance window; rolling with brief endpoint flapping | Redis 6.x ACLs, 7.x sharded pub/sub |
| Node type | none — `create` argument | changeable via `update-cluster` with rolling shard replacement | memory budget, CPU, network |
| Shard count (num-shards) | none — `create` argument | changeable via `update-cluster` with resharding (online but non-trivial) | horizontal write scaling, up to 500 shards |
| Replicas per shard | none — `create` argument | changeable via `update-cluster`; adds/removes replicas | read scaling + Multi-AZ failover |
| Multi-AZ with shard-level failover | `--enable-failover` + >=1 replica per shard + subnet group spanning >=2 AZs | failover promoted only if replica is in a different AZ than the shard's primary | per-shard primary-failure resilience |
| TLS at-rest | ON by default; disable via `--no-tls` (NOT recommended) | **CANNOT be added post-creation** if disabled without a new cluster | compliance (PCI-DSS, HIPAA) |
| TLS in-transit | ON by default; disable via `--no-tls` (NOT recommended) | can be disabled via `update-cluster` with rolling shard replacement; re-enabling has caveats | TLS-only clients, sniffing defense |
| ACL (user-based access control) | REQUIRED — cluster requires at least one ACL at creation | default `open-access` ACL allows unrestricted access; NEVER use in production | named users with scoped permissions |
| Subnet group | VPC + >=1 subnet; >=2 AZs for Multi-AZ | subnets CANNOT be removed once added; only added | VPC-only addressing |
| Security group | VPC | port 6379 inbound from application SG | network isolation |
| Parameter group (family) | none — `create` argument | changes apply on next reboot | maxmemory-policy, timeout, reserved-memory |
| Snapshot (automated) | `--snapshot-retention-limit > 0` at creation | restore creates a NEW cluster; snapshot is cluster-scoped | point-in-time recovery |
| Data tiering | `--data-tiering=true` at creation + supported node type (r6gd family) | **CANNOT be enabled/disabled post-creation** — requires a new cluster | SSD-backed cold tier, lower cost for large datasets |
| Multi-Region | primary cluster + Multi-Region engine enabled + each region's cluster already provisioned | replication is async; write conflicts resolve by last-writer-wins | cross-region low-latency reads, DR |

**The immutable rows are the ones a baseline model misses.** TLS
at-rest (if disabled), data tiering, and the VPC/subnet placement
are decided at creation time. The procedure below forces an explicit
decision on each before the `create-cluster` call.

**Cross-dependency gotchas:**
- Disabling TLS at creation and re-enabling later is NOT supported
  cleanly — MemoryDB's TLS setting is set at creation. Re-enabling
  via update has caveats and may require a new cluster. Leave TLS ON
  (the default).
- ACLs are cluster-scoped. A cluster has exactly one ACL attached at
  a time; changing the ACL applies to all connections immediately.
- Data tiering is a one-way door: a cluster created WITHOUT tiering
  CANNOT be tiered later without creating a new cluster and migrating.
- Multi-AZ failover is per-SHARD, not per-cluster. A 5-shard cluster
  can have up to 5 simultaneous shard failovers during an AZ event.

## Expert heuristic: effective memory calculator

→ Expert-heuristic deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: shard count estimator

→ Expert-heuristic deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: failover promotion semantics

→ Expert-heuristic deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with MemoryDB access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | MemoryDB clusters and subnet groups are region-scoped | `aws configure get region` |
| VPC ID + at least 2 subnets in different AZs (for Multi-AZ) | MemoryDB is VPC-only; Multi-AZ requires multi-AZ subnet group | `aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc>"` — confirm >=2 distinct `AvailabilityZone` values |
| Cluster name unique in this region | Names are region-unique | `aws memorydb describe-clusters --cluster-name <name>` returns `ClusterNotFound` |
| ACL defined (user-based access control) | MemoryDB REQUIRES an ACL; the default `open-access` is NOT for production | `aws memorydb describe-acls --acl-name <acl>`; create a named ACL with least-privilege users |
| Security group with port 6379 inbound from application SG | Wrong port = silent connectivity failure; MemoryDB listens on 6379 | `aws ec2 describe-security-groups --group-ids <sg>` — verify inbound rule on 6379 |
| Workload description (data size, write rate, hot/cold pattern) | Drives node type, shard count, replica count, data-tiering decisions | Captured in the prompt or follow-up question |
| Engine choice (MemoryDB vs ElastiCache) | MemoryDB is a durable database; ElastiCache is a cache. Different price/perf | If the workload tolerates data loss on failover, ElastiCache is cheaper |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — MemoryDB vs ElastiCache (boundary call)

The single highest-impact MemoryDB decision is whether to use
MemoryDB or ElastiCache. They are both managed Redis, but they serve
different use cases.

**Decision tree:**

```text
Does the workload require durability (committed data MUST survive
node/AZ failure)?
├── YES → MemoryDB  (durable in-memory database)
│         Multi-AZ transaction log; zero committed-transaction loss
│         on failover. Higher cost per node.
└── NO  → Is the data disposable (cache-miss is acceptable)?
    ├── YES → ElastiCache  (NOT this skill — use elasticache-cache-deployer)
    │         No transaction log; failover may lose in-flight writes.
    │         Lower cost per node.
    └── NO  → MemoryDB  (the safest choice)
```

**Feature comparison:**

| Feature | MemoryDB | ElastiCache (Redis) |
|---|---|---|
| Use case | Durable in-memory DATABASE | In-memory CACHE |
| Multi-AZ durability | Transaction log (zero committed loss) | Async replication (may lose in-flight writes) |
| TLS at-rest / in-transit | ON by default | Optional (set at creation) |
| ACLs (user-based auth) | REQUIRED | Optional (AUTH token or ACL) |
| Snapshots | YES (automated + manual) | YES (Redis only) |
| Data tiering (SSD) | YES (r6gd family) | NO |
| Multi-Region | YES (Multi-Region engine) | YES (Global Datastore) |
| Pricing | Higher (durability overhead) | Lower |

**Common mistake:** picking ElastiCache for a workload that needs
durability, then losing data on failover. MemoryDB's transaction log
is the load-bearing durability control. If the data MUST survive,
use MemoryDB.

## Step 2 — Node type + shard count + replica count

MemoryDB offers `db.r6g` and `db.r6gd` (data-tiering) families, plus
`db.r7g` (latest Graviton). Avoid `t-series` burstable for production.

**Node family selection:**

| Family | Optimized for | Use when |
|---|---|---|
| `db.r6g.large` ... `.24xlarge` | Memory, Graviton | General-purpose MemoryDB; production |
| `db.r6gd.large` ... `.24xlarge` | Memory + SSD tiering | Large datasets with hot/cold access pattern (cost optimization) |
| `db.r7g.large` ... `.24xlarge` | Memory, Graviton (latest) | New clusters; ~10% better perf over r6g |

**Sizing rules:**
- Plan for 50% memory utilization (see Expert heuristic above). 50%
  of nominal is the operating budget.
- For data tiering, the SSD tier adds ~2x the node's memory in SSD
  capacity, but cold-tier access is 100x-1000x slower.
- Replicas do NOT add usable memory — they hold a copy of the same
  data. To add memory, add shards.
- For durability, ALWAYS >=1 replica per shard (Multi-AZ failover).

**Common scenarios:**
- **Low write, high read session store** (1k writes/sec, 50k
  reads/sec): 2 shards × 3 replicas each.
- **High-write real-time leaderboard** (300k writes/sec): 5 shards ×
  1 replica each.
- **Large dataset, cost-optimized** (1 TB, hot/cold split):
  db.r6gd.24xlarge with data tiering, 3 shards.

## Step 3 — Multi-AZ with shard-level failover

Multi-AZ with shard-level failover is the primary resilience and
durability control for MemoryDB.

**Requirements:**
- `--enable-failover` (or `automatic-failover-enabled` in Terraform).
- At least 1 replica per shard in a DIFFERENT AZ than the shard's
  primary.
- Subnet group spanning at least 2 AZs.

**Behavior on shard-primary failure:**
- MemoryDB detects the primary failure (health check).
- A replica in a different AZ is promoted to primary for that shard
  (10-30 seconds).
- The cluster configuration endpoint stays stable; clients route via
  MOVED/ASK redirection.
- Data loss window: zero committed transactions (Multi-AZ transaction
  log). This is the durability guarantee that distinguishes MemoryDB
  from ElastiCache.

**Common mistake:** subnet group with only one AZ. Multi-AZ fails
silently — MemoryDB cannot place the replica in a different AZ.
Verify subnet group spans >=2 AZs before `create-cluster`.

## Step 4 — Network + security (VPC, subnet group, security group)

MemoryDB is **VPC-only** — there is no public IP option (like
ElastiCache). All clusters live inside a VPC.

→ Subnet-group, AZ-verification, and security-group CLI moved verbatim to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

**NEVER** open port 6379 to `0.0.0.0/0` — even with TLS and ACLs,
this exposes the cluster to internet scanning. Always scope inbound
to the application's SG.

## Step 5 — Encryption (TLS at-rest + in-transit, on by default)

MemoryDB enables TLS at-rest AND in-transit by default. This is a
deliberate design choice reflecting that MemoryDB is a database, not
a cache.

- TLS at-rest: ON by default. Uses AWS-managed KMS key by default;
  customer CMK via `--kms-key-id` (optional).
- TLS in-transit: ON by default. Uses AWS-generated certs.
- **Disabling TLS is NOT recommended.** If disabled at creation, it
  CANNOT be cleanly re-enabled later without caveats. Leave TLS ON.
- ACLs require TLS — they use the same auth pathway.

**Common mistake:** planning to "disable TLS now, enable later."
MemoryDB's TLS setting is set at creation. Re-enabling via update has
caveats and may require a new cluster. Leave TLS ON.

## Step 6 — ACLs (user-based access control)

MemoryDB REQUIRES an ACL to control access — there is no "open" mode
(unlike ElastiCache). The default `open-access` ACL allows
unrestricted access and should NEVER be used in production.

→ ACL user/ACL creation CLI moved verbatim to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

**Attach the ACL at cluster creation via `--acl-name`.**

**Access-string syntax** (Redis ACL format): `on` enables the user;
`~*` allows all keys (use `~prefix:*` to scope); `+@all` allows all
commands; `-@all +@read` allows read-only; `+@write +@read` allows
read+write.

**Common mistake:** using the default `open-access` ACL in
production. Anyone with network access to the cluster can read/write
all data. Create a named ACL with scoped users.

## Step 7 — Parameter groups (maxmemory-policy)

Parameter groups control MemoryDB runtime behavior. Changes apply on
next reboot (not immediate).

**maxmemory-policy decision (load-bearing):**

| Policy | Behavior when memory fills | Use when |
|---|---|---|
| `volatile-lru` | Evict LRU among keys with TTL only | Mixed store + cache — DEFAULT for MemoryDB |
| `allkeys-lru` | Evict least-recently-used key | Pure cache semantics (data disposable) |
| `noeviction` | Return OOM error on writes | Strict durable store (NEVER silently evict) |
| `volatile-ttl` | Evict closest-to-expiry TTL'd key | Priority-based (soon-to-expire first) |

**Decision rule for MemoryDB (durable database):**
- Default is `volatile-lru` — evicts only TTL'd keys, preserving
  persistent data. Safe default for a database.
- For a pure-cache use case: `allkeys-lru`.
- For a strict store (no eviction EVER): `noeviction`. Plan capacity
  so memory never fills.

## Step 8 — Snapshots (automated + manual)

MemoryDB supports automated snapshots (RDB files) for point-in-time
recovery.

→ Snapshot enable, manual-snapshot, and restore CLI moved verbatim to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

**Common mistake:** setting retention limit to 0 (snapshots
disabled). For production MemoryDB, set retention 7-35 days.

## Step 9 — Data tiering (SSD cost optimization)

Data tiering (MemoryDB, 2022-2023) moves infrequently-accessed keys
to an SSD tier, lowering cost for large datasets.

**Requirements:**
- `--data-tiering=true` at creation.
- Supported node type: `db.r6gd` family only (not `db.r6g`).
- **CANNOT be enabled or disabled post-creation** — a one-way door.

**Behavior:**
- Hot keys stay in memory (sub-ms latency).
- Cold keys (least-recently-used) move to SSD (100x-1000x the latency
  of in-memory).
- The SSD tier is ~2x the node's memory capacity.

**When to use:** large dataset (hundreds of GB to TB) with a clear
hot/cold access pattern; cost optimization where cold-key latency is
acceptable (analytics, batch, rarely-accessed user data).

**When NOT to use:** uniform access patterns (no hot/cold split);
latency-sensitive workloads where all keys must be sub-ms; small
datasets that fit in memory without tiering.

**Common mistake:** enabling data tiering for a uniform-access
workload. All keys hit the SSD tier eventually, and latency degrades.
Use tiering only for workloads with a clear hot/cold split.

## Step 10 — Multi-Region / recent features

→ Multi-Region detail and recent AWS features moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER use the default `open-access` ACL in production.** The
   default ACL allows unrestricted read/write access. Create a named
   ACL with least-privilege users (read-only for analytics, read-write
   for the application).

2. **NEVER disable TLS at creation planning to re-enable later.**
   MemoryDB's TLS setting is set at creation. Re-enabling via update
   has caveats and may require a new cluster. Leave TLS ON (the
   default).

3. **NEVER use a single-AZ subnet group for Multi-AZ MemoryDB.**
   Multi-AZ requires the promoted replica in a different AZ than the
   shard's primary. Verify `aws ec2 describe-subnets` shows >=2
   distinct AZs in the subnet group before `create-cluster`.

4. **NEVER open port 6379 to `0.0.0.0/0`.** Even with TLS and ACLs,
   internet exposure invites scanning and exploit attempts. Always
   scope inbound to the application's SG.

5. **NEVER enable data tiering for a uniform-access workload.**
   Tiered keys have 100x-1000x the latency of in-memory keys. Use
   tiering only for workloads with a clear hot/cold access pattern.

6. **NEVER run a MemoryDB cluster with 0 replicas per shard in
   production.** There is no failover target and the shard loses
   durability on primary failure. The minimum production topology is
   1 replica per shard in a different AZ.

7. **NEVER pick ElastiCache for a workload that requires durability.**
   ElastiCache may lose in-flight writes on failover (asynchronous
   replication). MemoryDB's Multi-AZ transaction log guarantees zero
   committed-transaction loss. Pick MemoryDB if the data MUST survive.

8. **NEVER size MemoryDB nodes by spec-sheet memory.** Plan for 50%
   usable; the rest is overhead (fork-on-snapshot, query buffers,
   copy-on-write).

9. **NEVER assume data tiering can be enabled/disabled later.** It is
   a one-way door set at creation. A non-tiered cluster CANNOT be
   tiered without creating a new cluster and migrating.

10. **NEVER use `noeviction` maxmemory-policy for a cache-like
    workload.** `noeviction` returns OOM on writes when memory fills.
    Use `volatile-lru` (default; evicts only TTL'd keys) or
    `allkeys-lru` (pure cache).

11. **NEVER set `snapshot-retention-limit` to 0 on a production
    MemoryDB cluster.** Disabling snapshots means no point-in-time
    recovery. Use 7-35 days for production.

12. **NEVER assume replicas add memory capacity.** MemoryDB replicas
    hold a copy of the same data — they add READ capacity and
    availability, NOT storage. To add memory, add shards.

## Output format

```text
MEMORYDB: <cluster-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Service: MemoryDB (durable in-memory database, NOT ElastiCache cache)
  [✓|✗] Engine version: <version>
  [✓|✗] Node type: db.<family>.<size> (<memory> GiB nominal; <usable> GiB usable per shard)
  [✓|✗] Shard count: <N> (<total_usable> GiB total usable)
  [✓|✗] Replicas per shard: <N> (Multi-AZ failover)
  [✓|✗] Multi-AZ with shard-level failover: Enabled | Disabled (NO failover)
  [✓|✗] Subnet group: <name> (spans <N> AZs)
  [✓|✗] Security group: <sg-id> (inbound port 6379 from <app-sg>)
  [✓|✗] TLS at rest: Enabled (AWS-managed | customer CMK <key-arn>)
  [✓|✗] TLS in transit: Enabled
  [✓|✗] ACL: <acl-name> (users: <user-list>; NOT open-access)
  [✓|✗] Parameter group: <name> (maxmemory-policy=<policy>, timeout=<s>)
  [✓|✗] Snapshot retention: <N> days (window: <UTC-range>) | Disabled
  [✓|✗] Maintenance window: <UTC-range>
  [✓|✗] Data tiering: Enabled (db.r6gd.<size>, <ssd> GiB SSD tier) | Disabled
  [✓|✗] Multi-Region: members in <regions> | Single-region
VERIFICATION_COMMANDS:
  aws memorydb describe-clusters --cluster-name <name> --show-shard-node-info
  aws memorydb describe-acls --acl-name <acl-name>
  aws memorydb describe-subnet-groups --subnet-group-name <subnet-group>
  aws ec2 describe-subnets --subnet-ids <subnet-ids>
  aws kms describe-key --key-id <cmk-id>
```

### Worked example — production MemoryDB with Multi-AZ + data tiering

```text
MEMORYDB: prod-memorydb
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service: MemoryDB (durable in-memory database, NOT ElastiCache cache)
  [✓] Engine version: 7.0
  [✓] Node type: db.r6gd.24xlarge (612.30 GiB nominal; 306.15 GiB usable per shard)
  [✓] Shard count: 3 (918.45 GiB in-memory usable + 3304.8 GiB SSD tier)
  [✓] Replicas per shard: 1 (Multi-AZ failover)
  [✓] Multi-AZ with shard-level failover: Enabled
  [✓] Subnet group: prod-memorydb-subnet (spans 3 AZs)
  [✓] Security group: sg-memorydb123 (inbound port 6379 from sg-app456)
  [✓] TLS at rest: Enabled (AWS-managed KMS)
  [✓] TLS in transit: Enabled
  [✓] ACL: prod-acl (users: app-rw, analytics-ro; NOT open-access)
  [✓] Parameter group: default.memorydb-redis7 (maxmemory-policy=volatile-lru)
  [✓] Snapshot retention: 7 days (window: 03:00-05:00 UTC)
  [✓] Maintenance window: sun:05:00-sun:07:00
  [✓] Data tiering: Enabled (db.r6gd.24xlarge, ~1224 GiB SSD tier per node)
  [✓] Multi-Region: Single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws memorydb describe-clusters --cluster-name prod-memorydb --show-shard-node-info
  aws memorydb describe-acls --acl-name prod-acl
  aws memorydb describe-subnet-groups --subnet-group-name prod-memorydb-subnet
  aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc
```

## Error handling

→ Error-handling runbooks moved verbatim to [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — expert-heuristic deep dives (memory calculator, shard estimator, failover semantics), extended Mindset, Multi-Region/recent features
- [references/error-handling.md](references/error-handling.md) — error-handling runbooks (ClusterAlreadyExists, Multi-AZ subnet span, NOAUTH, DataTiering)
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — copy-pasteable CLI sequence — extended with Steps 4/6/8 CLI from SKILL.md
- [references/topology-and-tiering.md](references/topology-and-tiering.md) — shard/replica math, tiering detail, sizing pitfalls

## Domain

AWS CloudOps / Amazon MemoryDB Provisioning & Redis Cluster Topology
Design.

## AWS documentation

- **Amazon MemoryDB User Guide** — https://docs.aws.amazon.com/memorydb/latest/devguide/what-is-memorydb-for-redis.html
- **MemoryDB node types** — https://docs.aws.amazon.com/memorydb/latest/devguide/nodes.select-size.html
- **MemoryDB TLS encryption** — https://docs.aws.amazon.com/memorydb/latest/devguide/encryption.html
- **MemoryDB ACLs** — https://docs.aws.amazon.com/memorydb/latest/devguide/clusters.acls.html
- **MemoryDB data tiering** — https://docs.aws.amazon.com/memorydb/latest/devguide/data-tiering.html
- **MemoryDB Multi-Region** — https://docs.aws.amazon.com/memorydb/latest/devguide/multi-region-global.html
- **MemoryDB snapshots** — https://docs.aws.amazon.com/memorydb/latest/devguide/snapshots.html
- **MemoryDB vs ElastiCache** — https://docs.aws.amazon.com/memorydb/latest/devguide/memorydb-vs-elasticache.html
