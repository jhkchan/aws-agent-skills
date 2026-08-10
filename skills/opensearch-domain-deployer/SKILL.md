---
name: opensearch-domain-deployer
description: >-
  Provisions Amazon OpenSearch Service domains with production
  defaults: deployment type (managed cluster vs Serverless), instance
  type (t3.small.search dev to r6g.4xlarge.search production), data
  nodes vs dedicated masters vs UltraWarm vs cold storage, Multi-AZ
  3-zone, EBS (gp3 default, io1 for high IOPS), encryption at-rest
  (KMS, must enable at creation) and in-transit (TLS), VPC-only vs
  public access, fine-grained access control (FGAC) with IAM or
  Cognito master user, snapshots (automated + manual to S3), shard
  and replica count, OpenSearch Serverless, vector search, streaming
  ingestion. Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating an OpenSearch domain, choosing managed
  vs Serverless, designing Multi-AZ topology, sizing shards and
  instances, enabling FGAC, or generating provisioning CLI / IaC
  templates. Triggers: create OpenSearch, provision OpenSearch,
  OpenSearch Serverless, OpenSearch FGAC, UltraWarm, vector search.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with opensearch,
  opensearchserverless, ec2, kms, iam, and cognito-idp access. Works
  with Terraform aws_opensearch_domain /
  aws_opensearchserverless_collection resources and CloudFormation
  AWS::OpenSearchService::Domain templates.
keywords:
  - aws
  - opensearch
  - elasticsearch
  - cloudops
  - deploy
  - provisioning
  - search
  - analytics
  - domain
  - managed cluster
  - serverless
  - data nodes
  - dedicated master
  - ultrawarm
  - cold storage
  - multi-az
  - 3-zone
  - ebs
  - gp3
  - io1
  - encryption at rest
  - encryption in transit
  - tls
  - kms
  - vpc
  - public access
  - fine-grained access control
  - fgac
  - iam master user
  - cognito
  - snapshot
  - repository
  - shard count
  - replica count
  - vector search
  - streaming ingestion
tags:
  - aws
  - opensearch
  - elasticsearch
  - cloudops
  - deploy
  - analytics
  - search
  - provisioning
  - managed-cluster
  - serverless
  - multi-az
  - encryption
  - fgac
  - ultrawarm
  - vector-search
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
    - elasticsearch
    - cloudops
    - deploy
    - analytics
    - search
    - provisioning
    - managed-cluster
    - serverless
    - multi-az
    - encryption
    - fgac
    - ultrawarm
    - vector-search
  dependencies:
    - aws-orchestrator
  keywords:
    - create opensearch domain
    - provision opensearch
    - set up opensearch serverless
    - opensearch managed cluster
    - opensearch multi-az
    - opensearch encryption
    - opensearch vpc
    - opensearch fgac
    - opensearch ultrawarm
    - opensearch cold storage
    - opensearch shards
    - opensearch vector search
    - opensearch streaming ingestion
    - opensearch cognito
    - opensearch snapshot repository
  when_to_use: >-
    Invoke when the user wants to create a new OpenSearch Service
    domain (managed cluster or Serverless), design a Multi-AZ production
    topology with dedicated master nodes, size data nodes and shard
    count, enable fine-grained access control (FGAC), configure UltraWarm
    or cold storage for cost optimization, set up vector search
    collections, configure snapshot repositories, or generate
    provisioning CLI commands / IaC templates. Do NOT invoke for
    auditing existing domain posture (use opensearch-domain-auditor),
    or for non-OpenSearch search/analytics (Athena, CloudSearch,
    self-managed Elasticsearch on EC2).
---

# OpenSearch Domain Deployer

An AWS CloudOps agent skill that provisions Amazon OpenSearch Service
domains with correct defaults. The skill walks the operator through a
10-step provisioning procedure, captures the operator's deployment
type, topology, security, and capacity decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create OpenSearch, provision OpenSearch, OpenSearch deployment, managed
cluster, OpenSearch Serverless, data nodes, dedicated master nodes,
UltraWarm, cold storage, Multi-AZ, 3-zone deployment, instance type,
t3.small.search, r6g.4xlarge.search, EBS storage, gp3, io1, encryption
at rest, encryption in transit, TLS, KMS, VPC access, public access,
fine-grained access control, FGAC, IAM master user, Cognito, snapshot
repository, shard count, replica count, vector search collection,
streaming ingestion.

## Invocation contract (hard requirement)

When this skill is invoked with a domain-provisioning request (domain
name, instance type, workload shape, region, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in §"Output format" using the literal all-caps labels
`DOMAIN:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do
NOT preface the checklist with prose, headings, or disclaimers — emit
the block as the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

## Mindset

**One-line takeaway:** OpenSearch correctness is decided at creation
time. Encryption at rest, fine-grained access control mode, VPC vs
public access, and the Multi-AZ topology are impossible or disruptive
to change later — the provisioning procedure treats each as a one-way
door and forces an explicit decision before the `create-domain` call.

Three misconceptions dominate OpenSearch misdesign at provisioning
time:

- **"Pick the largest instance type and scale down later."** OpenSearch
  charges per instance-hour regardless of utilization. A 30-node
  `r6g.4xlarge.search` cluster running at 5% CPU costs the same as one
  running at 80%. Size based on storage + compute requirements, not on
  "we might need it." The shard-count heuristic (1 shard per 30-50 GB)
  is the right starting point, not the instance spec sheet.

- **"Public access with IP allowlist is fine for production."** Public
  access exposes the OpenSearch endpoint to internet scanning, even
  with an IP allowlist. The IP allowlist is a network control, not an
  authentication control — a misconfigured allowlist or a compromised
  allowlisted IP immediately exposes the cluster. VPC-only access with
  FGAC + IAM is the production baseline.

- **"Dedicated master nodes are optional for production."** Without
  dedicated masters, cluster-state changes (shard reallocation, node
  loss) consume CPU on data nodes — query latency spikes during
  recovery. For any production cluster with > 10 data nodes OR
  latency-sensitive workloads, dedicated masters are mandatory.

## Quick navigation

| Section | When to read |
|---|---|
| §"Prerequisites" | Always — verify before provisioning |
| §"Step 1 — Deployment type" | Managed cluster vs Serverless |
| §"Step 2 — Instance types" | t3/r6g/m6g/c6g.search selection |
| §"Step 3 — Multi-AZ + dedicated masters" | Production topology |
| §"Step 4 — Storage (EBS, instance)" | gp3 vs io1 vs instance-store |
| §"Step 5 — Encryption" | KMS at-rest, TLS in-transit |
| §"Step 6 — Network + FGAC" | VPC vs public, IAM vs Cognito |
| §"Step 7 — Indexing (shards, replicas)" | Shard count, replica count |
| §"Step 8 — Snapshots" | Automated + manual to S3 |
| §"Step 9 — UltraWarm / cold storage" | Tiered storage for cost |
| §"Step 10 — Serverless / vector search" | Latest 2023-2026 features |
| §"NEVER do these things" | Review before signing off |
| §"Output format" | The literal checklist template |
| references/topology-and-indexing.md | Deep Multi-AZ + shard math |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Reasoning framework (why provisioning order matters)

OpenSearch configurations have **dependency and immutability
semantics** that make the provisioning order non-trivial. Wrong-order
or wrong-time decisions either cannot be reversed or require a full
re-index migration:

1. **Encryption at rest BEFORE the first document** — must enable at
   domain creation. Adding encryption at rest to an existing domain is
   NOT supported — it requires creating a new domain, re-indexing all
   data, and repointing clients.

2. **FGAC mode BEFORE the first user** — fine-grained access control
   mode (IAM master user vs Cognito user pool vs IP-only) is chosen at
   creation. Switching modes post-creation requires a full reindex via
   remote reindex or snapshot restore.

3. **VPC vs public access BEFORE the first client** — changing from
   public to VPC access (or vice versa) requires creating a new domain.
   There is NO modify path. Pick VPC at creation for production.

4. **Multi-AZ BEFORE production traffic** — Multi-AZ (3-zone) requires
   the domain's node count be a multiple of 3. Adding a third AZ to a
   2-AZ cluster requires a node-count change (which triggers shard
   rebalancing) and is disruptive. Default to 3-zone at creation for
   production.

5. **Instance type + EBS BEFORE the first shard** — changing instance
   type requires a blue-green deployment (OpenSearch spins up new
   nodes, migrates shards, decommissions old nodes). Multi-hour
   operation. Size up front.

6. **Shard count BEFORE the first index** — over-sharding (too many
   shards per GB) creates overhead; under-sharding (too few shards)
   creates hot shards. Resolving requires a `_split` or `_shrink` API
   call per index (disruptive). Apply the 30-50 GB per shard rule at
   index creation.

## OpenSearch configuration dependency graph (novel heuristic)

OpenSearch configurations are NOT independent. Many are immutable
after creation, others silently downgrade. Use this graph both to
sequence provisioning and to debug "why can't I add this?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Deployment type (managed / Serverless) | none — `create-domain` vs `create-collection` | **IMMUTABLE** — Serverless and managed are different APIs; no migration path | all downstream config |
| Domain name | globally unique in the account-region | **IMMUTABLE** — name cannot be changed; new domain = new endpoint | endpoint URL, DNS |
| Instance type (data nodes) | managed cluster | changeable via blue-green (multi-hour shard migration) | storage, compute |
| Instance count (data nodes) | managed cluster; Multi-AZ requires multiple of 3 | changeable; triggers shard rebalancing (latency spike during) | high availability, capacity |
| Dedicated master nodes | managed cluster | strongly recommended for > 10 data nodes; toggleable but disruptive | cluster stability under node loss |
| Multi-AZ (3-zone) | managed cluster + instance count multiple of 3 | **CANNOT add a 3rd AZ post-creation without node-count change** | AZ-failure resilience |
| EBS storage | managed cluster; gp3 / io1 / standard | changeable via blue-green (multi-hour migration); size is the slowest change | storage capacity |
| Instance-store (NVMe) | specific instance types (i3, i3en) | CANNOT add instance-store to an EBS-only instance | very high IOPS |
| Encryption at rest | managed cluster; must enable at creation; KMS key ARN | **CANNOT add to existing domain** without new domain + reindex | compliance (PCI-DSS, HIPAA) |
| Encryption in transit (TLS) | managed cluster; node-to-node + client-to-node | can enable via `update-domain-config` with rolling replacement | TLS-only clients |
| Fine-grained access control (FGAC) | managed cluster; enable at creation | **Mode switch (IAM ↔ Cognito) requires full reindex** | per-index / per-document IAM |
| Master user (IAM role or ARN) | FGAC enabled | can change post-creation | master-tier administration |
| VPC access | managed cluster; subnet IDs + security group | **CANNOT switch VPC ↔ public post-creation** | network isolation |
| Security groups | VPC access | changeable; port 443 inbound from application SG | network access control |
| Snapshot (automated) | managed cluster | daily automated to AWS-managed S3; retention 1-35 days (configurable) | point-in-time recovery |
| Snapshot (manual to S3) | S3 bucket + IAM role with write access | requires "snapshot repository" registration via PUT _snapshot | long-term retention, cross-cluster migration |
| Shard count | per-index setting at index creation | `_split` / `_shrink` to change post-creation (disruptive) | parallelism, hot-shard risk |
| Replica count | per-index setting | changeable at runtime (no disruption) | HA within / across AZ |
| UltraWarm | managed cluster; specific instance types | read-only; requires index migration (warm → hot is one-way operation) | cost-effective recent-history storage |
| Cold storage | managed cluster; UltraWarm enabled | read-only; recall takes minutes-hours | long-term retention at lowest cost |
| OpenSearch Serverless | separate API (`create-collection`) | NOT compatible with managed-cluster features (UltraWarm, cold storage, dedicated masters) | no capacity management |
| Vector search collection | OpenSearch Serverless | managed-cluster vector search uses traditional indices | vector similarity search (k-NN) |
| Streaming ingestion | OpenSearch Serverless or managed | requires IAM role for source (Kinesis, Kafka, MSK) | near-real-time ingestion without Lambda |

**The four immutable-or-near-immutable rows are the ones a baseline
model misses.** Encryption at rest, FGAC mode, VPC vs public access,
and Multi-AZ topology are decided at creation time. The procedure
below forces an explicit decision on each before the `create-domain`
call.

**Cross-dependency gotchas** (not visible in the table):
- Enabling encryption in transit on an existing domain triggers a
  rolling node replacement that **disconnects every client** for 10-30
  minutes total. Enable at creation.
- Switching FGAC from IAM master user to Cognito user pool (or vice
  versa) requires creating a NEW domain and reindexing via remote
  reindex — there is NO toggle.
- A Multi-AZ domain with 6 data nodes (2 per AZ) loses one AZ
  gracefully; a 4-node Multi-AZ domain (uneven split) does NOT —
  shard allocation becomes unbalanced. Always use multiples of 3.
- UltraWarm indices are READ-ONLY. Moving an index back from warm to
  hot requires `cold_to_warm` or reindex — plan the lifecycle.
- OpenSearch Serverless does NOT support dedicated master nodes,
  UltraWarm, or cold storage — those are managed-cluster features.

## Expert heuristic: shard count estimator

OpenSearch shard count is the most commonly mis-sized parameter. Too
many shards (over-sharding) creates overhead — each shard is a Lucene
index with its own segments, memory footprint, and merge thread. Too
few shards (under-sharding) creates hot shards that bottleneck
ingest and query throughput.

**The 30-50 GB per shard rule:**

```text
recommended_shard_count = ceil(total_data_size_gb / 30)

# Use 30 GB per shard as the upper bound for write-heavy workloads
# Use 50 GB per shard as the upper bound for read-heavy / time-series workloads

# Example: 500 GB of indices, write-heavy (e.g., logs)
recommended_shard_count = ceil(500 / 30) = 17 shards

# Example: 1 TB of indices, read-heavy (e.g., product catalog)
recommended_shard_count = ceil(1024 / 50) = 21 shards
```

**Why 30-50 GB:** above this size, shard recovery (after node loss)
takes too long (10-60 minutes per shard), and merge pressure builds
up. Below 10 GB per shard, the per-shard overhead dominates and
cluster-state updates slow down.

**Per-shard overhead budget:**
- Heap overhead: ~50 KB of heap per shard (mapping, settings).
- File handle overhead: each shard opens ~100-1000 file descriptors.
- CPU overhead: each shard has a merge thread that consumes CPU.

**Cluster-wide shard budget rule of thumb:** 20-25 shards per GB of
heap. A 3-node cluster with 32 GB heap each (96 GB total heap) should
NOT exceed ~2,000-2,400 shards cluster-wide.

**Common scenarios:**
- **Logs / metrics (write-heavy, time-series):** 30 GB per shard.
  Use Index State Management (ISM) to roll over daily, keeping each
  daily index under 30 GB.
- **Product catalog / search (read-heavy):** 50 GB per shard. Fewer,
  larger shards cache better.
- **Vector search (k-NN):** shard count = number of data nodes (one
  shard per node is optimal for k-NN; over-sharding dilutes the
  graph-based index).
- **Small dataset (< 10 GB):** one shard, one replica. Do NOT
  over-shard a small dataset — the overhead dominates.

## Expert heuristic: instance count and sizing

The relationship between data nodes, shard count, and replica count
determines both capacity and availability.

**Capacity formula:**

```text
total_storage_needed = raw_data_size × (1 + replica_count) × 1.1
# 1.1 = 10% overhead for Lucene segments, indexing, free-space watermark

# Free-space watermark: OpenSearch blocks writes at 85% disk full
# (cluster.routing.allocation.disk.watermark.high). Plan for 15% free.

per_node_storage = EBS_volume_size_GB (or instance-store size)
required_data_nodes = ceil(total_storage_needed / per_node_storage)

# Example: 1 TB raw, 1 replica, EBS 100 GB per node
# total = 1024 × 2 × 1.1 = 2253 GB
# required_data_nodes = ceil(2253 / 100) = 23 nodes
```

**Multi-AZ alignment:**

For Multi-AZ (3-zone), round `required_data_nodes` UP to the next
multiple of 3:

```text
required_data_nodes_multi_az = ceil(required_data_nodes / 3) × 3
# 23 nodes → round up to 24 (8 per AZ)
```

**Heap-to-storage ratio rule:**

```text
heap_to_storage_ratio = total_heap_gb / total_storage_gb
# Optimal: 1:30 for general search (heap-to-disk)
# Optimal: 1:15 for heavy aggregations (more heap)
# Optimal: 1:50+ for logs (light aggregations)

# Below 1:50 → under-utilizing memory (consider smaller instances)
# Above 1:10 → memory-bound (consider larger instances or sharding)
```

**Dedicated master node decision:**

```text
if data_nodes > 10:
    → USE dedicated master nodes (3 — one per AZ for Multi-AZ)
else if data_nodes <= 10 AND workload is latency-sensitive:
    → USE dedicated master nodes
else:
    → optional (data nodes can serve as masters for small clusters)
```

**Common mistake:** sizing by CPU only. OpenSearch is storage-bound
for most workloads (logs, search). Calculate storage first, then
verify CPU headroom for queries.

## Expert heuristic: cluster-state instability and dedicated masters

A baseline model says "dedicated masters are recommended" without
explaining what breaks without them. This is the load-bearing detail
for production SLAs.

**Without dedicated masters (data nodes serve as masters):**
- Cluster-state updates (new index, shard allocation, node loss) are
  processed on a data node.
- Cluster-state update blocks CPU on that node for 1-30 seconds
  (depending on cluster size).
- During this block, in-flight queries on that node spike in latency
  or time out.
- For clusters > 10 data nodes, cluster-state size grows — updates
  become frequent and slow.

**With dedicated masters:**
- Cluster-state updates run on the dedicated master (NOT a data node).
- Data nodes serve queries without interruption.
- Master election is faster on node loss (dedicated masters have
  spare CPU for election consensus).

**Mandatory dedicated masters for:**
- Any cluster with > 10 data nodes (HARD recommendation).
- Any cluster where latency p99 must stay under 100 ms (latency-
  sensitive).
- Any cluster with frequent index creation (time-series, logs with
  daily indices).

**Common scenarios:**
- **3-node dev cluster:** no dedicated masters (data nodes serve).
- **10-node production, search app:** 3 dedicated masters
  (`c6g.large.search` — masters are CPU-bound, not memory-bound).
- **30-node production, logs:** 3 dedicated masters
  (`c6g.2xlarge.search` — more CPU for cluster-state on larger
  clusters).

**Master sizing rule:** masters need CPU (cluster-state computation)
and modest memory. `c6g.large.search` for clusters up to 15 data
nodes; `c6g.2xlarge.search` for 15-30; `c6g.4xlarge.search` for 30+.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with OpenSearch access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Domains, instances, snapshots are region-scoped | `aws configure get region` |
| Domain name unique in this account-region | Names are account-region-unique; the domain endpoint derives from the name | `aws opensearch describe-domain --domain-name <name>` returns `ResourceNotFoundException` |
| VPC ID + subnets in 3 AZs (for Multi-AZ + VPC access) | Multi-AZ requires 3 AZs; VPC access requires subnets | `aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc>"` — confirm 3 distinct AZs |
| Security group with port 443 inbound from application SG | OpenSearch uses port 443 (HTTPS) for client traffic | `aws ec2 describe-security-groups --group-ids <sg>` — verify inbound rule on 443 |
| KMS key ARN (if encryption at rest with customer CMK) | Custom encryption requires a CMK in the same region; AWS-managed default is acceptable for dev | `aws kms describe-key --key-id <cmk-id>` |
| IAM role ARN for master user (if FGAC with IAM) | FGAC requires a master user — either an IAM role ARN or a Cognito user pool | `aws iam get-role --role-name <role>` |
| Cognito user pool + identity pool IDs (if FGAC with Cognito) | Cognito-based FGAC requires pre-existing user pool and identity pool | `aws cognito-idp describe-user-pool --user-pool-id <pool>` |
| S3 bucket + IAM role for manual snapshots | Manual snapshots require a registered repository; the role needs `s3:PutObject` on the bucket | `aws s3api head-bucket --bucket <bucket>` + `aws iam get-role --role-name <role>` |
| Workload description (data size, query pattern, ingest rate) | Drives instance type, shard count, replica count decisions | Captured in the prompt or follow-up question |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Deployment type: managed cluster vs Serverless (immutable)

The deployment type is the highest-impact OpenSearch decision and is
**immutable** without a full migration (different APIs, different
endpoints, different feature sets).

**Decision tree:**

```text
Is the workload unpredictable / bursty / unknown capacity?
├── YES → OpenSearch Serverless
│         (auto-scaling; pay-per-use; no capacity management)
│         Note: Serverless does NOT support dedicated masters,
│         UltraWarm, cold storage, or cross-cluster search.
└── NO → Is the workload steady-state and predictable?
    ├── YES → Managed cluster
    │         (full feature set; capacity planning required)
    └── NO → Is the workload vector search only (no text search)?
        ├── YES → OpenSearch Serverless vector search collection
        └── NO → Managed cluster  (default for general search/analytics)
```

**Managed cluster specifics:**
- Full OpenSearch API surface (text search, aggregations, k-NN vector
  search, SQL, anomaly detection, ISM).
- Supports UltraWarm, cold storage, dedicated masters, cross-cluster
  search.
- Capacity planning required (instance type, instance count, EBS).
- Charged per instance-hour regardless of utilization.

**OpenSearch Serverless specifics:**
- Auto-scaling based on traffic; pay-per-use (OCUs — OpenSearch
  Capacity Units).
- No capacity management (no instance type, no shard count to user).
- Subset of API: text search, vector search, some aggregations.
- Does NOT support UltraWarm, cold storage, dedicated masters, or
  cross-cluster search.
- Collection = equivalent of a managed-cluster domain (independent
  endpoint).

**Common mistake:** picking Serverless for "simplicity" then needing
UltraWarm or cold storage. Serverless does NOT support tiered storage.
Pick managed cluster for long-retention analytics workloads.

### Step 2 — Instance types (managed cluster)

OpenSearch offers `.search` suffixed instance types. Choose based on
workload shape.

**Instance family selection:**

| Family | Examples | Optimized for | Use when |
|---|---|---|---|
| `r6g.search` | r6g.large.search (16 GiB RAM, 2 vCPU), r6g.2xlarge.search (64 GiB, 8 vCPU), r6g.4xlarge.search (128 GiB, 16 vCPU) | Memory | General search; large indices; production DEFAULT CHOICE |
| `r7g.search` | r7g.large.search, r7g.4xlarge.search | Memory (latest) | General search; latest Graviton; new clusters |
| `c6g.search` | c6g.large.search (4 GiB, 2 vCPU), c6g.2xlarge.search (16 GiB, 8 vCPU) | Compute | Compute-heavy (aggregations, ML); dedicated master nodes |
| `m6g.search` | m6g.large.search (8 GiB, 2 vCPU), m6g.4xlarge.search (64 GiB, 16 vCPU) | Balanced | Mixed workloads; mid-size indices |
| `i3.search` | i3.large.search (instance-store NVMe), i3.2xlarge.search | Instance storage (NVMe) | Very high IOPS; log analytics; bypass EBS |
| `t3.search` | t3.small.search (2 GiB, 2 vCPU), t3.medium.search (4 GiB, 2 vCPU) | Burst | Dev / test / prototype ONLY |
| Legacy (`t2`, `m3`, `m4`, `c4`, `r3`, `r4`, `i2`) | — | — | DO NOT USE — end-of-life |

**Size by workload:**

- **Dev / test:** `t3.small.search` (single-node, no Multi-AZ).
- **Small production (< 50 GB indices):** `r6g.large.search` × 3 (one
  per AZ) — 16 GiB heap each.
- **Mid production (50-500 GB indices):** `r6g.2xlarge.search` × 3 to
  × 6 (Multi-AZ) — 32 GiB heap each.
- **Large production (500 GB - 5 TB indices):** `r6g.4xlarge.search`
  × 6 to × 12 (Multi-AZ) — 64 GiB heap each + 3 dedicated masters.
- **Very large (5+ TB):** shard the data across multiple domains OR
  use UltraWarm / cold storage for older data.

**Heap sizing rule:** set JVM heap to 50% of instance RAM, capped at
31 GB (compressed oops boundary). OpenSearch defaults to 50%; do NOT
exceed 31 GB.

**Common mistake:** using `t3.small.search` for production. The t3
family has CPU credits that burst; sustained traffic depletes credits
and throttles the cluster. Use `r6g.search` for any production
workload.

### Step 3 — Multi-AZ + dedicated master nodes

Multi-AZ (3-zone) is the primary resilience control for managed
clusters. **Instance count must be a multiple of 3** for even AZ
distribution.

**Multi-AZ topology:**

```text
# 3 data nodes, Multi-AZ:
#   1 in us-east-1a, 1 in us-east-1b, 1 in us-east-1c
#   Loses 1 AZ gracefully (2 of 3 nodes survive)

# 6 data nodes, Multi-AZ:
#   2 in us-east-1a, 2 in us-east-1b, 2 in us-east-1c
#   Loses 1 AZ gracefully (4 of 6 nodes survive)

# 9 data nodes, Multi-AZ:
#   3 per AZ
#   Loses 1 AZ gracefully (6 of 9 nodes survive)
```

**Zone awareness:**
- Enable `ZoneAwarenessEnabled=true` and
  `ZoneAwarenessConfig.AvailabilityZoneCount=3` for Multi-AZ.
- OpenSearch places primary and replica shards in different AZs.
- A 3-node cluster with `replica=1` tolerates one AZ loss.

**Dedicated master nodes:**
- Enable `DedicatedMasterEnabled=true`.
- 3 dedicated masters (one per AZ for Multi-AZ).
- Master instance type: `c6g.large.search` for ≤15 data nodes,
  `c6g.2xlarge.search` for 15-30, `c6g.4xlarge.search` for 30+.

**Mandatory dedicated masters for:**
- > 10 data nodes (cluster-state size grows).
- Latency-sensitive workloads (p99 < 100 ms).
- Frequent index creation (time-series, daily indices).

**Common mistake:** 2-AZ topology with odd node count. Uneven shard
distribution; one AZ is a SPOF. Always use 3 AZs with node count
multiple of 3.

### Step 4 — Storage (EBS vs instance-store)

OpenSearch data nodes use either EBS volumes or instance-store
(NVMe) for storage.

**EBS storage (default for most instance types):**

| Volume type | IOPS | Throughput | Use when |
|---|---|---|---|
| `gp3` (default) | 3,000 baseline, up to 16,000 | 125 MB/s baseline, up to 1,000 MB/s | General-purpose; most production workloads. DEFAULT CHOICE. |
| `io1` | up to 64,000 IOPS (provisioned) | up to 1,000 MB/s | High-IOPS workloads; consistent latency |
| `io2` | up to 64,000 IOPS | up to 1,000 MB/s | High-IOPS + durability (Block Express) |
| `standard` (magnetic) | low | low | DO NOT USE — legacy |

**EBS size:** 10 GB - 6 TB per node (gp3); up to 16 TB (io2 Block
Express). Plan based on the capacity formula in §"Expert heuristic:
instance count and sizing."

**Instance-store (NVMe) — specific instance types:**
- `i3.search`, `i3en.search` have NVMe instance storage.
- Higher IOPS than EBS (no network hop).
- ephemeral — data is LOST if the instance fails. Use with replicas
  (= 1 or higher) for durability.
- Use when: log analytics at massive scale (> 100k docs/sec ingest),
  where EBS IOPS are the bottleneck.

**Free-space watermark (load-bearing):**
- OpenSearch blocks writes at 85% disk full
  (`cluster.routing.allocation.disk.watermark.high`).
- Plan for 15% free space in capacity calculations.

**Common mistake:** sizing EBS for raw data without the replica +
overhead multiplier. A 500 GB index with 1 replica needs 500 × 2 ×
1.1 = 1.1 TB across the cluster. Per-node: 1.1 TB / N nodes.

### Step 5 — Encryption (at-rest + in-transit)

OpenSearch encryption has two layers: at-rest (storage) and
in-transit (network).

**Encryption at rest:**
- **MUST enable at domain creation.** Cannot be added to an existing
  domain without creating a new domain + reindexing.
- Uses AWS KMS. Default: AWS-managed key. For compliance: customer
  CMK via `--encryption-at-rest-options`.
- Encrypts EBS volumes, instance storage, automated snapshots,
  in-flight logs.

**Encryption in transit (TLS):**
- **Recommended at creation.** Can be enabled post-creation via
  `update-domain-config`, but triggers a rolling node replacement
  that disconnects clients for 10-30 minutes total.
- Node-to-node encryption: TLS between OpenSearch nodes (cluster
  internal).
- HTTPS enforcement: TLS between client and OpenSearch endpoint.

```bash
aws opensearch create-domain ... \
  --encryption-at-rest-options Enabled=true,KmsKeyId=arn:aws:kms:...:alias/<cmk> \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07
```

**TLS security policy:** use `Policy-Min-TLS-1-2-2019-07` (TLS 1.2
minimum). Do NOT allow TLS 1.0 / 1.1 (deprecated, vulnerable).

**KMS key policy for OpenSearch:** the CMK's key policy must grant
the OpenSearch service principal `kms:GenerateDataKey` and
`kms:Decrypt`. OpenSearch adds these grants automatically when you
reference the CMK at creation.

**Common mistake:** forgetting to enable at-rest encryption at
creation. Adding it later requires a full domain migration (new
domain + reindex + client repoint). Plan for it.

### Step 6 — Network access + fine-grained access control (FGAC)

Network access and authentication are tightly coupled in OpenSearch.
The four combinations have different security properties.

**Network access: VPC-only vs public:**

| Mode | Endpoint | IP allowlist | Use when |
|---|---|---|---|
| VPC-only | Private VPC endpoint | N/A (security group controls) | PRODUCTION. Network isolation. |
| Public | Public internet endpoint | optional (IP/CIDR allowlist) | Dev / test only. Not recommended for production. |

**FGAC modes (mutually exclusive — choose at creation):**

| Mode | Master user | Authentication | Use when |
|---|---|---|---|
| IAM master user (ARn) | IAM role ARN | AWS SigV4 + OpenSearch internal user DB | Programmatic access; IAM-centric orgs; AWS-native |
| Cognito user pool | Cognito user pool + identity pool | Cognito-hosted UI + IAM role federation | Human users; SSO; web-app dashboards |
| IP-only (no FGAC) | N/A | IP allowlist only | DO NOT USE for production — IP allowlist is not authentication |

**Resource-based policies (complement FGAC):**
- OpenSearch domains support resource-based policies for cross-account
  access without IAM role assumption.
- Use for: cross-account read-only access (e.g., analytics account
  reads from production account's domain).

**Common mistake:** public access with IP allowlist for "production."
An IP allowlist is a network control, not an authentication control —
a misconfigured allowlist or compromised allowlisted IP exposes the
cluster. Always use VPC-only access with FGAC for production.

### Step 7 — Indexing (shard count, replica count)

Shard count and replica count are per-index settings decided at index
creation. They are the highest-impact indexing decisions.

**Shard count:**
- Apply the 30-50 GB per shard rule (see §"Expert heuristic: shard
  count estimator").
- Set at `PUT /<index>` via `"settings": {"number_of_shards": N}`.
- Change post-creation: `_split` (increase) or `_shrink` (decrease) —
  both disruptive.

**Replica count:**
- Default: 1 (one extra copy of each shard).
- Set at `PUT /<index>` via `"settings": {"number_of_replicas": N}`.
- Changeable at runtime (no disruption).
- Multi-AZ: replica shards go to a different AZ than the primary.

**Replica count decision:**
- 0: dev / test only (no HA; data loss on node failure).
- 1: production standard (tolerates 1 node loss; doubles storage).
- 2: high availability (tolerates 2 simultaneous node losses; triples
  storage). Use sparingly — cost.

**Index template pattern (set defaults for all new indices):**

```json
PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1,
      "index.refresh_interval": "1s"
    }
  }
}
```

**Index State Management (ISM) for time-series:**
- Roll over indices daily OR when size exceeds 30 GB.
- Move old indices to UltraWarm after N days.
- Delete indices after M days (or move to cold storage).

**Common mistake:** over-sharding a small dataset. A 1 GB index with
5 shards wastes overhead — use 1 shard.

### Step 8 — Snapshots (automated + manual)

OpenSearch supports automated and manual snapshots for point-in-time
recovery.

**Automated snapshots:**
- Daily, to an AWS-managed S3 bucket (not customer-visible).
- Retention: 1-35 days (configurable).
- Used for: point-in-time recovery to the SAME domain (in-place
  restore) OR to a NEW domain (snapshot restore).

**Manual snapshots:**
- Customer-managed S3 bucket.
- Require a "snapshot repository" registered via `PUT _snapshot/<repo>`.
- Used for: long-term retention beyond automated retention,
  cross-cluster migration, backup before major upgrades.

**Register a manual snapshot repository:**

```bash
# 1. Create an S3 bucket for snapshots
aws s3api create-bucket --bucket opensearch-snapshots-prod --region us-east-1

# 2. Create an IAM role with s3:PutObject / GetObject on the bucket
# (trust policy: opensearch.amazonaws.com assumes the role)

# 3. Register the repository via the OpenSearch API
# (use the OpenSearch `_snapshot` endpoint with the bucket + role ARN)
```

The repository registration uses the OpenSearch `_snapshot` API, which
requires the domain's master user credentials (IAM SigV4 for IAM FGAC;
Cognito user pool credentials for Cognito FGAC).

**Restore from snapshot creates a NEW index:**
- Automated snapshot restore: in-place or to a new index.
- Manual snapshot restore: to a new index (rename pattern required to
  avoid clobbering existing indices).

**Common mistake:** relying on automated snapshots as the ONLY backup.
For long-term retention or cross-region DR, configure manual snapshots
to a customer-managed S3 bucket in a different region.

### Step 9 — UltraWarm and cold storage (managed cluster only)

UltraWarm and cold storage are tiered storage options for cost-
effective retention of older data. Managed cluster only — Serverless
does NOT support these.

**UltraWarm:**
- Read-only warm tier for recent history (e.g., last 30 days of logs).
- Uses NMVe instance storage (lower cost per GB than hot tier).
- ~50% cheaper than hot storage.
- Indices are READ-ONLY after migration to UltraWarm.
- Migration: hot → warm is automatic via ISM; warm → hot requires
  explicit `reindex` from warm.

**Cold storage:**
- Read-only archive tier for long-term retention (months-years).
- Uses S3 (lowest cost per GB).
- Recall takes minutes-hours (must explicitly recall to query).
- Requires UltraWarm enabled.
- ~80% cheaper than hot storage.

**Index lifecycle (ISM policy):**

```json
{
  "policy": {
    "default_state": "hot",
    "states": [
      {"name": "hot", "actions": [], "transitions": [{"state_name": "warm", "conditions": {"min_index_age": "7d"}}]},
      {"name": "warm", "actions": [], "transitions": [{"state_name": "cold", "conditions": {"min_index_age": "30d"}}]},
      {"name": "cold", "actions": [], "transitions": [{"state_name": "delete", "conditions": {"min_index_age": "365d"}}]},
      {"name": "delete", "actions": [{"delete": {}}]}
    ]
  }
}
```

**Common mistake:** migrating indices to UltraWarm then needing to
write to them. UltraWarm is READ-ONLY. Plan the lifecycle so writes
complete before migration.

### Step 10 — OpenSearch Serverless / vector search / streaming ingestion (latest features)

**OpenSearch Serverless (2022-2024):**
- Auto-scaling, pay-per-use (OCU billing).
- No capacity management (no instance type, no shard count).
- Collection = equivalent of a managed-cluster domain.
- VPC-only or public access.

```bash
aws opensearchserverless create-collection \
  --name prod-serverless \
  --type SEARCH \
  --description "Serverless search collection"

aws opensearchserverless create-security-config \
  --name prod-serverless-auth \
  --type iamidentitycenter
```

**Vector search collections (2023-2024):**
- Optimized for vector similarity search (k-NN).
- Use `--type VECTORSEARCH` on `create-collection`.
- Supports approximate nearest neighbor (ANN) algorithms
  (HNSW, IVF).
- Managed-cluster vector search: use the k-NN plugin with
  `index.knn: true` on the index.

**Streaming ingestion (2023-2024):**
- Direct ingestion from Kinesis Data Streams, MSK, or Amazon S3
  without Lambda.
- Requires IAM role for the source to write to OpenSearch.
- Lower latency than Lambda-based ingestion.

```bash
aws opensearch create-domain ... \
  --log-publishing-options LogType=INDEX_SLOW_LOGS,CloudWatchLogLevel=INFO,Enabled=true
```

**Cross-cluster search (2023-2024):**
- Connect multiple OpenSearch domains (managed or Serverless) for
  federated search.
- Use the `connections` API to establish a cross-cluster connection.
- Query one domain, fan out to connected peers.

**Common mistake:** provisioning a managed cluster for a vector-search-
only workload. Serverless vector search collections are cheaper and
simpler for pure k-NN workloads. Use managed cluster only if the
workload needs UltraWarm, cold storage, or cross-cluster search.

## NEVER do these things

1. **NEVER use public access for a production OpenSearch domain.**
   Public access exposes the endpoint to internet scanning. An IP
   allowlist is a network control, not an authentication control.
   Always use VPC-only access with FGAC + IAM.

2. **NEVER forget to enable encryption at rest at domain creation.**
   Adding encryption at rest to an existing domain is NOT supported —
   it requires a new domain, full reindex, and client repoint. Enable
   at creation, every time.

3. **NEVER use `t3.small.search` for production.** The t3 family has
   CPU credits that burst; sustained traffic depletes credits and
   throttles the cluster. Use `r6g.search` or `r7g.search` for any
   production workload.

4. **NEVER provision a 2-AZ topology with odd node count.** Multi-AZ
   requires 3 AZs and node count multiple of 3. A 4-node 2-AZ cluster
   has uneven shard allocation and one AZ is a SPOF.

5. **NEVER skip dedicated master nodes for clusters > 10 data nodes.**
   Without dedicated masters, cluster-state updates consume CPU on
   data nodes — query latency spikes during recovery. Use 3 dedicated
   masters (one per AZ).

6. **NEVER over-shard a small dataset.** A 1 GB index with 5 shards
   wastes overhead — use 1 shard. Apply the 30-50 GB per shard rule
   at index creation, not "5 shards by default."

7. **NEVER set JVM heap above 31 GB.** Above 31 GB, the JVM disables
   compressed ordinary object pointers (oops), increasing memory
   overhead. Cap heap at 31 GB even on larger instances.

8. **NEVER allow TLS 1.0 or 1.1.** Use `Policy-Min-TLS-1-2-2019-07`
   (TLS 1.2 minimum). TLS 1.0 / 1.1 are deprecated and vulnerable.

9. **NEVER use IP-only FGAC for production.** IP allowlist is not
   authentication. Use IAM master user or Cognito user pool.

10. **NEVER rely on automated snapshots as the ONLY backup.**
    Automated snapshots are daily, AWS-managed, 1-35 day retention.
    For long-term retention or cross-region DR, configure manual
    snapshots to a customer-managed S3 bucket.

11. **NEVER switch FGAC mode post-creation without planning a
    reindex.** Switching IAM ↔ Cognito requires creating a NEW domain
    and reindexing via remote reindex. There is NO toggle.

12. **NEVER use UltraWarm as a write target.** UltraWarm indices are
    READ-ONLY. Writes must complete on hot tier before ISM migrates
    the index to UltraWarm.

13. **NEVER provision OpenSearch Serverless for workloads needing
    UltraWarm or cold storage.** Serverless does NOT support tiered
    storage. Use managed cluster for long-retention analytics.

14. **NEVER use end-of-life instance families** (`t2`, `m3`, `m4`,
    `c4`, `r3`, `r4`, `i2` `.search`). Use Graviton (g-series:
    `r6g`, `r7g`, `c6g`, `m6g`) for best price/performance.

## Output format

```text
DOMAIN: <domain-or-collection-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Deployment type: managed cluster | serverless
  [✓|✗] Instance type: <family>.<size>.search (data nodes)
  [✓|✗] Instance count: <N> data nodes (multiple of 3 for Multi-AZ)
  [✓|✗] Multi-AZ (3-zone): Enabled | Disabled
  [✓|✗] Dedicated master nodes: <N> × <family>.<size>.search | None
  [✓|✗] Storage: EBS <type> <size>GB | instance-store NVMe
  [✓|✗] Encryption at rest: Enabled (customer CMK <key-arn> | AWS-managed) | Disabled
  [✓|✗] Encryption in transit (TLS): Enabled (Policy-Min-TLS-1-2-2019-07) | Disabled
  [✓|✗] Network access: VPC-only (subnets: <ids>, SG: <sg-id> port 443) | Public (IP allowlist)
  [✓|✗] Fine-grained access control (FGAC): IAM master user (<role-arn>) | Cognito (<pool-id>) | Disabled
  [✓|✗] Master user: IAM role <arn> | Cognito user <username>
  [✓|✗] Shard count rule: 30-50 GB per shard applied
  [✓|✗] Replica count: <N> (tolerates <N> node losses)
  [✓|✗] Automated snapshots: Enabled (retention <N> days)
  [✓|✗] Manual snapshot repository: registered (S3 bucket <name>, role <arn>) | None
  [✓|✗] UltraWarm: Enabled (<N> × <type>) | Disabled
  [✓|✗] Cold storage: Enabled | Disabled
  [✓|✗] OpenSearch Serverless: Yes (collection type <type>) | No
VERIFICATION_COMMANDS:
  aws opensearch describe-domain --domain-name <name>
  aws opensearch describe-domain-config --domain-name <name>
  aws ec2 describe-security-groups --group-ids <sg-id>
  aws kms describe-key --key-id <cmk-id>
  aws iam get-role --role-name <master-role>
```

### Worked example — production managed cluster with Multi-AZ

```text
DOMAIN: prod-search
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Deployment type: managed cluster
  [✓] Instance type: r6g.2xlarge.search (data nodes)
  [✓] Instance count: 6 data nodes (2 per AZ × 3 AZs)
  [✓] Multi-AZ (3-zone): Enabled (us-east-1a/b/c)
  [✓] Dedicated master nodes: 3 × c6g.large.search (1 per AZ)
  [✓] Storage: EBS gp3 100GB per node (600 GB cluster capacity)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-opensearch-kms)
  [✓] Encryption in transit (TLS): Enabled (Policy-Min-TLS-1-2-2019-07)
  [✓] Network access: VPC-only (subnets: subnet-0aaa/0bbb/0ccc, SG: sg-search123 port 443)
  [✓] Fine-grained access control (FGAC): IAM master user (arn:aws:iam::123456789012:role/opensearch-master)
  [✓] Master user: IAM role arn:aws:iam::123456789012:role/opensearch-master
  [✓] Shard count rule: 30 GB per shard applied (17 shards for 500 GB indices)
  [✓] Replica count: 1 (tolerates 1 node loss per shard)
  [✓] Automated snapshots: Enabled (retention 14 days)
  [✓] Manual snapshot repository: registered (S3 bucket opensearch-snapshots-prod, role arn:aws:iam::123456789012:role/opensearch-snapshot)
  [✓] UltraWarm: Disabled (workload is search, not time-series)
  [✓] Cold storage: Disabled
  [✓] OpenSearch Serverless: No
VERIFICATION_COMMANDS:
  aws opensearch describe-domain --domain-name prod-search
  aws opensearch describe-domain-config --domain-name prod-search
  aws ec2 describe-security-groups --group-ids sg-search123
  aws kms describe-key --key-id alias/prod-opensearch-kms
  aws iam get-role --role-name opensearch-master
```

## STRICT output contract

This section codifies the exact output shape the eval harness asserts
against. Every invocation MUST produce output that matches this
contract or the response is rejected. The labels are case-sensitive
all-caps keywords — no markdown styling, no lowercase variants.

### Required output structure

Every response MUST be a single block with these literal labels, in
this order, as the first lines of the response (no preamble, no prose,
no disclaimers):

```text
DOMAIN: <domain-or-collection-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Deployment type: managed cluster | serverless
  [✓|✗] Instance type: <family>.<size>.search (data nodes)
  [✓|✗] Instance count: <N> data nodes (multiple of 3 for Multi-AZ)
  [✓|✗] Multi-AZ (3-zone): Enabled | Disabled
  [✓|✗] Dedicated master nodes: <N> × <family>.<size>.search | None
  [✓|✗] Storage: EBS <type> <size>GB | instance-store NVMe
  [✓|✗] Encryption at rest: Enabled (customer CMK <key-arn> | AWS-managed) | Disabled
  [✓|✗] Encryption in transit (TLS): Enabled (Policy-Min-TLS-1-2-2019-07) | Disabled
  [✓|✗] Network access: VPC-only (subnets: <ids>, SG: <sg-id> port 443) | Public (IP allowlist)
  [✓|✗] Fine-grained access control (FGAC): IAM master user (<role-arn>) | Cognito (<pool-id>) | Disabled
  [✓|✗] Master user: IAM role <arn> | Cognito user <username>
  [✓|✗] Shard count rule: 30-50 GB per shard applied
  [✓|✗] Replica count: <N> (tolerates <N> node losses)
  [✓|✗] Automated snapshots: Enabled (retention <N> days)
  [✓|✗] Manual snapshot repository: registered (S3 bucket <name>, role <arn>) | None
  [✓|✗] UltraWarm: Enabled (<N> × <type>) | Disabled
  [✓|✗] Cold storage: Enabled | Disabled
  [✓|✗] OpenSearch Serverless: Yes (collection type <type>) | No
VERIFICATION_COMMANDS:
  aws opensearch describe-domain --domain-name <name>
  aws opensearch describe-domain-config --domain-name <name>
  aws ec2 describe-security-groups --group-ids <sg-id>
  aws kms describe-key --key-id <cmk-id>
  aws iam get-role --role-name <master-role>
```

### FORBIDDEN output patterns

1. **NEVER output READY_TO_DEPLOY without listing every checklist item
   with [✓] or [✗].** Every row in the CHECKLIST block must appear
   with an explicit status marker. A checklist with missing rows is
   incomplete and breaks downstream provisioning pipelines that count
   items — the eval harness asserts a minimum row count.

2. **NEVER omit the instance type recommendation — the checklist must
   specify the exact instance type (e.g., r6g.large.search).** A vague
   entry like "Instance type: TBD" or "Instance type: memory-optimized"
   is rejected. Always cite the full `.search`-suffixed type from the
   r6g/r7g/c6g/m6g/i3 families.

3. **NEVER recommend public access for production — VPC-only is the
   production default.** A READY_TO_DEPLOY verdict with "Network
   access: Public" for a production domain is a hard failure. Only
   dev / test domains may use public access, and the checklist entry
   must explicitly note "dev/test only" in that case.

4. **NEVER emit a checklist without the encryption-at-rest status.**
   Encryption at rest is immutable after creation — omitting it from
   the checklist leaves the operator blind to a one-way door decision
   that cannot be reversed without a full domain migration and reindex.

5. **NEVER substitute lowercase or markdown-styled labels for the
   literal all-caps `DOMAIN:`, `VERDICT:`, `CHECKLIST:`,
   `VERIFICATION_COMMANDS:`.** The eval harness pattern-matches on the
   exact labels; `**Verdict**`, `### Verdict`, `Domain:` are all
   silently rejected.

6. **NEVER preface the checklist with prose, headings, or
   disclaimers.** The `DOMAIN:` line must be the first line of the
   response. Any preamble ("Here is your deployment checklist...")
   breaks assertion-based evals that expect the label at byte offset 0.

### Perfect example output

```text
DOMAIN: prod-search
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Deployment type: managed cluster
  [✓] Instance type: r6g.2xlarge.search (data nodes)
  [✓] Instance count: 6 data nodes (2 per AZ × 3 AZs)
  [✓] Multi-AZ (3-zone): Enabled (us-east-1a/b/c)
  [✓] Dedicated master nodes: 3 × c6g.large.search (1 per AZ)
  [✓] Storage: EBS gp3 100GB per node (600 GB cluster capacity)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-opensearch-kms)
  [✓] Encryption in transit (TLS): Enabled (Policy-Min-TLS-1-2-2019-07)
  [✓] Network access: VPC-only (subnets: subnet-0aaa/0bbb/0ccc, SG: sg-search123 port 443)
  [✓] Fine-grained access control (FGAC): IAM master user (arn:aws:iam::123456789012:role/opensearch-master)
  [✓] Master user: IAM role arn:aws:iam::123456789012:role/opensearch-master
  [✓] Shard count rule: 30 GB per shard applied (17 shards for 500 GB indices)
  [✓] Replica count: 1 (tolerates 1 node loss per shard)
  [✓] Automated snapshots: Enabled (retention 14 days)
  [✓] Manual snapshot repository: registered (S3 bucket opensearch-snapshots-prod, role arn:aws:iam::123456789012:role/opensearch-snapshot)
  [✓] UltraWarm: Disabled (workload is search, not time-series)
  [✓] Cold storage: Disabled
  [✓] OpenSearch Serverless: No
VERIFICATION_COMMANDS:
  aws opensearch describe-domain --domain-name prod-search
  aws opensearch describe-domain-config --domain-name prod-search
  aws ec2 describe-security-groups --group-ids sg-search123
  aws kms describe-key --key-id alias/prod-opensearch-kms
  aws iam get-role --role-name opensearch-master
```

## Decision tree: managed cluster vs Serverless

```text
Is the workload unpredictable / bursty / unknown capacity?
├── YES → OpenSearch Serverless
│         (auto-scaling; pay-per-use; no capacity management)
│         Note: Serverless does NOT support UltraWarm, cold storage,
│         dedicated masters, or cross-cluster search.
└── NO → Does the workload need UltraWarm or cold storage?
    ├── YES → Managed cluster (Serverless lacks tiered storage)
    └── NO → Is the workload steady-state and predictable?
        ├── YES → Managed cluster (full feature set)
        └── NO → Is the workload vector search only?
            ├── YES → OpenSearch Serverless vector search collection
            └── NO → Managed cluster  (default for general search)
```

## Decision tree: VPC vs public access

```text
Is this a production domain?
├── YES → VPC-only access with FGAC + IAM
│         (Network isolation; security group controls ingress;
│          FGAC + IAM controls authentication)
└── NO → Is this dev / test with no sensitive data?
    ├── YES → Public access with strong FGAC (acceptable for dev)
    └── NO → VPC-only access (default — even for non-prod)
```

## Error handling

### Domain name already exists (`ResourceAlreadyExistsException`)

```bash
aws opensearch describe-domain --domain-name <name>
```

- If configuration matches intent: the domain is already provisioned
  correctly. Skip to verification and emit READY_TO_DEPLOY.
- If configuration differs: decide whether to `update-domain-config`
  (mutable settings: instance count, instance type, EBS size,
  access policy, snapshot configuration) or create a NEW domain.
  Encryption-at-rest, FGAC mode, and VPC-vs-public CANNOT be changed
  post-creation — those require a new domain + reindex.

### Encryption-at-rest enable fails (`EncryptionAtRestNotEnabledAtCreation`)

You tried to enable encryption at rest on an existing domain. This is
NOT supported. To encrypt an existing unencrypted domain:

1. Create a NEW domain with encryption at rest enabled.
2. Reindex from the old domain to the new domain via the `_remote/reindex`
   OpenSearch API.
3. Repoint clients to the new domain endpoint.
4. Delete the old domain.

**For production:** enable encryption at rest at creation, every time.

### Multi-AZ create fails with uneven node count

Multi-AZ (3-zone) requires instance count to be a multiple of 3.
OpenSearch rejects the create if `InstanceCount` is not divisible by
3 when `ZoneAwarenessEnabled=true` and `AvailabilityZoneCount=3`.

**Fix:** round `InstanceCount` UP to the next multiple of 3:

```bash
# Round up to next multiple of 3
aws opensearch create-domain ... \
  --cluster-config InstanceType=r6g.2xlarge.search,InstanceCount=6,ZoneAwarenessEnabled=true,ZoneAwarenessConfig={AvailabilityZoneCount=3}
```

### Dedicated master node toggle fails during `update-domain-config`

Toggling dedicated masters (`DedicatedMasterEnabled=false` → `true`)
on an existing domain triggers a blue-green deployment that can take
1-4 hours. During this time, the cluster is operational but
experiences elevated latency.

**For production:** enable dedicated masters at creation. Toggling
post-creation requires a maintenance window.

### Snapshot repository registration fails (`RepositoryMissingException`)

The manual snapshot repository must be registered via the OpenSearch
`PUT _snapshot/<repo>` API BEFORE calling `_snapshot/<repo>/<snapshot>`.

**Verify the IAM role for snapshots:**

```bash
aws iam get-role --role-name opensearch-snapshot-role
aws iam get-role-policy --role-name opensearch-snapshot-role --policy-name snapshot-policy
```

The role's trust policy must allow `opensearch.amazonaws.com` to
assume it; the permissions policy must grant `s3:PutObject`,
`s3:GetObject`, `s3:ListBucket` on the snapshot bucket.

### FGAC mode switch fails (`ValidationException`)

Switching from IAM master user to Cognito user pool (or vice versa)
on an existing domain is NOT supported via `update-domain-config`.

**Fix:** create a NEW domain with the desired FGAC mode, then reindex
via `_remote/reindex` from the old to the new domain.

### Cluster stuck in `PROCESSING` after `update-domain-config`

A blue-green deployment on a large cluster (many nodes + replicas)
can take 1-4 hours. The domain status remains `PROCESSING` until the
new nodes are provisioned and shards are migrated.

```bash
aws opensearch describe-domain --domain-name <name> \
  --query 'DomainStatus.Processing'
# Wait for "false" before issuing the next update.
```

## Worked example — production managed cluster with Multi-AZ + FGAC

A production 6-data-node Multi-AZ cluster with 3 dedicated masters,
EBS gp3 storage, customer CMK encryption, VPC-only access, FGAC with
IAM master user, automated + manual snapshots, and CloudWatch alarms.
This is the canonical production pattern.

```bash
# 1. Create the security group (inbound 443 from application SG)
aws ec2 create-security-group \
  --group-name opensearch-prod-sg \
  --description "Security group for prod OpenSearch domain" \
  --vpc-id vpc-0aaa

aws ec2 authorize-security-group-ingress \
  --group-id sg-search123 \
  --protocol tcp \
  --port 443 \
  --source-security-group-id sg-app456

# 2. Create the IAM role for the master user
aws iam create-role \
  --role-name opensearch-master \
  --assume-role-policy-document file://trust-policy.json

# 3. Create the IAM role for manual snapshots
aws iam create-role \
  --role-name opensearch-snapshot \
  --assume-role-policy-document file://snapshot-trust-policy.json

# 4. Create the S3 bucket for manual snapshots
aws s3api create-bucket \
  --bucket opensearch-snapshots-prod \
  --region us-east-1

# 5. Create the customer CMK
aws kms create-alias \
  --alias-name alias/prod-opensearch-kms \
  --target-key-id <key-id>

# 6. Create the OpenSearch domain
aws opensearch create-domain \
  --domain-name prod-search \
  --engine-version OpenSearch_2.11 \
  --cluster-config \
    InstanceType=r6g.2xlarge.search,InstanceCount=6,\
DedicatedMasterEnabled=true,DedicatedMasterType=c6g.large.search,DedicatedMasterCount=3,\
ZoneAwarenessEnabled=true,ZoneAwarenessConfig={AvailabilityZoneCount=3} \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
  --encryption-at-rest-options \
    Enabled=true,KmsKeyId=arn:aws:kms:us-east-1:123456789012:alias/prod-opensearch-kms \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07 \
  --advanced-security-options \
    Enabled=true,InternalUserDatabaseEnabled=false,MasterUserOptions={MasterUserARN=arn:aws:iam::123456789012:role/opensearch-master} \
  --vpc-options SubnetIds=subnet-0aaa,subnet-0bbb,subnet-0ccc,SecurityGroupIds=sg-search123 \
  --log-publishing-options \
    LogType=INDEX_SLOW_LOGS,CloudWatchLogsLogGroupArn=arn:aws:logs:us-east-1:123456789012:log-group:opensearch-index-slow,Enabled=true \
  --snapshot-options AutomatedSnapshotStartHour=3 \
  --access-policies file://access-policy.json \
  --tags Key=Environment,Value=production Key=Workload,Value=search

# 7. Wait for the domain to become active (10-30 minutes)
aws opensearch describe-domain --domain-name prod-search \
  --query 'DomainStatus.[Processing,Endpoint]'

# 8. Register the manual snapshot repository via the OpenSearch API
# (use the master IAM credentials for SigV4 signing)
curl -X PUT "https://<endpoint>/_snapshot/manual-snapshots" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "s3",
    "settings": {
      "bucket": "opensearch-snapshots-prod",
      "region": "us-east-1",
      "role_arn": "arn:aws:iam::123456789012:role/opensearch-snapshot"
    }
  }'

# 9. CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-search-cluster-status-red" \
  --namespace AWS/ES \
  --metric-name ClusterStatus.red \
  --dimensions Name=DomainName,Value=prod-search Name=ClientId,Value=123456789012 \
  --statistic Maximum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:opensearch-alerts

aws cloudwatch put-metric-alarm \
  --alarm-name "prod-search-cpu-high" \
  --namespace AWS/ES \
  --metric-name CPUUtilization \
  --dimensions Name=DomainName,Value=prod-search Name=ClientId,Value=123456789012 \
  --statistic Average --period 60 --threshold 80 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:opensearch-alerts

# 10. Verify
aws opensearch describe-domain --domain-name prod-search
aws opensearch describe-domain-config --domain-name prod-search
aws kms describe-key --key-id alias/prod-opensearch-kms
aws iam get-role --role-name opensearch-master
```

The checklist for this domain:

```text
DOMAIN: prod-search
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Deployment type: managed cluster
  [✓] Instance type: r6g.2xlarge.search
  [✓] Instance count: 6 data nodes (2 per AZ × 3 AZs)
  [✓] Multi-AZ (3-zone): Enabled
  [✓] Dedicated master nodes: 3 × c6g.large.search
  [✓] Storage: EBS gp3 100GB per node
  [✓] Encryption at rest: Enabled (customer CMK)
  [✓] Encryption in transit (TLS): Enabled (TLS 1.2 minimum)
  [✓] Network access: VPC-only
  [✓] FGAC: IAM master user
  [✓] Shard count rule: 30 GB per shard applied
  [✓] Replica count: 1
  [✓] Automated snapshots: Enabled (retention 14 days)
  [✓] Manual snapshot repository: registered
  [✓] UltraWarm: Disabled
  [✓] Cold storage: Disabled
  [✓] OpenSearch Serverless: No
VERIFICATION_COMMANDS:
  aws opensearch describe-domain --domain-name prod-search
  aws opensearch describe-domain-config --domain-name prod-search
  aws kms describe-key --key-id alias/prod-opensearch-kms
  aws iam get-role --role-name opensearch-master
```

## Recent AWS features (2022-2026)

- **OpenSearch Serverless (2022-2023):** Auto-scaling, pay-per-use.
  Separate API (`opensearchserverless`). VPC-only or public. Does NOT
  support UltraWarm, cold storage, dedicated masters. Provisioning
  tip: use for unpredictable / bursty workloads where capacity
  planning is hard.
- **Vector search collections (2023-2024):** Serverless collection
  type `VECTORSEARCH`. Optimized for k-NN similarity search. Supports
  HNSW and IVF algorithms. Use for RAG / generative AI workloads.
- **Streaming ingestion (2023-2024):** Direct ingestion from Kinesis
  Data Streams, MSK, or S3 without Lambda. Lower latency than Lambda-
  based ingestion. Requires IAM role for source to write to OpenSearch.
- **Cross-cluster search (2023-2024):** Connect multiple domains for
  federated search. Use `connections` API to establish peering.
- **gp3 EBS default (2022-2023):** gp3 replaces gp2 as the default
  EBS type. Higher baseline IOPS (3,000 vs gp2's 250). Provisioning
  tip: gp3 is cheaper and faster than gp2 — use gp3 always.
- **Graviton (g-series) instance types (2022-2024):** `r6g.search`,
  `c6g.search`, `m6g.search` offer ~20% better price/performance over
  Intel (no `-g` suffix). Default to Graviton for new clusters.
- **OpenSearch 2.x (2022-2024):** Anomaly detection, k-NN boosts,
  session-based search, streaming ingestion improvements. Provisioning
  tip: use OpenSearch 2.11+ for latest features.
- **AWS-managed service updates (rolling):** OpenSearch applies
  engine upgrades during the maintenance window. Provisioning tip:
  set `AutomatedSnapshotStartHour` to control timing; do NOT use the
  default random window.

## Domain

AWS CloudOps / OpenSearch Service Provisioning & Search Topology Design.

## AWS documentation

- **Amazon OpenSearch Service Developer Guide** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html
- **Managed domains** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/createupdatedomains.html
- **OpenSearch Serverless** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html
- **Multi-AZ domains** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-multiaz.html
- **Dedicated master nodes** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-dedicatedmasternodes.html
- **Encryption at rest** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/encryption-at-rest.html
- **Fine-grained access control** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html
- **UltraWarm storage** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html
- **Cold storage** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/cold-storage.html
- **Sizing domains** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html
- **Vector search** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/knn.html
