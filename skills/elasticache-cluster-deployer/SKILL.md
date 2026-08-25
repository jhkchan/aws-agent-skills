---
name: elasticache-cluster-deployer
description: 'Provisions Amazon ElastiCache clusters with production defaults: Redis OSS self-designed clusters vs cluster mode enabled (shards and replicas), Memcached clusters, replication groups (primary + read replicas), multi-AZ with automatic failover, node type sizing, subnet group creation, security groups, parameter groups, at-rest encryption (KMS), in-transit encryption (TLS), Redis AUTH tokens, Redis shard/slot mapping, backup and snapshot management (automated + manual), Global Datastore (cross-region replication), auto-scaling, and online cluster resizing (scale up/down with use-online-resharding). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an ElastiCache cluster, setting up Redis replication groups, enabling multi-AZ. Triggers: create elasticache cluster, redis replication group, cluster mode enabled, elasticache multi-az failover, elasticache encryption kms tls, redis auth token, elasticache global datastore, online resharding, elasticache auto scaling, memcached...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with elasticache access. Works with Terraform aws_elasticache_replication_group / aws_elasticache_cluster / aws_elasticache_subnet_group resources and CloudFormation AWS::ElastiCache::ReplicationGroup / AWS::ElastiCache::CacheCluster / AWS::ElastiCache::SubnetGroup templates.'
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
  tags: aws, elasticache, redis, memcached, cloudops, deploy, databases, provisioning, replication-group, cluster-mode, multi-az, encryption, global-datastore
  dependencies: aws-orchestrator
  keywords: aws, elasticache, redis, memcached, cloudops, deploy, provisioning, replication group, cluster mode, multi-az, failover, encryption, kms, tls, auth token, global datastore, online resharding, auto scaling
  when_to_use: Invoke when the user wants to create an Amazon ElastiCache cluster (Redis OSS or Memcached), configure a Redis replication group with multi-AZ automatic failover, enable cluster mode with shards and read replicas, configure at-rest encryption (KMS) or in-transit encryption (TLS), set Redis AUTH tokens, create a Global Datastore for cross-region replication, perform online cluster resizing, or configure ElastiCache auto-scaling. Do NOT invoke for Amazon MemoryDB for Redis, Amazon DynamoDB, or self-managed Redis/Memcached on EC2.
---

# ElastiCache Cluster Deployer

An AWS CloudOps agent skill that provisions Amazon ElastiCache clusters
with correct defaults. The skill walks the operator through Redis OSS
cluster mode vs non-cluster mode, Memcached topology, replication groups,
multi-AZ automatic failover, node type sizing, subnet groups, security
groups, parameter groups, encryption, AUTH tokens, shard/slot mapping,
backup management, Global Datastore, auto-scaling, and online cluster
resizing — then emits a READY_TO_DEPLOY checklist with verification
commands.

## Activation keywords

create ElastiCache cluster, Redis replication group, cluster mode
enabled, ElastiCache multi-AZ failover, ElastiCache encryption KMS TLS,
Redis AUTH token, ElastiCache Global Datastore, online resharding,
ElastiCache auto scaling, Memcached cluster.

## STRICT output contract

When this skill is invoked with an ElastiCache-provisioning request
(create a cluster, configure a replication group, enable multi-AZ
failover, set up encryption, create a Global Datastore, scale a cluster
online, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `ELASTICACHE_CLUSTER:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` when any CHECKLIST item is
   `[✗]`.** If even one prerequisite is unmet, the verdict MUST be
   `PREREQUISITES_MISSING`. A mixed-verdict block is a contract
   violation.

2. **NEVER omit the `ELASTICACHE_CLUSTER:` header line.** It is the
   parse anchor for downstream provisioning pipelines. Substituting a
   markdown heading (`## ElastiCache`) or a lowercase variant breaks
   automation silently.

3. **NEVER mark encryption as "TBD", "optional", or "post-creation."**
   At-rest (KMS) and in-transit (TLS) encryption are creation-time-only
   for Redis replication groups — they CANNOT be toggled on after the
   cluster exists. The CHECKLIST MUST show an explicit encryption
   decision (`Enabled` or `Disabled`), never a deferred one.

4. **NEVER show multi-AZ failover as `Enabled` when
   `replicas-per-node-group` is 0.** Multi-AZ automatic failover requires
   at least one replica per shard as a promotion target. `Multi-AZ:
   Enabled` with zero replicas is a silent no-op — failover has no
   target to promote.

5. **NEVER allow the snapshot window to overlap the maintenance window
   in the CHECKLIST.** Overlap causes skipped backups or delayed
   maintenance. The output MUST include both windows and confirm
   non-overlap with at least 1 hour of separation.

6. **NEVER use `--num-cache-clusters` (non-cluster mode) and
   `--num-node-groups` (cluster mode) interchangeably in the CHECKLIST.**
   These are different API paths requiring different client libraries
   (cluster-aware vs standard Redis client). The topology line MUST
   explicitly identify which mode is selected.

7. **NEVER omit the `VERIFICATION_COMMANDS:` block.** The copy-pasteable
   AWS CLI commands are how the operator confirms the deployment
   succeeded. A checklist without verification commands is incomplete.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Redis vs Memcached engine selection | Engine choice |
| Step 2 — Cluster mode enabled vs self-designed (Redis) | Redis topology |
| Step 3 — Replication groups and multi-AZ failover | High availability |
| Step 4 — Node type sizing | Capacity planning |
| Step 5 — Subnet groups and security groups | Network + security |
| Step 6 — Parameter groups | Engine configuration |
| Step 7 — Encryption at rest (KMS) and in transit (TLS) | Security |
| Step 8 — Redis AUTH tokens | Authentication |
| Step 9 — Backup and snapshot management | Data durability |
| Step 10 — Global Datastore (cross-region replication) | DR / cross-region |
| Step 11 — Auto-scaling | Capacity elasticity |
| Step 12 — Online cluster resizing (use-online-resharding) | Scale operations |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/redis-topology-and-failover.md | Cluster mode + failover detail |
| references/security-and-encryption.md | Encryption + AUTH detail |

## Mindset

**One-line takeaway:** ElastiCache for Redis cluster mode enabled
partitions data across shards using hash slots (16,384 total), each
shard has a primary and 0-5 read replicas, multi-AZ failover promotes a
replica automatically when the primary fails. Encryption at rest and in
transit must be enabled at creation time — they CANNOT be toggled on
after the cluster exists. Online resharding lets you add/remove shards
with zero downtime using the use-online-resharding flag.

Three misconceptions dominate ElastiCache misdesign at provisioning
time:

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

## Configuration dependency graph (novel heuristic)

ElastiCache configurations are NOT independent. Encryption must be
enabled at creation time. Cluster mode is immutable without online
resharding. Subnet groups must exist before the cluster. Use this graph
to sequence provisioning.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subnet group | Subnets in >= 2 AZs (multi-AZ); same VPC | Cross-VPC subnets rejected at API | cluster creation |
| Security group | VPC exists; port 6379 (Redis) or 11211 (Memcached) | No ingress rule = client timeout (not API error) | client connectivity |
| Replication group (Redis) | Subnet group + security group exist | Encryption must be set at creation — CANNOT toggle | cluster endpoints |
| Cluster mode enabled | `--num-node-groups > 1` at creation | Switching modes requires migration | horizontal scaling |
| Multi-AZ + failover | >= 1 replica per shard; nodes across >= 2 AZs | Multi-AZ without replicas = no failover target | high availability |
| At-rest encryption (KMS) | KMS key exists; set at creation | CANNOT enable on existing cluster | compliance |
| In-transit encryption (TLS) | Set at creation | CANNOT enable on existing cluster | compliance |
| AUTH token | In-transit encryption MUST be enabled first | AUTH without TLS = token in cleartext | authentication |
| Backup (automated) | Retention period > 0; snapshot window set | Overlap with maintenance window = skipped snapshots | data durability |
| Global Datastore | Primary cluster in region A; same engine version | Encryption config must match across regions | cross-region DR |
| Online resharding | Cluster mode enabled; async operation | Non-cluster mode CANNOT be resharded | scale without downtime |
| Auto-scaling | Replication group exists; scaling policy defined | Min/max must be within node-group limits | capacity elasticity |

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

## Expert heuristic: cluster mode enabled topology + replica promotion priority + snapshot window vs maintenance window overlap

A baseline model says "create a Redis cluster." The correct heuristic
designs the cluster-mode topology (shards and hash slots), sets replica
promotion priorities for predictable failover, and ensures the snapshot
window does not overlap the maintenance window.

```text
Cluster mode enabled — 3 shards, 1 replica each (6 nodes total):

  Shard 1 (slots 0-5460):
    Primary: node-0001 (AZ-a)
    Replica: node-0004 (AZ-b, priority 100) ← failover target

  Shard 2 (slots 5461-10922):
    Primary: node-0002 (AZ-b)
    Replica: node-0005 (AZ-c, priority 100)

  Shard 3 (slots 10923-16383):
    Primary: node-0003 (AZ-c)
    Replica: node-0006 (AZ-a, priority 100)

Replica promotion priority (ReplicaPriority, default 100):
  Lower number = higher promotion priority.
  Priority 0 = never promoted (read-only replica).

Failover: primary fails → highest-priority replica promoted → DNS updated.
```

**Window overlap check:**
```text
Snapshot window:   03:00-05:00 UTC daily
Maintenance window: mon:05:00-mon:06:00 UTC weekly

If they overlap → snapshots skipped or maintenance delayed.
Best practice: gap of 1+ hours between snapshot end and maintenance.
  Snapshot:   01:00-03:00 UTC
  Maintenance: mon:05:00-mon:06:00 UTC
```

**Key implication:** the topology (shard count, replica count, AZ
placement) determines capacity and availability. Replica promotion
priority controls failover behavior. Window overlap is a silent failure
that causes missing backups.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC and subnets (>= 2 AZs) | Subnet group needs multi-AZ subnets | `aws ec2 describe-subnets` |
| Subnet group exists or creatable | Cluster requires a subnet group | `aws elasticache describe-cache-subnet-groups` |
| Security group (port 6379/11211) | Client connectivity | `aws ec2 describe-security-groups` |
| Node type selected | Memory, CPU, network capacity | `aws elasticache describe-cache-engine-versions` |
| Engine + version | Encryption needs Redis >= 6.0 for TLS 1.3 | Confirm feature compatibility |
| Encryption decision | MUST be at creation — cannot toggle later | Assess compliance requirements |
| AUTH token decision | Requires in-transit encryption first | Assess authentication requirements |
| Multi-AZ + failover decision | Requires >= 1 replica per shard | Assess availability requirements |
| Cluster mode decision | Different API path and client libs | Assess scaling requirements |
| Snapshot vs maintenance window | Must not overlap | Plan windows |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Redis vs Memcached engine selection

| Feature | Redis OSS | Memcached |
|---|---|---|
| Persistence | Yes (RDB, AOF) | No |
| Replication | Yes (primary + replicas) | No |
| Multi-AZ failover | Yes (auto promotion) | No |
| Cluster mode / sharding | Yes (cluster mode enabled) | Yes (auto-discovery) |
| Encryption at rest | Yes (KMS) | No |
| Encryption in transit | Yes (TLS) | No |
| AUTH token | Yes | No |
| Snapshots / backups | Yes | No |
| Global Datastore | Yes (cross-region) | No |
| Online resharding | Yes | No |
| Multi-threaded | No (per shard) | Yes |
| Data structures | Rich (lists, sets, hashes, streams) | Key-value only |

**Choose Redis** for persistence, replication, encryption, HA, or rich
data structures. **Choose Memcached** for simple ephemeral multi-
threaded caching with no durability.

## Step 2 — Cluster mode enabled vs self-designed (Redis)

| Feature | Non-cluster (self-designed) | Cluster mode enabled |
|---|---|---|
| API params | `--num-cache-clusters` | `--num-node-groups` + `--replicas-per-node-group` |
| Partitioning | Single primary (no sharding) | Hash slots across shards |
| Max memory | One node's capacity | Sum of all shards |
| Client library | Standard Redis client | Cluster-aware client |
| Online resharding | Not supported | Supported |

**Non-cluster mode:**

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-non-cluster \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122 \
  --automatic-failover-enabled --multi-az-enabled
```

**Cluster mode enabled:**

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-cluster \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122 \
  --automatic-failover-enabled --multi-az-enabled \
  --cache-parameter-group-name my-param-group
```

**Common mistake:** using `--num-cache-clusters` when you need cluster
mode. Cluster mode uses `--num-node-groups` and `--replicas-per-node-group`.

## Step 3 — Replication groups and multi-AZ failover

A Redis replication group has a primary and 0-5 read replicas per shard.
Multi-AZ with automatic failover promotes a replica in a different AZ
when the primary fails.

```bash
# At creation (recommended):
aws elasticache create-replication-group \
  --replication-group-id my-redis-ha \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --automatic-failover-enabled --multi-az-enabled \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122

# Modify existing:
aws elasticache modify-replication-group \
  --replication-group-id my-redis-ha \
  --automatic-failover-enabled --multi-az-enabled --apply-immediately
```

**Critical:** multi-AZ without at least one replica per shard is
ineffective — failover has no target to promote.

## Step 4 — Node type sizing

| Workload | Recommended type | Rationale |
|---|---|---|
| Small cache (< 5 GB) | cache.r6g.large | Cost-effective |
| Medium (5-25 GB) | cache.r6g.xlarge or cluster mode | Balance memory + CPU |
| Large (25-100 GB) | cache.r6g.2xlarge or more shards | Distribute memory |
| High throughput | cache.r6g.4xlarge+ or more shards | CPU + network |

For cluster mode, total capacity = (node memory) x (num shards).
Per-shard throughput scales with replicas (reads) and shards (writes).

## Step 5 — Subnet groups and security groups

**Create a subnet group (requires >= 2 AZs for multi-AZ):**

```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name my-cache-subnet-group \
  --cache-subnet-group-description "ElastiCache subnet group" \
  --subnet-ids subnet-aaa11122 subnet-bbb22233 subnet-ccc33344
```

**Security group (Redis 6379, Memcached 11211):**

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name elasticache-redis-sg --description "ElastiCache Redis SG" \
  --vpc-id vpc-aaa11122 --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" --protocol tcp --port 6379 \
  --source-security-group-id sg-app11122
```

**Critical:** the SG must allow inbound from the application SG (not
CIDR) for least-privilege. Port differs: Redis = 6379, Memcached = 11211.

## Step 6 — Parameter groups

```bash
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --cache-parameter-group-family redis6.x \
  --description "Custom Redis parameters"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --parameter-name-values ParameterName=maxmemory-policy,ParameterValue=allkeys-lru
```

| Parameter | Default | Effect |
|---|---|---|
| maxmemory-policy | volatile-lru | Eviction policy when full |
| timeout | 0 | Idle client timeout |
| cluster-enabled | yes (cluster mode) | Redis cluster mode |

## Step 7 — Encryption at rest (KMS) and in transit (TLS)

**Encryption is creation-time-only for Redis replication groups.** It
CANNOT be toggled on after the cluster exists.

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-encrypted \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/aaa11122 \
  --transit-encryption-enabled \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122
```

| Encryption type | Parameter | Post-creation |
|---|---|---|
| At-rest (KMS) | `--at-rest-encryption-enabled` | CANNOT toggle |
| In-transit (TLS) | `--transit-encryption-enabled` | CANNOT toggle |
| AUTH token | `--auth-token` | CANNOT toggle |

**Critical:** if you need encryption on an existing cluster, you must
create a new encrypted cluster and migrate data.

## Step 8 — Redis AUTH tokens

AUTH tokens require in-transit encryption (TLS) — otherwise the token
is sent in cleartext.

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-auth \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --transit-encryption-enabled \
  --auth-token "MyStr0ngT0k3n!2026" \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122

# Store token in Secrets Manager for rotation
aws secretsmanager create-secret \
  --name elasticache/redis-auth-token \
  --secret-string "MyStr0ngT0k3n!2026"
```

## Step 9 — Backup and snapshot management

| Backup type | How | Retention |
|---|---|---|
| Automated | Daily snapshot in snapshot window | 0-35 days (0 = disabled) |
| Manual | On-demand via API | Until manually deleted |

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-backup \
  --engine redis --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122

# Manual snapshot
aws elasticache create-snapshot \
  --snapshot-name my-manual-snapshot-20260805 \
  --replication-group-id my-redis-backup
```

**Critical:** the snapshot window MUST NOT overlap the maintenance
window. If they overlap, snapshots may be skipped.

## Step 10 — Global Datastore (cross-region replication)

Global Datastore provides cross-region replication for DR and low-
latency multi-region reads.

```bash
# Step 1: Create primary in region A with global suffix
aws elasticache create-replication-group \
  --replication-group-id my-redis-global-primary \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --global-replication-group-suffix-group-id my-global \
  --cache-subnet-group-name my-subnet-useast \
  --security-group-ids sg-useast111 --region us-east-1

# Step 2: Create the Global Datastore
aws elasticache create-global-replication-group \
  --global-replication-group-id my-global-datastore \
  --primary-replication-group-id my-redis-global-primary \
  --global-replication-group-description "Cross-region DR" \
  --region us-east-1

# Step 3: Add secondary in region B
aws elasticache create-replication-group \
  --replication-group-id my-redis-global-secondary \
  --global-replication-group-id <global-id-fqn> \
  --cache-subnet-group-name my-subnet-euwest \
  --security-group-ids sg-euwest111 --region eu-west-1
```

**Constraints:** same engine version across regions; encryption config
must match; secondary is read-only until failover.

## Step 11 — Auto-scaling

```bash
# Register scalable target (shard count)
aws application-autoscaling register-scalable-target \
  --service-namespace elasticache \
  --resource-id replication-group/my-redis-cluster \
  --scalable-dimension elasticache:replication-group:NodeGroups \
  --min-capacity 3 --max-capacity 10

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --service-namespace elasticache \
  --resource-id replication-group/my-redis-cluster \
  --scalable-dimension elasticache:replication-group:NodeGroups \
  --policy-name my-scaling-policy --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ElastiCachePrimaryEngineCPUUtilization"},"TargetValue":60.0,"ScaleOutCooldown":300,"ScaleInCooldown":300}'
```

Auto-scaling uses CloudWatch metrics (EngineCPUUtilization,
DatabaseMemoryUsagePercentage) as triggers. Scale-out adds shards;
scale-in removes shards. Online resharding is performed automatically.

## Step 12 — Online cluster resizing (use-online-resharding)

Online resharding adds/removes shards from a cluster-mode-enabled
replication group with ZERO downtime.

```bash
# Scale out (add shards)
aws elasticache modify-replication-group-shard-configuration \
  --replication-group-id my-redis-cluster \
  --node-group-count 5 --apply-immediately

# Scale in (remove specific shards)
aws elasticache modify-replication-group-shard-configuration \
  --replication-group-id my-redis-cluster \
  --node-group-count 2 \
  --node-groups-to-remove "0003" "0004" --apply-immediately

# Check resharding status (async operation)
aws elasticache describe-replication-groups \
  --replication-group-id my-redis-cluster \
  --query 'ReplicationGroups[0].Status'
# "modifying" = in progress; "available" = complete
```

**Key implication:** online resharding is ONLY for cluster-mode-enabled
groups. Non-cluster mode requires migration to a new cluster.

## Step 13 — Recent features

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

## NEVER do these things

1. **NEVER assume encryption can be enabled after cluster creation.**
   At-rest (KMS) and in-transit (TLS) encryption are creation-time-only
   for Redis replication groups. Existing non-encrypted clusters require
   migration to a new encrypted cluster.

2. **NEVER set an AUTH token without enabling in-transit encryption.**
   AUTH requires TLS. Setting AUTH without TLS sends the token in
   cleartext — a security vulnerability.

3. **NEVER enable multi-AZ failover without at least one replica per
   shard.** Multi-AZ without a replica to promote is a no-op. Always
   verify `--replicas-per-node-group >= 1`.

4. **NEVER confuse cluster mode and non-cluster mode.** Cluster mode
   uses `--num-node-groups` + `--replicas-per-node-group`. Non-cluster
   uses `--num-cache-clusters`. Client libraries differ (cluster-aware
   vs standard).

5. **NEVER allow the snapshot window to overlap the maintenance
   window.** Overlap causes skipped snapshots or delayed maintenance.
   Separate windows by at least 1 hour.

6. **NEVER attempt online resharding on a non-cluster-mode cluster.**
   Online resharding is ONLY for cluster-mode-enabled groups. Non-
   cluster mode requires migration.

7. **NEVER create a Global Datastore with mismatched engine versions.**
   Primary and secondary must use the same engine version. Mismatches
   cause replication failures.

8. **NEVER use Memcached when you need persistence, replication, or
   encryption.** Memcached does NOT support these features. Use Redis.

9. **NEVER forget the security group port.** Redis = 6379; Memcached =
   11211. Wrong port is a silent failure (client timeout, not API error).

10. **NEVER scale a cluster without monitoring the resharding status.**
    Online resharding is asynchronous. Check
    `describe-replication-groups` status until "available" before
    further modifications.

## Output format

```text
ELASTICACHE_CLUSTER: <cluster-id> (<engine>, <node-type>, <topology>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Engine: Redis OSS | Memcached
  [✓|✗] Topology: Cluster mode enabled (<N> shards x <R> replicas) | Non-cluster (<N> nodes) | Memcached (<N> nodes)
  [✓|✗] Node type: <node-type>
  [✓|✗] Subnet group: <subnet-group-name> (<N> AZs)
  [✓|✗] Security group: <sg-id> (port <6379|11211>)
  [✓|✗] Parameter group: <param-group-name>
  [✓|✗] Multi-AZ failover: Enabled (<N> AZs) | Disabled
  [✓|✗] At-rest encryption (KMS): Enabled (key <kms-key-id>) | Disabled
  [✓|✗] In-transit encryption (TLS): Enabled | Disabled
  [✓|✗] AUTH token: Set (Secrets Manager) | Not set
  [✓|✗] Backup: Automated (retention <N> days, window <window>) | Manual | Disabled
  [✓|✗] Snapshot window: <window> (no overlap with maintenance <window>)
  [✓|✗] Global Datastore: <global-id> (primary <region>, secondary <region>) | Not configured
  [✓|✗] Auto-scaling: Target tracking (<metric>, target <value>%) | Not configured
  [✓|✗] Online resharding: Available (cluster mode) | Not available (non-cluster)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id <cluster-id> --region <region>
  aws elasticache describe-cache-clusters --show-cache-node-info --region <region>
  aws elasticache describe-global-replication-groups --show-global-nodegroups --region <region>
```

### Worked example — Redis cluster mode enabled, 3 shards, KMS encryption, multi-AZ

```text
ELASTICACHE_CLUSTER: session-store-prod (Redis OSS 7.0, cache.r6g.large, cluster mode enabled)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: Redis OSS (version 7.0)
  [✓] Topology: Cluster mode enabled (3 shards x 1 replica = 6 nodes total)
    Shard 1: slots 0-5460, primary AZ-a, replica AZ-b (priority 100)
    Shard 2: slots 5461-10922, primary AZ-b, replica AZ-c (priority 100)
    Shard 3: slots 10923-16383, primary AZ-c, replica AZ-a (priority 100)
  [✓] Node type: cache.r6g.large (2 vCPU, 12.93 GB RAM per node)
  [✓] Subnet group: prod-redis-subnet-group (3 AZs: us-east-1a, us-east-1b, us-east-1c)
  [✓] Security group: sg-0abc123def456 (port 6379, inbound from sg-app-workload only)
  [✓] Parameter group: prod-redis-params (maxmemory-policy=allkeys-lru, timeout=300)
  [✓] Multi-AZ failover: Enabled (3 AZs, automatic-failover + multi-az flags set)
  [✓] At-rest encryption (KMS): Enabled (key arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ef-1234-567890abcdef)
  [✓] In-transit encryption (TLS): Enabled (creation-time-only — cannot toggle post-creation)
  [✓] AUTH token: Set (Secrets Manager: elasticache/session-store-prod-auth-token, requires TLS)
  [✓] Backup: Automated (retention 7 days, snapshot window 01:00-03:00 UTC daily)
  [✓] Snapshot window: 01:00-03:00 UTC (no overlap with maintenance wed:04:00-wed:05:00 UTC — 1h gap confirmed)
  [✓] Global Datastore: Not configured
  [✓] Auto-scaling: Target tracking (EngineCPUUtilization, target 60%, min 3 shards, max 10 shards)
  [✓] Online resharding: Available (cluster mode enabled — can add/remove shards with zero downtime)
  [✓] Tags: Environment=production, Application=session-store, Owner=platform-team
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id session-store-prod --region us-east-1
  aws elasticache describe-cache-clusters --show-cache-node-info --region us-east-1
  aws kms describe-key --key-id arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ef-1234-567890abcdef --region us-east-1
```

### Worked example — PREREQUISITES_MISSING (subnet group absent)

```text
ELASTICACHE_CLUSTER: cache-dev (Redis OSS 7.0, cache.r6g.large, cluster mode enabled)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Engine: Redis OSS (version 7.0)
  [✓] Topology: Cluster mode enabled (3 shards x 1 replica = 6 nodes total)
  [✓] Node type: cache.r6g.large
  [✗] Subnet group: dev-redis-subnet-group — DOES NOT EXIST. Run `aws elasticache describe-cache-subnet-groups --cache-subnet-group-name dev-redis-subnet-group` returns ResourceNotFound. Create the subnet group with subnets in at least 2 AZs before deploying.
  [✓] Security group: sg-dev123456 (port 6379, inbound from sg-app-dev)
  [✓] Multi-AZ failover: Enabled (3 AZs planned)
  [✓] At-rest encryption (KMS): Enabled (key arn:aws:kms:us-east-1:123456789012:key/b2c3d4e5-6789-01ab-cdef-234567890abc)
  [✓] In-transit encryption (TLS): Enabled
  [✓] Snapshot window: 01:00-03:00 UTC (no overlap with maintenance wed:04:00-wed:05:00 UTC)
VERIFICATION_COMMANDS:
  aws elasticache describe-cache-subnet-groups --cache-subnet-group-name dev-redis-subnet-group --region us-east-1
  # Create the subnet group first, then re-invoke this skill
```

## Error handling

### Cluster creation fails with "encryption not supported"

- Verify the engine version supports encryption (Redis >= 6.x for TLS
  1.3). Upgrade the engine version and retry.

### Multi-AZ failover not triggering

- Verify at least one replica per shard. Check nodes are across >= 2
  AZs. Use `describe-replication-groups` to confirm `AutomaticFailover`
  status is "enabled."

### Clients cannot connect

- Check the security group allows inbound from the app SG on the
  correct port. For TLS-enabled clusters, verify the client library
  supports TLS connections.

### Online resharding stuck in "modifying"

- Resharding is asynchronous (minutes to hours). Monitor with
  `describe-replication-groups`. Check CloudWatch for replication lag
  or memory pressure if stuck.

### Snapshot skipped

- Snapshot window overlaps maintenance window. Reschedule one of them.

## Domain

AWS CloudOps / Amazon ElastiCache Cluster Provisioning & In-Memory
Data Store Management.

## AWS documentation

- **ElastiCache for Redis** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/WhatIs.html
- **Replication groups** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.html
- **Cluster mode enabled** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/ClusterMode.html
- **Multi-AZ with automatic failover** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/AutoFailover.html
- **Encryption at rest and in transit** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/at-rest-encryption.html
- **AUTH tokens** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/auth.html
- **Global Datastore** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Redis-Global-Datastore.html
- **Online resharding** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/cluster-mode-resharding.html
- **ElastiCache auto-scaling** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/AutoScaling.html
- **Memcached** — https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/WhatIs.html
- **Snapshots and backups** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Snapshots.html
