---
name: elasticache-cache-deployer
description: 'Provisions ElastiCache (Redis OSS / Memcached) clusters with production defaults: engine selection (Redis for persistence, clustering, pub/sub, TLS vs Memcached for simple key-value, multi-threaded, no persistence), cluster mode enabled vs disabled, node type sizing, Multi-AZ failover (Redis only), VPC-only networking, encryption at-rest + in-transit + AUTH (Redis only), subnet group, parameter group maxmemory-policy, snapshot retention, ElastiCache Serverless, Global Datastore. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an ElastiCache cluster, choosing between Redis and Memcached, designing a Multi-AZ Redis failover topology, sizing cache nodes, or generating provisioning CLI commands / IaC templates. Triggers: create ElastiCache, provision Redis, provision Memcached, ElastiCache cluster mode, Redis replication group, Global Datastore, ElastiCache Serverless, cache node type sizing.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with elasticache, ec2, kms, and iam access. Works with Terraform aws_elasticache_cluster / aws_elasticache_replication_group resources and CloudFormation AWS::ElastiCache::* templates.'
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
  tags: aws, elasticache, redis, memcached, cloudops, deploy, databases, cache, provisioning, replication-group, multi-az, encryption, global-datastore, serverless
  dependencies: aws-orchestrator
  keywords: aws, elasticache, redis, memcached, cloudops, deploy, provisioning, cache, replication group, cluster mode, multi-az, failover, encryption at rest, encryption in transit, auth token, tls, subnet group, parameter group, maxmemory-policy, allkeys-lru, noeviction, snapshot, backup, global datastore, elasticache serverless, outposts
  when_to_use: Invoke when the user wants to create a new ElastiCache cluster (Redis or Memcached), design a Multi-AZ Redis failover topology, choose between Redis and Memcached, size cache nodes for a workload, harden an existing cluster before production (TLS, AUTH, encryption at rest), set up a Global Datastore for cross-region replication, provision an ElastiCache Serverless cache, or generate provisioning CLI commands / IaC templates. Do NOT invoke for auditing existing cluster posture (use elasticache-cluster-auditor), or for non-ElastiCache caches (DynamoDB DAX, MemoryDB for Redis, self-managed Redis on EC2).
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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Mindset misconceptions".
> Load when: you need the full argument behind the engine/cluster-mode/Multi-AZ misconceptions.

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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Reasoning framework".
> Load when: sequencing engine, cluster mode, encryption, subnet group, node type, and parameter decisions.

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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Configuration dependency graph".
> Load when: the immutability analysis and cross-dependency gotchas behind the table.

## Expert heuristic: effective memory calculator

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Expert heuristic: effective memory calculator".
> Load when: sizing real usable memory (Redis 50% rule vs Memcached 90%).
numbers.

## Expert heuristic: cluster mode shard count estimator

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Expert heuristic: cluster mode shard count estimator".
> Load when: computing shard count from sustained write rate (60% rule) and scenario shapes.

## Expert heuristic: failover promotion semantics

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Expert heuristic: failover promotion semantics".
> Load when: reasoning about promotion time, data-loss windows, and Memcached cross-az.

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

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 1".
> Load when: walking the Redis-vs-Memcached engine decision. The condensed tree lives in § Decision tree: Redis vs Memcached.

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 1".
> Load when: comparing engines feature-by-feature or reviewing the Memcached migration mistake.

### Step 2 — Cluster mode decision (immutable for write scaling — decide BEFORE create)

For Redis, cluster mode determines whether writes scale horizontally.
This is the second-highest-impact decision and is **effectively
immutable** without a full cluster migration.

**Decision tree:**

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 2".
> Load when: walking the cluster-mode decision incl. MULTI/EXEC. The condensed tree lives in § Decision tree: Redis cluster mode enabled vs disabled.

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 2".
> Load when: hash slots, CROSSSLOT limits, or the disabled→enabled migration mistake.

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

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 3".
> Load when: picking node families/sizes and applying the 50%/90% memory rules.

### Step 4 — Multi-AZ + automatic failover (Redis only)

Multi-AZ with automatic failover is the primary resilience control for
Redis. Memcached does NOT support Multi-AZ.

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 4".
> Load when: checking the five gating requirements for Multi-AZ failover.

> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 4".
> Load when: promotion flow, endpoint behavior, or AZ topology examples.

### Step 5 — Network + security (VPC, subnet group, security group)

ElastiCache is **VPC-only** — there is no public IP option (unlike
RDS). All clusters live inside a VPC.

**Subnet group creation:**

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 5".
> Load when: creating the multi-AZ cache subnet group.

Verify the subnets span >=2 AZs:

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 5".
> Load when: verifying the subnet group spans >=2 AZs before create.

**Security group rules:**

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 5".
> Load when: opening port 6379/11211 inbound from the application SG.

**NEVER** open the cache port to `0.0.0.0/0` — even with AUTH, this
exposes the cluster to internet scanning. Always scope inbound to the
application's SG.

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 5".
> Load when: the cluster is unreachable or the SG was not attached at creation.

### Step 6 — Encryption + AUTH + TLS (Redis only)

Encryption and AUTH are Redis-only. Memcached has NO encryption
support — if compliance requires encryption, the answer is Redis.

**Encryption at rest:**
> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 6".
> Load when: using a customer CMK or adding encryption to an existing cluster.

**Encryption in transit (TLS):**
> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 6".
> Load when: enabling TLS post-creation or reasoning about rolling replacement.

**AUTH token:**
> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 6".
> Load when: generating and applying the Redis AUTH token.

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 6".
> Load when: using ACL user groups or pairing AUTH with TLS.

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
> **Moved verbatim** → [references/engine-and-topology.md](references/engine-and-topology.md) § "Step 7".
> Load when: mapping cache vs store vs mix workloads to a policy.
  with TTL on disposable keys.

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 7".
> Load when: setting non-maxmemory parameters for Redis or Memcached.

### Step 8 — Snapshots / backups (Redis only)

Redis supports automated snapshots (RDB files) for point-in-time
recovery. Memcached does NOT support snapshots.

**Enable automated snapshots at creation:**

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 8".
> Load when: enabling snapshot retention/window at creation.

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 8".
> Load when: choosing retention days and windows.

**Manual snapshot:**

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 8".
> Load when: taking an on-demand snapshot.

**Restore from snapshot creates a NEW cluster:**

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 8".
> Load when: restoring a replication group from a snapshot ARN.

**Common mistake:** setting retention limit to 0 (snapshots disabled).
For production Redis, set retention 7-35 days. For dev, 1-3 days is fine.

### Step 9 — ElastiCache Serverless / Global Datastore (latest features)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 9".
> Load when: provisioning serverless, Global Datastore, or Outposts topologies.

### Step 10 — CloudWatch alarms (operational hygiene)

Recommended CloudWatch alarms on every production cluster:

> **Moved verbatim** → [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) § "Step 10".
> Load when: creating CPU/swap/eviction/replication-lag alarms.

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

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Error handling".
> Load when: an API error fires, a cluster is stuck MODIFYING, or a migration is needed.

## Worked example — provisioned Redis cluster mode enabled with Multi-AZ

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example".
> Load when: emitting the full CLI sequence and checklist for the canonical production pattern.

## Recent AWS features (2023-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features 2023-2026".
> Load when: deciding on Valkey, Graviton nodes, Redis 7.x, or serverless.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — canonical production Redis cluster-mode-enabled CLI sequence + checklist
- [references/error-handling.md](references/error-handling.md) — API error triage: name exists, subnet single-AZ, AUTH/TLS, snapshot restore, MODIFYING stuck, cluster-mode migration
- [references/advanced-patterns.md](references/advanced-patterns.md) — reasoning framework, dependency-graph deep dive, misconceptions, ACL detail, Serverless/Global Datastore/Outposts, recent AWS features
- [references/engine-and-topology.md](references/engine-and-topology.md) — engine math, shard estimator, failover semantics, feature matrix, sizing rules (extended with SKILL.md detail)
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — copy-pasteable CLI sequence (extended with subnet group, SG, snapshot, restore, alarms, parameters)

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
