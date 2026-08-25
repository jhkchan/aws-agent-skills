---
name: neptune-db-cluster-deployer
description: 'Provisions Amazon Neptune DB clusters (graph database) with production defaults: cluster creation (instance type, cluster size, reader replicas), VPC networking (DB subnet group across >=3 AZs, security groups on port 8182), encryption (KMS at creation — immutable), auto-failover (Multi-AZ with reader promotion), parameter groups (neptune_enforce_ssl, neptune_query_timeout), IAM database auth, loading data (bulk load from S3 via the Neptune Loader), querying (Gremlin, SPARQL, openCypher), Neptune Streams, snapshot/restore, and the Neptune Analytics boundary. Emits a READY_TO_DEPLOY checklist. Use when creating a Neptune DB cluster, sizing writer/reader instances, designing a Multi-AZ graph topology, hardening TLS/IAM, loading graph data from S3, or choosing between Neptune DB and Neptune Analytics. Triggers: create Neptune, provision graph database, Neptune cluster, Gremlin, SPARQL, openCypher, Neptune bulk load, Neptune Streams, neptune_enforce_ssl, Neptune Multi-AZ.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with neptune, ec2, kms, iam, and s3 access. Works with Terraform aws_neptune_cluster / aws_neptune_cluster_instance resources and CloudFormation AWS::Neptune::DBCluster / AWS::Neptune::DBInstance templates.'
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
  tags: aws, neptune, graph-database, cloudops, deploy, databases, provisioning, gremlin, sparql, opencypher, multi-az, encryption, iam-db-auth, neptune-streams
  dependencies: aws-orchestrator
  keywords: aws, neptune, graph database, cloudops, deploy, provisioning, gremlin, sparql, opencypher, multi-az, failover, encryption at rest, tls, iam database auth, subnet group, parameter group, neptune_enforce_ssl, neptune_query_timeout, bulk load, neptune loader, neptune streams, reader instance
  when_to_use: Invoke when the user wants to create a new Amazon Neptune DB cluster (graph database), size writer and reader instances, design a Multi-AZ topology with reader promotion, harden TLS via neptune_enforce_ssl, enable IAM database auth, load graph data from S3 via the Neptune Loader, query via Gremlin / SPARQL / openCypher, enable Neptune Streams for change capture, or generate provisioning CLI commands / IaC templates. Do NOT invoke for Neptune Analytics (analytics graph service, separate API), for self-managed Neo4j / JanusGraph on EC2, or for auditing an existing Neptune cluster's posture.
---

# Neptune DB Cluster Deployer

An AWS CloudOps agent skill that provisions Amazon Neptune DB clusters
(graph database) with correct defaults. The skill walks the operator
through a provisioning procedure, captures the operator's instance,
topology, security, and query-language decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create Neptune, provision Neptune, Neptune cluster, graph database,
Gremlin, SPARQL, openCypher, Neptune Multi-AZ, Neptune reader instance,
Neptune bulk load, Neptune Loader, Neptune Streams, Neptune parameter
group, neptune_enforce_ssl, neptune_query_timeout, IAM database auth,
Neptune subnet group, Neptune KMS encryption, db.r6g.large,
db.r6g.8xlarge, db.x2gdb.16xlarge.

## STRICT output contract

When this skill is invoked with a Neptune-provisioning request
(cluster name, instance class, workload shape, region, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `NEPTUNE:`, `VERDICT:`, `CHECKLIST:`, and
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
| Step 1 — Neptune DB vs Neptune Analytics | Boundary call (avoid the common misroute) |
| Step 2 — Instance class + cluster size | Sizing writer + readers |
| Step 3 — Multi-AZ with reader promotion | Production topology |
| Step 4 — Network + security (VPC, subnet group, SG) | VPC wiring |
| Step 5 — Encryption (KMS at creation, immutable) | TLS + at-rest |
| Step 6 — Parameter groups | neptune_enforce_ssl, neptune_query_timeout |
| Step 7 — IAM database auth | Token-based access |
| Step 8 — Bulk load from S3 | Initial data ingest |
| Step 9 — Query languages (Gremlin, SPARQL, openCypher) | API surface |
| Step 10 — Streams / snapshots / recent features | Change capture, recovery |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/instance-and-topology.md | Writer/reader math, instance classes |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

**One-line takeaway:** Neptune correctness is decided at creation
time. Encryption at rest (KMS) and the cluster's VPC/subnet placement
are immutable post-creation — modifying them requires a snapshot
restore into a new cluster. The procedure treats each one-way door as
an explicit decision before the `create-db-cluster` call.

Three misconceptions dominate Neptune misdesign at provisioning time:

- **"Neptune Analytics is just a bigger Neptune DB."** It is not.
  Neptune DB is a transactional (OLTP) graph database with a
  writer-replica cluster, Multi-AZ failover, and Gremlin/SPARQL/
  openCypher endpoints. Neptune Analytics is a separate analytics
  (OLAP) service for graph algorithms on large datasets with its own
  API (`create-graph`), no writer/replica split, and no Gremlin
  transactions. They share query languages but not the data plane.
  Pick the service before any other decision — this skill only
  provisions Neptune DB.

- **"Set encryption at rest after the cluster is running."** Neptune
  encryption at rest is **immutable**: it MUST be set at creation via
  `--storage-encrypted` (and an optional customer CMK via
  `--kms-key-id`). Adding it later requires snapshot → restore into a
  new encrypted cluster. Same for TLS — `neptune_enforce_ssl=1` in
  the parameter group applied at creation locks the cluster to TLS-only.

- **"A single instance is fine for production."** Neptune's
  writer-only topology has no failover. Multi-AZ requires at least one
  reader instance in a different AZ; promotion takes ~30 seconds. The
  minimum production topology is 1 writer + 1 reader across two AZs,
  with `--deletion-protection` on the cluster.

## Configuration dependency graph (novel heuristic)

Neptune configurations are NOT independent. Many are immutable after
creation, others silently downgrade. Use this graph both to sequence
provisioning and to debug "why can't I add this?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Engine version (`1.3.x.x`) | none — `create` argument | engine upgrades apply in maintenance window; rolling with brief endpoint flapping | Gremlin 3.7+, openCypher, server-side plan cache |
| Instance class | none — `create` argument | changeable via `modify-db-instance` with rolling reboot | memory budget, CPU for traversal depth |
| Writer + reader replicas | DB subnet group spanning >=2 AZs (Multi-AZ) | writer-only = NO failover; promotion needs >=1 reader in different AZ | Multi-AZ, read scaling, failover |
| Storage / IOPS | set at cluster create | **IMMUTABLE** — change requires snapshot/restore | throughput for write-heavy graphs |
| Encryption at rest (KMS) | `--storage-encrypted` + optional `--kms-key-id` at creation | **CANNOT be added post-creation** without snapshot/restore | compliance (HIPAA, PCI, SOC2) |
| TLS / neptune_enforce_ssl | parameter group applied at creation | changing requires instance reboot; mixed TLS is messy | TLS-only clients, sniffing defense |
| IAM database auth | `--enable-iam-database-authentication` at creation | can be enabled post-create via modify but triggers rolling reboot; non-IAM auth still works in parallel unless disabled | token-based access |
| DB subnet group | VPC + >=1 subnet; >=3 AZs for Multi-AZ | subnets CANNOT be removed once added; only added | VPC-only addressing |
| Security group | VPC | port 8182 inbound from application SG | network isolation |
| Parameter group | none — `create` argument | parameter changes apply on next reboot | neptune_enforce_ssl, neptune_query_timeout, labs modes |
| Bulk load from S3 | S3 bucket + IAM role with `neptune-load` trust + `s3:GetObject`; source in same region | concurrent loads on the same cluster conflict; loader is idempotent per `load_id` | initial ingest |
| Neptune Streams | `neptune_streams=1` in parameter group + (recommended) Kinesis/Lambda consumer | enabling/disabling requires instance reboot; stream records resume after reboot | change data capture, replication |
| Snapshot (automated) | `--backup-retention-period > 0` at cluster create | restore creates a NEW cluster; snapshot is cluster-scoped | point-in-time recovery |
| Deletion protection | `--deletion-protection` at cluster create | with protection on, `delete-db-cluster` fails until disabled | accidental-delete defense |

**The immutable rows are the ones a baseline model misses.** Engine
version (rolling), storage config, encryption at rest, and VPC/subnet
placement are decided at creation time. The procedure below forces an
explicit decision on each before the `create-db-cluster` call.

**Cross-dependency gotchas:**
- Enabling `neptune_enforce_ssl=1` on an existing cluster requires a
  rolling instance reboot — plaintext clients drop. Enable at creation.
- IAM auth and password auth can coexist; to enforce IAM-only, do NOT
  set a password and rely on IAM tokens. Mixed mode is a common source
  of "why did this auth succeed?" confusion.
- The Neptune Loader only reads S3 buckets in the SAME region as the
  cluster. Cross-region loads require replicating the bucket first.
- A Multi-AZ cluster with only 1 instance (writer) has NO failover
  target. The cluster endpoint resolves to the writer; on writer loss
  with no readers, the cluster is unavailable until a new instance is
  promoted.

## Expert heuristic: graph sizing (memory budget)

Neptune is memory-bound for traversal performance. The graph must fit
in the buffer cache for sub-second queries; cache misses fall through
to the storage layer (10-100x slower). A baseline model quotes the
instance spec-sheet memory; this heuristic gives the real budget.

```text
usable_buffer_cache = instance_memory_bytes × 0.60
# ~60% of memory is the working buffer cache budget. Neptune reserves
# the rest for OS, JVM internal state, connection state, and
# copy-on-write during snapshot.

# Working set rule (Gremlin/SPARQL property graph):
required_memory = vertices_bytes + edges_bytes + (3 × indexes_bytes)
# Neptune maintains property + edge indexes consuming ~3x the raw
# edge data. Indexes are what make traversals fast; never size them out.

# Example: 200M vertices (200 B avg) + 1B edges (80 B avg)
# vertices=40 GB, edges=80 GB, indexes=240 GB -> 360 GB required
# -> db.r6g.12xlarge (384 GB) is the floor;
#    db.r6g.16xlarge (512 GB) for headroom
```

**Read-scaling note:** readers scale read traversals but NOT writes —
Neptune has exactly one writer per cluster. For high write rates,
scale up the writer instance class, not out.

## Expert heuristic: failover promotion semantics

A baseline model says "Multi-AZ gives you failover" without explaining
what gets promoted and how long it takes. This is the load-bearing
detail for production SLAs.

- **Cluster endpoint is stable.** Neptune exposes a single cluster
  endpoint that always points to the current writer. On failover, the
  endpoint repoints automatically — clients reconnect via the cluster
  endpoint without code changes.
- **Promotion time: typically ~30 seconds** (instance detection +
  reader promotion + endpoint DNS update).
- **Data loss window: zero committed transactions.** Neptune storage
  is cluster-shared (6-way storage replication); a promoted reader
  sees all writes the old writer committed. In-flight client writes
  during the ~30s window get errors and must be retried.
- **Reader-only failover is per-cluster.** If the writer is in AZ-a
  and all readers are also in AZ-a (anti-pattern), failover cannot
  move the writer out of AZ-a. Spread readers across AZs.

**Practical implication:** if the workload's SLA cannot tolerate a
~30-second client reconnect, the application must handle retry/
idempotency. Neptune itself recovers automatically.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Neptune access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Neptune clusters and subnet groups are region-scoped | `aws configure get region` |
| VPC ID + at least 2 subnets in different AZs (3+ preferred) | Neptune is VPC-only; Multi-AZ requires multi-AZ subnet group | `aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc>"` — confirm >=2 distinct `AvailabilityZone` values |
| Cluster name unique in this region | Names are region-unique | `aws neptune describe-db-clusters --db-cluster-identifier <name>` returns `DBClusterNotFound` |
| KMS key ARN (if encryption with customer CMK) | Custom encryption requires a CMK in the same region | `aws kms describe-key --key-id <cmk-id>` — confirm `Enabled=true` |
| Security group with port 8182 inbound from application SG | Wrong port = silent connectivity failure; Neptune listens on 8182 | `aws ec2 describe-security-groups --group-ids <sg>` — verify inbound rule on 8182 |
| Workload description (graph size, query depth, write rate) | Drives instance class, replica count, parameter group decisions | Captured in the prompt or follow-up question |
| S3 bucket + IAM role for bulk load (if loading data) | Loader needs IAM role with `s3:GetObject` and Neptune trust policy; bucket in same region | `aws iam get-role --role-name <role>`; bucket in same region |
| Engine choice (DB vs Analytics) | Neptune Analytics is a separate service; this skill is DB only | If the user asks for graph algorithms / large-scale analytics, redirect to Neptune Analytics |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Neptune DB vs Neptune Analytics (boundary call)

The single highest-impact Neptune decision is which SERVICE to use.
This skill only provisions Neptune DB. If the user wants Neptune
Analytics, stop and redirect.

**Decision tree:**

```text
What is the workload shape?
├── Transactional (OLTP) — point lookups, short traversals,
│   real-time app queries, frequent writes
│   └── Neptune DB  (this skill)
├── Analytical (OLAP) — PageRank / connected-components /
│   community-detection on a large static graph, batch
│   └── Neptune Analytics  (NOT this skill — separate API:
│       aws graph create-graph, no writer/reader split)
└── Both  └── Neptune DB for transactions + export to Neptune
                Analytics for batch algorithm runs
```

**Feature comparison:**

| Feature | Neptune DB | Neptune Analytics |
|---|---|---|
| API family | `aws neptune create-db-cluster` | `aws graph create-graph` (different CLI namespace) |
| Topology | writer + reader replicas (Multi-AZ) | single graph (no writer/reader split) |
| Failover | YES (writer promotion) | N/A (recreate on failure) |
| Gremlin transactions | YES | NO (read-only analytic queries) |
| SPARQL | YES | NO |
| openCypher | YES | YES |
| Graph algorithms (built-in) | NO (write your own Gremlin) | YES (PageRank, BFS, etc.) |
| Storage | cluster-shared (6-way) | ephemeral snapshot-loaded |
| Pricing | instance-hour + storage + IO | GB-hour (memory) + snapshot |

**Common mistake:** provisioning Neptune DB for a PageRank workload.
Neptune DB has no built-in algorithm library; running PageRank in
Gremlin on a large graph will time out and exhaust memory. Use Neptune
Analytics.

## Step 2 — Instance class + cluster size

Neptune offers `db.r5`, `db.r6g`, `db.r6i`, `db.x2g` families.
Memory-bound graphs favor `r6g`/`x2g`. Avoid `t3`/`t4g` burstable for
production (Neptune is not supported on burstable in some regions).

**Cluster size by workload:**

- **Dev / test:** 1 writer instance, `db.r6g.large`. No failover.
- **Small production (read-heavy, < 100 GB working set):** 1 writer +
  1 reader (Multi-AZ), `db.r6g.2xlarge`.
- **Mid production (100-500 GB, mixed read/write):** 1 writer + 2
  readers across 3 AZs, `db.r6g.8xlarge`.
- **Large production (500 GB+, deep traversals):** 1 writer + 3+
  readers, `db.r6g.16xlarge` or `db.x2gdb.16xlarge`.

**Sizing rules:**
- Plan for 60% of instance memory as the buffer cache budget (see
  Expert heuristic above). The graph working set (vertices + edges +
  3x indexes) MUST fit in the buffer cache for sub-second traversals.
- Readers scale reads, not writes. There is exactly one writer per
  Neptune cluster.
- Cluster storage auto-scales; do NOT size for storage, size for
  memory.

## Step 3 — Multi-AZ with reader promotion

Multi-AZ is the primary resilience control for Neptune DB.

**Requirements:**
- At least 1 reader instance in a DIFFERENT AZ than the writer.
- DB subnet group spanning at least 2 AZs (3+ preferred for
  spreading readers).
- Deletion protection enabled on the cluster.

**Behavior on writer failure:**
- Neptune detects writer loss (health check).
- A reader in a different AZ is promoted to writer (~30 seconds).
- The cluster endpoint repoints to the new writer automatically.
- Clients reconnect via the cluster endpoint — no code change.
- Data loss window: zero committed transactions (cluster-shared
  storage).

**Common mistake:** subnet group with only one AZ. Multi-AZ cannot
place the reader in a different AZ, and the cluster silently degrades
to writer-only (no failover). Verify the subnet group spans >=2 AZs
before `create-db-cluster`.

## Step 4 — Network + security (VPC, subnet group, security group)

Neptune is **VPC-only** — there is no public IP option. All clusters
live inside a VPC and are reachable only from inside the VPC (or via
a bastion / VPN / PrivateLink).

**DB subnet group creation:**

```bash
aws neptune create-db-subnet-group \
  --db-subnet-group-name prod-neptune-subnet \
  --db-subnet-group-description "Multi-AZ subnet group for prod Neptune" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --tags Key=Environment,Value=production
```

Verify the subnets span >=2 AZs (3+ preferred):

```bash
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZs for Multi-AZ
```

**Security group rules:**

```bash
# Inbound: allow the application's SG to reach Neptune on port 8182
aws ec2 authorize-security-group-ingress \
  --group-id sg-neptune123 \
  --protocol tcp \
  --port 8182 \
  --source-security-group-id sg-app456
```

**NEVER** open port 8182 to `0.0.0.0/0` — even with TLS and IAM auth,
this exposes the cluster to internet scanning. Always scope inbound to
the application's SG.

## Step 5 — Encryption (KMS at creation, immutable)

Neptune encryption at rest is **immutable**: set at creation via
`--storage-encrypted`. Adding it later requires a snapshot → restore
into a new encrypted cluster.

- `--storage-encrypted` enables encryption (AWS-managed KMS key by
  default).
- `--kms-key-id <cmk-arn>` uses a customer-managed CMK (required for
  most compliance regimes — HIPAA, PCI, SOC2).
- TLS in transit is controlled by the parameter group via
  `neptune_enforce_ssl=1` (see Step 6). Pair at-rest + in-transit
  encryption for defense in depth.

**Common mistake:** planning to "enable encryption later." A
non-encrypted Neptune cluster CANNOT be encrypted without a full
snapshot/restore cycle. Decide at creation.

## Step 6 — Parameter groups (neptune_enforce_ssl, neptune_query_timeout)

Parameter groups control Neptune runtime behavior. Most parameters
require an instance reboot to take effect — set them at cluster
creation in the DB cluster parameter group.

| Parameter | Default | Recommended | Why |
|---|---|---|---|
| `neptune_enforce_ssl` | `0` (off) | `1` (on) for all production | Forces TLS-only connections; plaintext rejected. Defense against network sniffing. |
| `neptune_query_timeout` | `120000` (ms) | `30000` (30s) for OLTP; `120000+` for analytics | Caps runaway traversals. Long-running queries consume CPU/memory and starve other queries. |
| `neptune_streams` | `0` (off) | `1` (on) if change capture needed | Enables Neptune Streams for CDC (see Step 10). |
| `neptune_lab_mode` | varies | Leave at default unless AWS support advises | Labs features may change; do not enable in production without testing. |

**Applying a parameter group:**

```bash
aws neptune create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --db-parameter-group-family neptune1 \
  --description "Production Neptune cluster parameter group"

aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --parameters \
    ParameterName=neptune_enforce_ssl,ParameterValue=1,ApplyMethod=immediate \
    ParameterName=neptune_query_timeout,ParameterValue=30000,ApplyMethod=immediate
```

Attach the parameter group at `create-db-cluster` via
`--db-cluster-parameter-group-name`.

**Common mistake:** enabling `neptune_enforce_ssl=1` on an existing
production cluster without a maintenance window. The rolling reboot
drops plaintext clients. Enable at creation.

## Step 7 — IAM database auth

Neptune supports IAM database auth — token-based access using AWS SigV4
instead of static passwords. Recommended for production; pairs with
`neptune_enforce_ssl=1`.

**Enable at creation:**

```bash
aws neptune create-db-cluster ... \
  --enable-iam-database-authentication
```

**IAM policy for Neptune access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["neptune-db:Connect"],
      "Resource": "arn:aws:neptune:<region>:<account>:cluster/<cluster-name>"
    }
  ]
}
```

**Common gotchas:**
- IAM auth and password auth can coexist. To enforce IAM-only, do NOT
  set a password and rely on IAM tokens.
- IAM tokens are SigV4-derived — short-lived (~15 minutes). The
  Gremlin/SPARQL driver must refresh tokens automatically (most modern
  drivers do; verify your client lib).
- IAM auth requires TLS — pair with `neptune_enforce_ssl=1`.

## Step 8 — Bulk load from S3 (Neptune Loader)

For initial data ingest, use the Neptune Loader (NOT a script that
issues individual Gremlin `g.addV` calls — that is 10-100x slower).

**Prerequisites:**
- S3 bucket in the SAME region as the Neptune cluster.
- IAM role with trust policy allowing Neptune and permissions
  `s3:GetObject` on the bucket.
- Data in a supported format: Gremlin CSV/JSON/n-quad, or SPARQL
  N-Triples/RDF.

**Load:**

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  https://<cluster-endpoint>:8182/loader \
  -d '{
    "source": "s3://prod-graph-bucket/initial-load/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::<account>:role/NeptuneLoadRole",
    "mode": "NEW",
    "region": "us-east-1",
    "failOnError": "TRUE",
    "parallelism": "MEDIUM"
  }'
```

**Common mistakes:**
- Cross-region S3 bucket — the Loader fails silently or with a
  generic permissions error. Always same-region.
- Concurrent loads on the same cluster conflict. Run one load at a
  time per cluster.
- `mode=AUTO` overwrites existing vertices; `mode=NEW` errors on
  duplicates; `mode=RESUME` continues an interrupted load.

## Step 9 — Query languages (Gremlin, SPARQL, openCypher)

Neptune supports three query languages on the SAME cluster (no need
to pick at creation). Endpoints:

| Language | Endpoint path | Use when |
|---|---|---|
| Gremlin | `:8182/gremlin` | Apache TinkerPop-compatible; property graph; deep traversals |
| SPARQL | `:8182/sparql` | RDF / semantic web; triple-store; SPARQL queries |
| openCypher | `:8182/opencypher` | Cypher (Neo4j-compatible) syntax; property graph; declarative patterns |

**Common mistake:** loading property-graph data then trying SPARQL.
Gremlin and openCypher operate on the property graph; SPARQL operates
on RDF triples. They are different data models. Pick the model at load
time.

## Step 10 — Streams / snapshots / recent features

**Neptune Streams (CDC):**
- Enable via `neptune_streams=1` in the parameter group + reboot.
- Exposes an HTTP endpoint (`:8182/streams`) returning change records
  (vertex/edge insertions, updates, deletions).
- Pair with a consumer (Kinesis Data Streams + Lambda, or a custom
  poller) for downstream replication / audit.
- Stream records are retained for ~24 hours.

**Snapshots (automated + manual):**
- Automated: set `--backup-retention-period 7` (days) at creation.
- Manual: `aws neptune create-db-cluster-snapshot` before upgrades.
- Restore creates a NEW cluster (the snapshot is cluster-scoped).

**Recent AWS features (2023-2026):**
- **Neptune Analytics (2023-2024):** Separate OLAP graph service with
  built-in algorithms (PageRank, BFS). NOT this skill — separate
  `aws graph` API. Pair with Neptune DB for batch analytic pipelines.
- **openCypher improvements (2023-2024):** Server-side planning and
  caching improve repeat-query latency ~30%. Use the latest engine
  version.
- **Engine version 1.3.x.x (rolling):** Gremlin 3.7+ support, better
  SPARQL federation. Pin the major version explicitly in production;
  do not use "latest".
- **Graviton (r6g) instance classes (2022-2024):** ~15% better
  price/performance over r5. Default to Graviton for new clusters.
- **IAM database auth enhancements (2023-2024):** Fine-grained
  `neptune-db:*` actions for query/type-level RBAC.

## NEVER do these things

1. **NEVER plan to "enable encryption at rest later."** Neptune
   encryption is immutable post-creation. Adding it requires a
   snapshot → restore into a new encrypted cluster. Decide at creation.

2. **NEVER provision Neptune DB for a graph-algorithm (PageRank,
   connected components) workload.** Neptune DB has no built-in
   algorithm library. Use Neptune Analytics (separate service). A
   baseline model conflates the two.

3. **NEVER enable `neptune_enforce_ssl=1` on an existing production
   cluster without a maintenance window.** The rolling reboot drops
   plaintext clients. Enable at creation.

4. **NEVER open port 8182 to `0.0.0.0/0`.** Even with TLS and IAM
   auth, internet exposure invites scanning. Always scope inbound to
   the application's SG.

5. **NEVER use a single-AZ subnet group for Multi-AZ Neptune.**
   Multi-AZ requires the promoted reader in a different AZ than the
   writer. Verify `aws ec2 describe-subnets` shows >=2 distinct AZs in
   the subnet group before `create-db-cluster`.

6. **NEVER run a Neptune DB cluster with only a writer instance in
   production.** There is no failover target. The minimum production
   topology is 1 writer + 1 reader in a different AZ.

7. **NEVER load data via individual Gremlin `g.addV()` calls for bulk
   ingest.** Use the Neptune Loader (10-100x faster). Per-vertex
   inserts are for incremental app writes only.

8. **NEVER use a cross-region S3 bucket for the Neptune Loader.** It
   fails silently or with a generic permissions error. Always
   same-region.

9. **NEVER load property-graph data then expect SPARQL to work.**
   Gremlin/openCypher operate on the property graph; SPARQL operates
   on RDF triples. Different data models. Pick at load time.

10. **NEVER size Neptune by spec-sheet memory.** Plan for 60% buffer
    cache budget; the graph working set (vertices + edges + 3x
    indexes) MUST fit in 60% of nominal or traversals slow 10-100x.

11. **NEVER disable deletion protection on a production cluster
    outside of a planned teardown.** Accidental `delete-db-cluster`
    destroys the cluster + storage irrecoverably.

12. **NEVER use the engine version "latest" in production.** Pin the
    major version explicitly; auto-upgrades during maintenance windows
    can introduce breaking behavior.

## Output format

```text
NEPTUNE: <cluster-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Service: Neptune DB (NOT Analytics)
  [✓|✗] Engine version: 1.3.x.x (pinned)
  [✓|✗] Writer instance: db.<family>.<size>
  [✓|✗] Reader instances: <N> (across <AZ-count> AZs for Multi-AZ)
  [✓|✗] Multi-AZ with reader promotion: Enabled | Disabled (writer-only — NO failover)
  [✓|✗] Subnet group: <name> (spans <N> AZs)
  [✓|✗] Security group: <sg-id> (inbound port 8182 from <app-sg>)
  [✓|✗] Encryption at rest: Enabled (customer CMK <key-arn> | AWS-managed) | Disabled
  [✓|✗] TLS / neptune_enforce_ssl: Enabled | Disabled
  [✓|✗] IAM database auth: Enabled | Disabled
  [✓|✗] Parameter group: <name> (neptune_query_timeout=<ms>, neptune_streams=<0|1>)
  [✓|✗] Snapshot retention: <N> days | Disabled
  [✓|✗] Deletion protection: Enabled | Disabled
  [✓|✗] Bulk load source: s3://<bucket>/<prefix> (same region, IAM role <role-arn>) | N/A
  [✓|✗] Query languages: Gremlin | SPARQL | openCypher
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier <name>
  aws neptune describe-db-instances --db-instance-identifier <name>-instance-1
  aws neptune describe-db-cluster-parameters --db-cluster-parameter-group-name <pg>
  aws ec2 describe-subnets --subnet-ids <subnet-ids>
  aws kms describe-key --key-id <cmk-id>
```

### Worked example — production Neptune DB with Multi-AZ

```text
NEPTUNE: prod-graph
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service: Neptune DB (NOT Analytics)
  [✓] Engine version: 1.3.2.0 (pinned)
  [✓] Writer instance: db.r6g.8xlarge
  [✓] Reader instances: 2 (across us-east-1b, us-east-1c for Multi-AZ)
  [✓] Multi-AZ with reader promotion: Enabled
  [✓] Subnet group: prod-neptune-subnet (3 AZs)
  [✓] Security group: sg-neptune123 (inbound 8182 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-graph-kms)
  [✓] TLS / neptune_enforce_ssl: Enabled
  [✓] IAM database auth: Enabled
  [✓] Parameter group: prod-neptune-pg (neptune_query_timeout=30000, neptune_streams=1)
  [✓] Snapshot retention: 7 days
  [✓] Deletion protection: Enabled
  [✓] Bulk load source: s3://prod-graph-bucket/initial-load/ (same region, IAM role NeptuneLoadRole)
  [✓] Query languages: Gremlin, openCypher
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier prod-graph
  aws neptune describe-db-instances --db-instance-identifier prod-graph-instance-1
  aws neptune describe-db-cluster-parameters --db-cluster-parameter-group-name prod-neptune-pg
  aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc
  aws kms describe-key --key-id alias/prod-graph-kms
```

## Decision tree: Neptune DB vs Neptune Analytics

```text
Is the workload transactional (OLTP) — point lookups, short
traversals, real-time app queries, frequent writes?
├── YES → Neptune DB  (this skill)
│         writer + readers, Multi-AZ, Gremlin/SPARQL/openCypher
└── NO  → Is the workload analytical (OLAP) — PageRank,
          connected-components, community-detection on a large
          static graph?
    ├── YES → Neptune Analytics  (NOT this skill — aws graph)
    │         single graph, built-in algorithms, GB-hour pricing
    └── NO  → Neptune DB for transactions + scheduled export to
              Neptune Analytics for batch algorithm runs
```

## Error handling

### Cluster name already exists (`DBClusterAlreadyExists`)

- If config matches intent: skip to verification, emit READY_TO_DEPLOY.
- If config differs: mutable settings (instance class, parameter group,
  snapshot retention, security groups) change via `modify-db-cluster`.
  Engine version, storage encryption, and VPC/subnet placement CANNOT
  be changed — those require a new cluster + snapshot/restore.

### Multi-AZ create fails (`DBSubnetGroup does not span multiple AZs`)

**Fix:** add subnets in different AZs via `modify-db-subnet-group`,
then verify distinct `AvailabilityZone` values via
`aws ec2 describe-subnets`.

### IAM auth fails (`AccessDeniedException` from `neptune-db:Connect`)

**Fix:** add `neptune-db:Connect` on
`arn:aws:neptune:<region>:<account>:cluster/<name>` to the IAM
principal's policy; verify the client driver refreshes SigV4 tokens
(~15 min lifetime).

### Loader fails (`Loader could not assume role`)

**Fix:** verify the role trust policy includes `rds.amazonaws.com` and
that the bucket is in the same region as the cluster.

## Domain

AWS CloudOps / Amazon Neptune DB Provisioning & Graph Topology Design.

## AWS documentation

- **Amazon Neptune User Guide** — https://docs.aws.amazon.com/neptune/latest/userguide/intro.html
- **Neptune instance classes** — https://docs.aws.amazon.com/neptune/latest/userguide/instance-types.html
- **Neptune encryption at rest** — https://docs.aws.amazon.com/neptune/latest/userguide/encrypt.html
- **Neptune TLS / neptune_enforce_ssl** — https://docs.aws.amazon.com/neptune/latest/userguide/security-ssl.html
- **Neptune IAM database auth** — https://docs.aws.amazon.com/neptune/latest/userguide/iam-auth.html
- **Neptune Loader** — https://docs.aws.amazon.com/neptune/latest/userguide/load-data.html
- **Neptune Streams** — https://docs.aws.amazon.com/neptune/latest/userguide/streams.html
- **Neptune Analytics (separate service)** — https://docs.aws.amazon.com/neptune-analytics/latest/dg/what-is-neptune-analytics.html
- **Gremlin / SPARQL / openCypher in Neptune** — https://docs.aws.amazon.com/neptune/latest/userguide/graph-engines.html
