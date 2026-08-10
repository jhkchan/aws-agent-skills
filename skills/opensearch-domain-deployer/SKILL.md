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
10-step provisioning procedure and emits a READY_TO_DEPLOY checklist with
verification commands.

## Activation keywords

create OpenSearch, provision OpenSearch, managed cluster, OpenSearch
Serverless, data nodes, dedicated master nodes, UltraWarm, cold storage,
Multi-AZ, 3-zone deployment, instance type, EBS storage, gp3, io1,
encryption at rest, encryption in transit, TLS, KMS, VPC access, public
access, fine-grained access control, FGAC, IAM master user, Cognito,
snapshot repository, shard count, replica count, vector search collection,
streaming ingestion.

## Invocation contract (hard requirement)

When this skill is invoked with a domain-provisioning request (domain
name, instance type, workload shape, region, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
"Output format" using the literal all-caps labels `DOMAIN:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface with prose,
headings, or disclaimers — emit the block as the first lines of the response.

## Mindset

**One-line takeaway:** OpenSearch correctness is decided at creation
time. Encryption at rest, FGAC mode, VPC vs public access, and Multi-AZ
topology are impossible or disruptive to change later — treat each as a
one-way door and force an explicit decision before `create-domain`.

Three misconceptions dominate OpenSearch misdesign:
- **"Pick the largest instance and scale down later."** OpenSearch charges
  per instance-hour regardless of utilization. Size based on storage +
  the shard-count heuristic (1 shard per 30-50 GB), not "we might need it."
- **"Public access with IP allowlist is fine for production."** An IP
  allowlist is a network control, not authentication. VPC-only with
  FGAC + IAM is the production baseline.
- **"Dedicated master nodes are optional."** Without dedicated masters,
  cluster-state changes consume CPU on data nodes — query latency spikes
  during recovery. Mandatory for > 10 data nodes or latency-sensitive workloads.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Deployment type | Managed cluster vs Serverless |
| Step 2 — Instance types | t3/r6g/m6g/c6g.search selection |
| Step 3 — Multi-AZ + dedicated masters | Production topology |
| Step 4 — Storage (EBS, instance) | gp3 vs io1 vs instance-store |
| Step 5 — Encryption | KMS at-rest, TLS in-transit |
| Step 6 — Network + FGAC | VPC vs public, IAM vs Cognito |
| Step 7 — Indexing (shards, replicas) | Shard count, replica count |
| Step 8 — Snapshots | Automated + manual to S3 |
| Step 9 — UltraWarm / cold storage | Tiered storage for cost |
| Step 10 — Serverless / vector search | Latest 2023-2026 features |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/topology-and-indexing.md | Deep Multi-AZ + shard math |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Reasoning framework (why provisioning order matters)

OpenSearch configurations have **dependency and immutability semantics**.
The four one-way doors decided at creation time:

1. **Encryption at rest** — MUST enable at creation. Cannot be added to
   an existing domain without new domain + reindex.
2. **FGAC mode** (IAM vs Cognito) — chosen at creation. Switching modes
   requires full reindex via remote reindex.
3. **VPC vs public access** — cannot switch post-creation. No modify path.
4. **Multi-AZ topology** — requires node count multiple of 3. Adding a
   third AZ to a 2-AZ cluster requires disruptive node-count change.

Additionally: instance type changes require blue-green deployment (multi-hour
shard migration). Shard count changes require `_split` or `_shrink` (disruptive).

The full configuration dependency graph (which settings are immutable,
which silently downgrade, which enable downstream features) is in
`references/topology-and-indexing.md`.

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with OpenSearch access | Required | `aws sts get-caller-identity` |
| Region selected | Domains are region-scoped | `aws configure get region` |
| Domain name unique in account-region | Name is immutable; endpoint derives from it | `aws opensearch describe-domain --domain-name <name>` |
| VPC ID + subnets in 3 AZs (Multi-AZ) | Multi-AZ requires 3 AZs | `aws ec2 describe-subnets` — confirm 3 distinct AZs |
| Security group with port 443 inbound | OpenSearch uses HTTPS | `aws ec2 describe-security-groups --group-ids <sg>` |
| KMS key ARN (if encryption with CMK) | Custom encryption requires CMK in same region | `aws kms describe-key --key-id <cmk-id>` |
| IAM role ARN for master user (if FGAC) | FGAC requires master user | `aws iam get-role --role-name <role>` |
| Cognito user pool + identity pool (if Cognito FGAC) | Required for Cognito-based FGAC | `aws cognito-idp describe-user-pool --user-pool-id <pool>` |
| S3 bucket + IAM role for manual snapshots | Manual snapshots require registered repository | `aws s3api head-bucket --bucket <bucket>` |
| Workload description (data size, query pattern) | Drives instance/shard/replica decisions | Captured in prompt |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Sizing heuristics (quick reference)

Full detail in `references/topology-and-indexing.md`.

**Shard count:** `ceil(total_data_size_gb / 30)` for write-heavy, `/ 50`
for read-heavy. Over-sharding small datasets wastes overhead; use 1 shard
for < 10 GB.

**Storage capacity:** `total_storage = raw_data × (1 + replica_count) × 1.1`
(10% overhead + 15% free-space watermark). Required data nodes =
`ceil(total_storage / per_node_storage)`. Round UP to multiple of 3 for Multi-AZ.

**Dedicated masters:** mandatory for > 10 data nodes. Type: `c6g.large.search`
for up to 15 data nodes; `c6g.2xlarge.search` for 15-30; `c6g.4xlarge.search` for 30+.

**Heap:** 50% of instance RAM, capped at 31 GB (compressed oops boundary).

## 10-step provisioning procedure

### Step 1 — Deployment type: managed cluster vs Serverless (immutable)

**Decision:**
- **Unpredictable/bursty workload** → OpenSearch Serverless (auto-scaling,
  pay-per-use). Does NOT support UltraWarm, cold storage, dedicated masters,
  or cross-cluster search.
- **Steady-state + predictable** → Managed cluster (full feature set).
- **Vector search only** → Serverless VECTORSEARCH collection.
- **Needs UltraWarm/cold storage** → Managed cluster (Serverless lacks tiered storage).

### Step 2 — Instance types (managed cluster)

| Family | Examples | Optimized for | Use when |
|---|---|---|---|
| `r6g.search` / `r7g.search` | r6g.large to r6g.4xlarge | Memory | **Production DEFAULT** |
| `c6g.search` | c6g.large to c6g.2xlarge | Compute | Aggregations, ML; dedicated masters |
| `m6g.search` | m6g.large to m6g.4xlarge | Balanced | Mixed workloads |
| `i3.search` | i3.large to i3.2xlarge | Instance storage (NVMe) | Very high IOPS; log analytics |
| `t3.search` | t3.small to t3.medium | Burst | **Dev/test ONLY** |
| Legacy (`t2`,`m3`,`m4`,`c4`,`r3`,`r4`,`i2`) | — | — | **DO NOT USE — end-of-life** |

**Size by workload:**
- Dev/test: `t3.small.search` × 1 (no Multi-AZ).
- Small production (< 50 GB): `r6g.large.search` × 3.
- Mid production (50-500 GB): `r6g.2xlarge.search` × 3-6 (Multi-AZ).
- Large production (500 GB-5 TB): `r6g.4xlarge.search` × 6-12 + 3 dedicated masters.
- Very large (5+ TB): shard across domains OR use UltraWarm/cold storage.

**NEVER use `t3.small.search` for production** — CPU credits deplete and
throttle under sustained traffic.

### Step 3 — Multi-AZ + dedicated master nodes

Multi-AZ (3-zone) is the primary resilience control. **Instance count must
be a multiple of 3.**

- Enable `ZoneAwarenessEnabled=true` + `AvailabilityZoneCount=3`.
- OpenSearch places primary and replica shards in different AZs.
- A 3-node cluster with `replica=1` tolerates one AZ loss.

**Dedicated masters** (3 — one per AZ):
- Mandatory for > 10 data nodes, latency-sensitive workloads (p99 < 100 ms),
  or frequent index creation.
- Master type: `c6g.large.search` (≤15 data nodes), `c6g.2xlarge.search`
  (15-30), `c6g.4xlarge.search` (30+).
- Masters are CPU-bound, not memory-bound. Use `c6g`, not `r6g`.

**NEVER use a 2-AZ topology with odd node count** — uneven shard
distribution makes one AZ a SPOF.

### Step 4 — Storage (EBS vs instance-store)

| Volume type | IOPS | Use when |
|---|---|---|
| `gp3` (default) | 3,000 baseline, up to 16,000 | **DEFAULT CHOICE** — most production |
| `io1` | up to 64,000 provisioned | High-IOPS; consistent latency |
| `standard` (magnetic) | low | **DO NOT USE — legacy** |

- EBS size: 10 GB - 6 TB (gp3). Plan for 15% free (write-block watermark at 85%).
- Instance-store (NVMe): `i3.search` only. Higher IOPS but ephemeral — data
  lost on instance failure. Use with `replica >= 1`.

**Common mistake:** sizing EBS for raw data without the replica + overhead
multiplier. A 500 GB index with 1 replica needs 500 × 2 × 1.1 = 1.1 TB.

### Step 5 — Encryption (at-rest + in-transit)

**Encryption at rest:**
- **MUST enable at domain creation.** Cannot be added later.
- Uses AWS KMS. Default: AWS-managed key. For compliance: customer CMK.

**Encryption in transit (TLS):**
- Recommended at creation. Can enable post-creation but triggers rolling
  node replacement disconnecting clients for 10-30 minutes.
- Use `Policy-Min-TLS-1-2-2019-07` (TLS 1.2 minimum). Never allow TLS 1.0/1.1.

```bash
aws opensearch create-domain ... \
  --encryption-at-rest-options Enabled=true,KmsKeyId=arn:aws:kms:...:alias/<cmk> \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07
```

### Step 6 — Network access + fine-grained access control (FGAC)

**Network access:**

| Mode | Use when |
|---|---|
| VPC-only | **PRODUCTION.** Network isolation; security group controls ingress. |
| Public | Dev/test only. IP allowlist is a network control, not authentication. |

**FGAC modes (mutually exclusive — choose at creation):**

| Mode | Master user | Use when |
|---|---|---|
| IAM master user | IAM role ARN | Programmatic access; AWS-native orgs |
| Cognito user pool | Cognito pool + identity pool | Human users; SSO; web-app dashboards |
| IP-only (no FGAC) | N/A | **DO NOT USE for production** |

**Common mistake:** public access with IP allowlist for "production." Always
use VPC-only access with FGAC for production.

### Step 7 — Indexing (shard count, replica count)

- **Shard count:** apply the 30-50 GB per shard rule. Set at index creation
  via `"number_of_shards": N`. Change post-creation: `_split`/`_shrink`
  (disruptive).
- **Replica count:** default 1. Set via `"number_of_replicas": N`.
  Changeable at runtime (no disruption). Multi-AZ places replicas in
  different AZs.

| Replica | Storage multiplier | Use when |
|---|---|---|
| 0 | 1x | Dev/test only (data loss on failure) |
| 1 | 2x | **Production standard** |
| 2 | 3x | High availability (rare; cost) |

**NEVER over-shard a small dataset.** A 1 GB index with 5 shards wastes
overhead — use 1 shard.

### Step 8 — Snapshots (automated + manual)

- **Automated:** daily to AWS-managed S3. Retention 1-35 days (configurable).
  Used for point-in-time recovery to same or new domain.
- **Manual:** customer-managed S3 bucket. Requires "snapshot repository"
  registered via `PUT _snapshot/<repo>`. Used for long-term retention,
  cross-cluster migration, backup before upgrades.

Full snapshot repository registration and restore CLI is in
`references/provisioning-cli-commands.md`.

**NEVER rely on automated snapshots as the ONLY backup.** For long-term
retention or cross-region DR, configure manual snapshots.

### Step 9 — UltraWarm and cold storage (managed cluster only)

Serverless does NOT support these. Managed cluster only.

- **UltraWarm:** read-only warm tier. ~50% cheaper than hot. Indices become
  READ-ONLY after migration. Hot→warm via ISM; warm→hot requires reindex.
- **Cold storage:** read-only archive on S3. ~80% cheaper. Recall takes
  minutes-hours. Requires UltraWarm enabled.

**ISM lifecycle:** hot (active) → warm (7d) → cold (30d) → delete (365d).

**NEVER use UltraWarm as a write target** — READ-ONLY. Writes must
complete on hot tier before ISM migrates.

### Step 10 — OpenSearch Serverless / vector search / streaming ingestion

- **OpenSearch Serverless:** auto-scaling, pay-per-use (OCU billing). No
  capacity management. Separate API (`opensearchserverless`).
- **Vector search collections:** `--type VECTORSEARCH`. Optimized for k-NN
  similarity search (HNSW, IVF). For RAG/generative AI workloads.
- **Streaming ingestion:** direct from Kinesis, MSK, or S3 without Lambda.
  Lower latency than Lambda-based ingestion.
- **Cross-cluster search:** connect multiple domains for federated search.

**Common mistake:** provisioning a managed cluster for vector-search-only
workload. Serverless VECTORSEARCH is cheaper and simpler for pure k-NN.

## NEVER do these things

1. **NEVER use public access for a production OpenSearch domain.** Public
   access exposes the endpoint to internet scanning. VPC-only with FGAC + IAM.

2. **NEVER forget to enable encryption at rest at domain creation.**
   Adding it later requires a new domain + full reindex + client repoint.

3. **NEVER use `t3.small.search` for production.** CPU credits deplete
   under sustained traffic. Use `r6g.search` or `r7g.search`.

4. **NEVER provision a 2-AZ topology with odd node count.** Multi-AZ
   requires 3 AZs and node count multiple of 3. Uneven allocation = SPOF.

5. **NEVER skip dedicated master nodes for clusters > 10 data nodes.**
   Without dedicated masters, cluster-state updates spike query latency
   during recovery. Use 3 dedicated masters (one per AZ).

Extended anti-patterns (JVM heap cap, TLS policy, IP-only FGAC, automated
snapshot reliance, FGAC mode switch, UltraWarm writes, EOL instances) are
documented in `references/topology-and-indexing.md`.

## Error handling

| Error | Cause | Fix |
|---|---|---|
| `ResourceAlreadyExistsException` | Domain name taken | Check existing config; update mutable settings or create new domain |
| Encryption-at-rest enable fails on existing domain | Cannot add post-creation | Create NEW domain with encryption, reindex via `_remote/reindex` |
| Multi-AZ create with uneven node count | `InstanceCount` not divisible by 3 | Round UP to next multiple of 3 |
| Dedicated master toggle during update | Blue-green deployment (1-4 hours) | Enable at creation; toggle requires maintenance window |
| `RepositoryMissingException` | Snapshot repo not registered | Register via `PUT _snapshot/<repo>` before taking snapshots |
| FGAC mode switch fails | IAM↔Cognito not supported via update | Create NEW domain with desired FGAC mode, reindex |
| Cluster stuck in `PROCESSING` | Blue-green on large cluster (1-4 hours) | `aws opensearch describe-domain --query 'DomainStatus.Processing'` — wait for false |

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
against. Every invocation MUST produce output matching this contract or
the response is rejected.

### Required output structure

Every response MUST be a single block with these literal labels, in order,
as the first lines of the response (no preamble, no prose, no disclaimers):

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
   with [✓] or [✗].** Every row must appear with an explicit status marker.
   The eval harness asserts a minimum row count.

2. **NEVER omit the instance type recommendation.** Must specify the exact
   `.search`-suffixed type (e.g., r6g.large.search). "TBD" or "memory-optimized"
   is rejected.

3. **NEVER recommend public access for production.** VPC-only is the
   production default. Only dev/test may use public, with explicit note.

4. **NEVER emit a checklist without the encryption-at-rest status.**
   Encryption at rest is immutable after creation — omitting it leaves the
   operator blind to a one-way door decision.

5. **NEVER substitute lowercase or markdown-styled labels for the literal
   all-caps `DOMAIN:`, `VERDICT:`, `CHECKLIST:`, `VERIFICATION_COMMANDS:`.**

6. **NEVER preface the checklist with prose, headings, or disclaimers.**
   The `DOMAIN:` line must be the first line of the response.

## Recent AWS features (2022-2026)

- **OpenSearch Serverless (2022-2023):** Auto-scaling, pay-per-use. Separate
  API. Does NOT support UltraWarm, cold storage, dedicated masters.
- **Vector search collections (2023-2024):** Serverless `VECTORSEARCH`. k-NN
  similarity search (HNSW, IVF). For RAG/generative AI workloads.
- **Streaming ingestion (2023-2024):** Direct from Kinesis, MSK, or S3
  without Lambda. Lower latency than Lambda-based ingestion.
- **Cross-cluster search (2023-2024):** Connect multiple domains for
  federated search via `connections` API.
- **gp3 EBS default (2022-2023):** gp3 replaces gp2. Higher baseline IOPS
  (3,000 vs gp2's 250). Cheaper and faster.
- **Graviton (g-series) instance types (2022-2024):** `r6g`, `c6g`, `m6g`
  offer ~20% better price/performance over Intel. Default for new clusters.
- **OpenSearch 2.x (2022-2024):** Anomaly detection, k-NN boosts, session-
  based search, streaming ingestion. Use OpenSearch 2.11+.

## References

- `references/topology-and-indexing.md` — managed vs Serverless feature
  matrix, Multi-AZ topology math, dedicated master sizing, EBS vs instance-
  store selection, shard/replica heuristics, UltraWarm/cold storage lifecycle,
  vector search collection sizing, configuration dependency graph.
- `references/provisioning-cli-commands.md` — full copy-pasteable CLI
  sequence for all provisioning steps, including managed cluster creation,
  Serverless collection setup, vector search, snapshot registration, ISM
  policies, CloudWatch alarms, and Terraform equivalents.

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
