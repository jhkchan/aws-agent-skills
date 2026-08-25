---
name: neptune-graph-deployer
description: 'Provisions Amazon Neptune graph database clusters with production defaults: cluster creation (primary + read replicas), instance types, Neptune ML integration, IAM database authentication, encryption at rest (KMS), parameter groups (neptune_enforce_ssl, neptune_query_timeout), subnet groups, security groups, Neptune Streams (change log), Global Database (cross-region), Gremlin vs SPARQL query language support, auto-scaling read replicas, bulk loader, CloudWatch metrics (VolumeBytesUsed, EngineCPUUtilization, GremlinRequestsPerSec), and snapshot management. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Neptune cluster, setting up graph database replicas, enabling Neptune ML, configuring IAM database authentication, or establishing a Neptune Global Database. Triggers: create neptune cluster, neptune graph database, gremlin sparql cluster, neptune ml, neptune global database, neptune streams, neptune iam auth, neptune bulk loader, neptune read replica autoscaling.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with neptune and rds access (Neptune uses RDS-style cluster APIs). Works with Terraform aws_neptune_cluster / aws_neptune_cluster_instance / aws_neptune_cluster_parameter_group resources and CloudFormation AWS::Neptune::DBCluster / AWS::Neptune::DBInstance templates.'
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
  tags: aws, neptune, graph-database, gremlin, sparql, cloudops, deploy, databases, provisioning, read-replica, encryption, neptune-ml, global-database
  dependencies: aws-orchestrator
  keywords: aws, neptune, graph database, gremlin, sparql, cloudops, deploy, provisioning, read replica, cluster, neptune ml, iam auth, encryption, kms, neptune streams, global database, bulk loader, auto scaling
  when_to_use: Invoke when the user wants to create an Amazon Neptune graph database cluster, configure primary and read replicas, enable Neptune ML integration, configure IAM database authentication, enable encryption at rest with KMS, set parameter groups (neptune_enforce_ssl, neptune_query_timeout), configure Neptune Streams for change logging, create a Neptune Global Database for cross-region disaster recovery, choose between Gremlin and SPARQL query languages, set up auto-scaling read replicas, or run the Neptune bulk loader. Do NOT invoke for Amazon Neptune Analytics (serverless graph analytics), Amazon RDS/Aurora (relational databases), or Amazon OpenSearch (search/document databases).
---

# Neptune Graph Deployer

An AWS CloudOps agent skill that provisions Amazon Neptune graph
database clusters with correct defaults. The skill walks the operator
through cluster creation (primary + read replicas), instance type
selection, Gremlin vs SPARQL query language support, Neptune ML
integration, IAM database authentication, encryption at rest (KMS),
parameter groups (neptune_enforce_ssl, neptune_query_timeout), subnet
groups, security groups, Neptune Streams (change log), Global Database
(cross-region), auto-scaling read replicas, bulk loader, and CloudWatch
metrics — then emits a READY_TO_DEPLOY checklist with verification
commands.

## Activation keywords

create Neptune cluster, Neptune graph database, Gremlin SPARQL cluster,
Neptune ML, Neptune Global Database, Neptune Streams, Neptune IAM auth,
Neptune bulk loader, Neptune read replica auto-scaling.

## STRICT output contract

When this skill is invoked with a Neptune-provisioning request (create
a cluster, configure read replicas, enable Neptune ML, set up IAM auth,
enable encryption, configure Streams, create a Global Database, or a
partial configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined below. This contract is what assertion-based evals
and downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

### Required output structure

The model MUST emit output using these literal labels, in this order,
as the FIRST lines of the response (no prose, headings, or disclaimers
before them):

- `NEPTUNE: <cluster-id> (<instance-type>, <engine-version>)` — first line
- `VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING` — second line
- `CHECKLIST:` followed by `- [✓]` or `- [✗]` items (one row per dimension below)
- `VERIFICATION_COMMANDS:` followed by a fenced block of copy-pasteable CLI

The CHECKLIST MUST cover every dimension, in this order: query language
(Gremlin/SPARQL/OpenCypher), topology (primary + N read replicas across
M AZs), instance type + memory + IOPS, subnet group, security group
(port 8182), parameter group (neptune_enforce_ssl, neptune_query_timeout,
neptune_streams), IAM database authentication, at-rest encryption (KMS
key ARN), Neptune Streams (filter pattern), Neptune ML, Global Database,
auto-scaling, backup retention/window, snapshot window (vs maintenance),
bulk loader readiness, and tags.

### Decision tree (determines VERDICT)

```text
Is a subnet group defined with >= 2 AZs in the target VPC?
├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Subnet group)
└── YES → Is the security group allowing TCP 8182 from the app SG?
          ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Security group port 8182)
          └── YES → Is a neptune1.x cluster parameter group created?
                    ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Parameter group)
                    └── YES → Is the at-rest encryption decision made BEFORE create?
                              ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Encryption is creation-time-only)
                              └── YES → Is the IAM auth decision recorded (also creation-time-only)?
                                        ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] IAM auth)
                                        └── YES → Is neptune_streams explicitly set in the parameter group?
                                                  ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] neptune_streams not set)
                                                  └── YES → All prerequisites satisfied
                                                            → VERDICT: READY_TO_DEPLOY
```

### FORBIDDEN patterns (NEVER)

1. **NEVER preface the CHECKLIST** with prose, headings, or disclaimers — emit the block as the first lines of the response.
2. **NEVER omit the VERIFICATION_COMMANDS section**, even when every checklist item passes.
3. **NEVER use generic placeholders** (`<your-value>`, `<cluster-id>`, `<region>`) in a worked example — always use concrete cluster IDs, real ARNs, and specific CLI commands.
4. **NEVER mix verdict shapes** — if any prerequisite is `[✗]`, VERDICT MUST be `PREREQUISITES_MISSING` and `READY_TO_DEPLOY` MUST NOT also appear.
5. **NEVER skip a CHECKLIST row** for a dimension that was evaluated — every dimension gets a `[✓]` or `[✗]` line.
6. **NEVER suggest toggling encryption, IAM auth, or `neptune_enforce_ssl`** on an existing cluster — they are creation-time-only or require a reboot.
7. **NEVER use `aws rds` commands** in VERIFICATION_COMMANDS — Neptune uses the `aws neptune` namespace.
8. **NEVER omit the engine version** from the `NEPTUNE:` header line — Global Database and Streams support depend on it.

### Perfect example — 3-instance cluster with Gremlin, KMS encryption, and Streams

This is the EXACT shape the model emits for a positive scenario.
Copy the literal labels, the bracket glyphs, and the fenced command
block. Replace the concrete values with the scenario's values; do not
genericise them into placeholders.

```text
NEPTUNE: fraud-graph-prod (db.r5.4xlarge, 1.3.2.1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Query language: Gremlin (primary), SPARQL (available)
  [✓] Topology: Primary + 2 read replicas (across 3 AZs: us-east-1a, us-east-1b, us-east-1c)
  [✓] Instance type: db.r5.4xlarge (128 GB RAM, 8000 baseline IOPS)
  [✓] Subnet group: neptune-prod-subnet-group (3 AZs)
  [✓] Security group: sg-0a1b2c3d4e5f6g7h8 (port 8182 inbound from sg-app-111222333)
  [✓] Parameter group: neptune-prod-params (neptune_enforce_ssl=1, neptune_query_timeout=120000, neptune_streams=1)
  [✓] IAM database authentication: Enabled (set at cluster creation)
  [✓] At-rest encryption (KMS): Enabled (key arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-1111-2222-3333-444455556666)
  [✓] Neptune Streams: Enabled (filter: {"op": ["ADD","UPDATE","REMOVE"]})
  [✓] Neptune ML: Not configured
  [✓] Global Database: Not configured
  [✓] Auto-scaling: Target tracking (EngineCPUUtilization 60%, min 1, max 5 replicas)
  [✓] Backup: Automated (retention 7 days, window 03:00-04:00 UTC)
  [✓] Snapshot window: 03:00-04:00 UTC (no overlap with maintenance mon:05:00-mon:06:00)
  [✓] Bulk loader: Ready (S3 s3://neptune-prod-bulk/graph/, IAM role arn:aws:iam::123456789012:role/NeptuneBulkLoadRole)
  [✓] Tags: Environment=production, Application=fraud-detection, Owner=data-eng
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier fraud-graph-prod --region us-east-1
  aws neptune describe-db-instances --db-instance-identifier fraud-graph-prod-primary --region us-east-1
  aws neptune describe-db-cluster-parameters --db-cluster-parameter-group-name neptune-prod-params --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/Neptune --metric-name EngineCPUUtilization --dimensions Name=DBInstanceIdentifier,Value=fraud-graph-prod-primary --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z --period 300 --statistics Average --region us-east-1
```

If any prerequisite fails, emit the SAME shape with
`VERDICT: PREREQUISITES_MISSING`, the failing row marked `[✗]` with a
specific gap citation (e.g. `[✗] Subnet group: only 1 AZ — need >= 2`),
the passing rows still listed, and VERIFICATION_COMMANDS showing the
command that would confirm the gap.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Gremlin vs SPARQL query language | Query language choice |
| Step 2 — Cluster creation (primary + read replicas) | Core topology |
| Step 3 — Instance types and storage | Capacity planning |
| Step 4 — Subnet groups and security groups | Network + security |
| Step 5 — Parameter groups (neptune_enforce_ssl, neptune_query_timeout) | Engine config |
| Step 6 — IAM database authentication | Access control |
| Step 7 — Encryption at rest (KMS) | Security |
| Step 8 — Neptune Streams (change log) | Change capture |
| Step 9 — Neptune ML integration | ML workloads |
| Step 10 — Global Database (cross-region) | DR / cross-region |
| Step 11 — Auto-scaling read replicas | Capacity elasticity |
| Step 12 — Bulk loader | Data ingestion |
| Step 13 — CloudWatch metrics and monitoring | Observability |
| Step 14 — Snapshot management | Data durability |
| Step 15 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/query-languages-and-streams.md | Gremlin/SPARQL + Streams detail |
| references/scaling-and-monitoring.md | Replica scaling + CloudWatch detail |

## Mindset

**One-line takeaway:** Amazon Neptune is a purpose-built graph database
that supports both Gremlin (property graph / RDF) and SPARQL (RDF)
query languages on the SAME cluster. A Neptune cluster has one primary
instance and 0-15 read replicas. Encryption at rest is a creation-time
setting. Neptune Streams captures every graph change for downstream
processing. Read replica auto-scaling handles graph traversal concurrency
spikes by adding replicas based on CPU utilization.

> The three provisioning misconceptions (storage/IOPS, replica write scaling, Gremlin-vs-SPARQL clusters) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand; the one-line takeaway above is the operative summary.

## Configuration dependency graph (novel heuristic)

> Full dependency graph table and cross-dependency gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand to sequence provisioning; encryption/IAM/Streams are creation-time decisions.

## Expert heuristic: instance storage vs IOPS provisioning + read replica scaling for graph traversal concurrency + Stream filter patterns

> Sizing heuristic (storage vs IOPS, replica scaling formula, Stream filter patterns) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
> Step 3 keeps the instance table and sizing rules.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC and subnets (>= 2 AZs) | Cluster needs multi-AZ subnet group | `aws ec2 describe-subnets` |
| Subnet group exists or creatable | Cluster requires a DB subnet group | `aws rds describe-db-subnet-groups` |
| Security group (port 8182) | Neptune default port for client connections | `aws ec2 describe-security-groups` |
| Instance type selected | Memory (graph fit) + IOPS (traversals) | `aws neptune describe-orderable-db-instance-options` |
| Engine version selected | Feature support (ML, Streams, Global DB) | `aws neptune describe-db-engine-versions` |
| Query language decision (Gremlin/SPARQL/both) | Application client library depends on it | Assess use case |
| Parameter group decision | neptune_enforce_ssl, neptune_query_timeout, neptune_streams | Assess security + performance |
| Encryption decision | MUST be at creation — cannot toggle later | Assess compliance |
| IAM auth decision | MUST be at cluster creation | Assess access control |
| Neptune ML decision (if needed) | S3 bucket + SageMaker IAM role required | Assess ML requirements |
| KMS key (if encryption with CMK) | Custom KMS key must exist | `aws kms describe-key` |
| Neptune Streams decision | Must be enabled in parameter group | Assess change capture needs |
| Snapshot window vs maintenance window | Must not overlap | Plan windows |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Gremlin vs SPARQL query language

| Feature | Gremlin | SPARQL |
|---|---|---|
| Graph model | Property graph | RDF (Resource Description Framework) |
| Query style | Traversal-based (imperative) | Pattern-matching (declarative) |
| Best for | Multi-hop traversals, path queries | Linked data, semantic queries, federation |
| Client library | Gremlin console, TinkerPop drivers | Jena, RDF4J, SPARQL endpoints |
| Same cluster? | Yes — both supported on one Neptune cluster | Yes |
| Performance | Optimized for traversals | Optimized for pattern matching |

**Choose Gremlin** for social network analysis, recommendation engines,
and fraud detection (multi-hop traversals). **Choose SPARQL** for
semantic web, linked data integration, and complex pattern matching
across heterogeneous data.

A Neptune cluster supports both. The application connects with the
appropriate client library. No separate cluster is needed.

## Step 2 — Cluster creation (primary + read replicas)

A Neptune cluster has one primary instance (serves reads + writes) and
0-15 read replicas (serve reads only). All writes go to the primary.

> Cluster/primary/replica creation CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Topology rule: one primary (reads+writes) + 0-15 read replicas (reads only), replicas in different AZs.

**Common mistake:** using `aws rds` commands instead of `aws neptune`.
Neptune uses its own API namespace (`aws neptune`) even though the
parameters mirror RDS.

## Step 3 — Instance types and storage

| Instance type | Memory | vCPUs | Use case |
|---|---|---|---|
| db.r5.large | 16 GB | 2 | Small dev/test graphs |
| db.r5.4xlarge | 128 GB | 16 | Medium production graphs |
| db.r5.8xlarge | 256 GB | 32 | Large production graphs |
| db.r5.12xlarge | 384 GB | 48 | High-memory traversals |
| db.x2g.8xlarge | 1 TB | 32 | Very large graph working sets |

**Sizing rules:**
- Memory must fit the graph working set (vertices + edges + indexes).
- IOPS scale with instance type and EBS volume configuration.
- Provisioned IOPS (io2) recommended for traversal-heavy workloads.
- Read replicas scale read concurrency, NOT write throughput.

> Instance-option enumeration CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Sizing rules above remain authoritative.

## Step 4 — Subnet groups and security groups

> Subnet-group and security-group CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Port 8182 inbound from the app SG is mandatory — see Critical note below.

**Critical:** Neptune uses port 8182 for all client connections (both
Gremlin and SPARQL). The security group must allow inbound from the
application SG on port 8182.

## Step 5 — Parameter groups (neptune_enforce_ssl, neptune_query_timeout)

Parameter groups control engine-level configuration including SSL
enforcement, query timeouts, and Streams.

> Parameter-group create/modify CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Parameter table and the static-parameter reboot warning below remain in-file.

| Parameter | Default | Effect |
|---|---|---|
| neptune_enforce_ssl | 0 | 1 = require TLS for all connections (static — needs reboot) |
| neptune_query_timeout | 120000 (ms) | Max query duration before timeout |
| neptune_streams | 0 | 1 = enable Neptune Streams change log (static — needs reboot) |

**Critical:** `neptune_enforce_ssl` and `neptune_streams` are static
parameters — they require an instance reboot to take effect. Set them
before the first write to avoid disruption.

## Step 6 — IAM database authentication

Neptune supports IAM database authentication using AWS SigV4. This
eliminates the need for database passwords.

> IAM-auth creation snippet and the neptune-db:connect policy JSON moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> IAM auth MUST be enabled at creation — see Critical note below.

**Critical:** IAM database authentication MUST be enabled at cluster
creation. It cannot be toggled on afterward. The application uses SigV4
signing instead of a static password.

## Step 7 — Encryption at rest (KMS)

**Encryption is creation-time-only for Neptune clusters.** It CANNOT be
toggled on after the cluster exists.

> Encrypted-cluster creation CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Encryption is creation-time-only; existing clusters need a new cluster + reload.

To encrypt an existing non-encrypted cluster, create a new encrypted
cluster and load data via the bulk loader or Neptune Export/Import.

## Step 8 — Neptune Streams (change log)

Neptune Streams captures every graph mutation (ADD, UPDATE, REMOVE) in
a change log. Enable it in the parameter group.

> Streams enable/reboot CLI, stream-consumer curl, and filter-pattern JSON moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Streams capture only post-enablement changes — see Critical note below.

**Critical:** Streams only capture changes AFTER enablement. Past
mutations are NOT retroactively available. Filter aggressively to reduce
consumer processing load.

## Step 9 — Neptune ML integration

Neptune ML uses SageMaker to train and deploy graph machine learning
models (node classification, link prediction, edge regression).

**Prerequisites:**
- S3 bucket for model artifacts and training data export.
- IAM role with SageMaker + Neptune + S3 permissions.
- The Neptune ML workflow: export data, train model, create inference
  endpoint.

> Neptune ML export/training CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Prerequisites and the inference-latency implication remain in-file.

**Key implication:** Neptune ML inference endpoints add latency to
queries. Use them for batch inference, not real-time low-latency paths.

## Step 10 — Global Database (cross-region)

Neptune Global Database provides cross-region read replicas for disaster
recovery and low-latency multi-region reads.

> Global Database create/secondary/replica CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Constraints (matching engine versions, read-only secondary) below.

**Constraints:** same engine version across regions; secondary cluster
is read-only until failover; replication lag depends on cross-region
network distance.

## Step 11 — Auto-scaling read replicas

Neptune supports Application Auto Scaling for read replicas based on
CloudWatch metrics.

> Auto-scaling register-target and target-tracking policy CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Replicas take minutes to become available — see Key implication below.

**Key implication:** read replica auto-scaling adds replicas (0-15 max)
based on CPU utilization or replica lag. Replicas take minutes to become
available — spikes can still cause timeouts during scale-out.

## Step 12 — Bulk loader

The Neptune bulk loader is for initial or batch data ingestion from S3.

> Bulk-loader curl payload and mode/parallelism best practice moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Loader is for batch ingestion, not streaming — see Critical note below.

**Critical:** the bulk loader is for batch ingestion, not continuous
streaming. For streaming writes, use the application SDK or Neptune
Streams consumer pattern.

## Step 13 — CloudWatch metrics and monitoring

| Metric | Namespace | What it measures |
|---|---|---|
| VolumeBytesUsed | AWS/Neptune | Storage consumed by the graph |
| EngineCPUUtilization | AWS/Neptune | CPU usage on the instance |
| GremlinRequestsPerSec | AWS/Neptune | Gremlin query rate |
| GremlinWebSocketOpenConnections | AWS/Neptune | Active Gremlin WebSocket connections |
| SparqlRequestsPerSec | AWS/Neptune | SPARQL query rate |
| TotalRequestsPerSec | AWS/Neptune | Total query rate (Gremlin + SPARQL) |
| DbCPUUtilization | AWS/Neptune | Database process CPU |
| DbFreeableMemory | AWS/Neptune | Available memory |
| BufferCacheHitRatio | AWS/Neptune | Cache effectiveness for traversals |

> CloudWatch monitoring CLI (CPU, storage growth) and alert thresholds moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
> Metric table above stays authoritative.

## Step 14 — Snapshot management

| Snapshot type | How | Retention |
|---|---|---|
| Automated | Within backup window | 1-35 days (backup-retention-period) |
| Manual | On-demand via API | Until manually deleted |

> Snapshot create/restore CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
> Snapshot type/retention table above.

## Step 15 — Recent features

> Recent features (2023-2025) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand — Neptune Analytics, OpenCypher, loader/Streams/Global DB improvements, r7g.

## NEVER do these things

1. **NEVER assume encryption can be enabled after cluster creation.**
   Storage encryption is creation-time-only for Neptune clusters.
   Existing non-encrypted clusters require migration to a new encrypted
   cluster.

2. **NEVER use `aws rds` commands for Neptune.** Neptune uses its own
   API namespace (`aws neptune`). The parameters mirror RDS, but the
   API endpoints are different.

3. **NEVER assume read replicas scale write throughput.** All writes go
   to the primary instance. Read replicas only serve read queries. If
   writes are the bottleneck, use a larger primary instance type.

4. **NEVER change `neptune_enforce_ssl` without a reboot plan.**
   `neptune_enforce_ssl` is a static parameter — it requires an instance
   reboot to take effect. Plan for the brief downtime.

5. **NEVER enable Neptune Streams and expect past changes to be
   captured.** Streams only capture changes AFTER enablement. Past
   mutations are NOT retroactively available.

6. **NEVER create a Global Database with mismatched engine versions.**
   Primary and secondary must use the same engine version. Mismatches
   cause replication failures.

7. **NEVER use the bulk loader for streaming writes.** The bulk loader
   is for initial or batch data ingestion from S3. For streaming, use
   the application SDK or Neptune Streams consumer pattern.

8. **NEVER forget the security group port.** Neptune uses port 8182
   for all client connections (Gremlin, SPARQL, and OpenCypher). Wrong
   port is a silent failure.

9. **NEVER enable IAM database authentication on an existing cluster.**
   IAM auth must be enabled at cluster creation. It cannot be toggled
   afterward.

10. **NEVER scale read replicas without monitoring replica lag.**
    Auto-scaling adds replicas based on CPU utilization, but new replicas
    take minutes to become available. Monitor `NeptuneReadReplicaLag`
    during scale-out.

## Output format

```text
NEPTUNE: <cluster-id> (<instance-type>, <engine-version>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Query language: Gremlin | SPARQL | OpenCypher | Multiple
  [✓|✗] Topology: Primary + <N> read replicas (across <M> AZs)
  [✓|✗] Instance type: <instance-type> (<memory> GB, <IOPS> baseline)
  [✓|✗] Subnet group: <subnet-group-name> (<N> AZs)
  [✓|✗] Security group: <sg-id> (port 8182)
  [✓|✗] Parameter group: <param-group-name> (neptune_enforce_ssl=<0|1>, neptune_query_timeout=<ms>)
  [✓|✗] IAM database authentication: Enabled | Disabled
  [✓|✗] At-rest encryption (KMS): Enabled (key <kms-key-id>) | Disabled
  [✓|✗] Neptune Streams: Enabled (filter <pattern>) | Disabled
  [✓|✗] Neptune ML: Enabled (S3 bucket <bucket>, SageMaker role <role>) | Not configured
  [✓|✗] Global Database: <global-id> (primary <region>, secondary <region>) | Not configured
  [✓|✗] Auto-scaling: Target tracking (<metric>, target <value>) | Not configured
  [✓|✗] Backup: Automated (retention <N> days, window <window>) | Manual only
  [✓|✗] Snapshot window: <window> (no overlap with maintenance <window>)
  [✓|✗] Bulk loader: Ready (S3 <bucket>, IAM role <role>) | Not needed
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier <cluster-id> --region <region>
  aws neptune describe-db-instances --db-instance-identifier <primary-id> --region <region>
  aws cloudwatch get-metric-statistics --namespace AWS/Neptune --metric-name EngineCPUUtilization --dimensions Name=DBInstanceIdentifier,Value=<primary-id> --region <region>
```

### Worked example — Neptune cluster with Gremlin, encryption, IAM auth, Streams, and read replicas

> Secondary worked example (full READY_TO_DEPLOY block) moved to [references/worked-examples.md](references/worked-examples.md).
> The Perfect example under the STRICT output contract above is the primary in-file example.

## Error handling

> Error-handling deep dives (encryption unsupported, connectivity, replica lag, empty Streams, Global DB replication, loader errors) moved to [references/error-handling.md](references/error-handling.md).
> Load on demand when provisioning or verification fails.

## Domain

AWS CloudOps / Amazon Neptune Graph Database Cluster Provisioning &
Graph Data Management.

## AWS documentation

- **Neptune User Guide** — https://docs.aws.amazon.com/neptune/latest/userguide/intro.html
- **Creating a Neptune cluster** — https://docs.aws.amazon.com/neptune/latest/userguide/manage-console-launch.html
- **Gremlin and SPARQL** — https://docs.aws.amazon.com/neptune/latest/userguide/access-graph-gremlin.html
- **Neptune ML** — https://docs.aws.amazon.com/neptune/latest/userguide/machine-learning.html
- **IAM database authentication** — https://docs.aws.amazon.com/neptune/latest/userguide/iam-auth.html
- **Encryption at rest** — https://docs.aws.amazon.com/neptune/latest/userguide/encrypt.html
- **Neptune Streams** — https://docs.aws.amazon.com/neptune/latest/userguide/streams.html
- **Global Database** — https://docs.aws.amazon.com/neptune/latest/userguide/neptune-global-database.html
- **Parameter groups** — https://docs.aws.amazon.com/neptune/latest/userguide/parameters.html
- **Bulk loader** — https://docs.aws.amazon.com/neptune/latest/userguide/load-data.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/neptune/latest/userguide/cw-metrics.html
## References (load on demand)
- [references/error-handling.md](references/error-handling.md) — provisioning/connectivity/stream/loader error deep dives.
- [references/advanced-patterns.md](references/advanced-patterns.md) — misconceptions, dependency graph, sizing heuristic, recent features.
- [references/worked-examples.md](references/worked-examples.md) — secondary full worked example.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — CloudWatch monitoring CLI and alert thresholds.
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — all provisioning CLI blocks (Steps 2-12, 14).

