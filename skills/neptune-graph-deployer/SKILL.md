---
name: neptune-graph-deployer
description: >-
  Provisions Amazon Neptune graph database clusters with production
  defaults: cluster creation (primary + read replicas), instance types,
  Neptune ML integration, IAM database authentication, encryption at
  rest (KMS), parameter groups (neptune_enforce_ssl,
  neptune_query_timeout), subnet groups, security groups, Neptune
  Streams (change log), Global Database (cross-region), Gremlin vs
  SPARQL query language support, auto-scaling read replicas, bulk
  loader, CloudWatch metrics (VolumeBytesUsed, EngineCPUUtilization,
  GremlinRequestsPerSec), and snapshot management. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating a Neptune cluster, setting up graph database replicas,
  enabling Neptune ML, configuring IAM database authentication, or
  establishing a Neptune Global Database. Triggers: create neptune
  cluster, neptune graph database, gremlin sparql cluster, neptune ml,
  neptune global database, neptune streams, neptune iam auth, neptune
  bulk loader, neptune read replica autoscaling.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with neptune and
  rds access (Neptune uses RDS-style cluster APIs). Works with
  Terraform aws_neptune_cluster / aws_neptune_cluster_instance /
  aws_neptune_cluster_parameter_group resources and CloudFormation
  AWS::Neptune::DBCluster / AWS::Neptune::DBInstance templates.
keywords:
  - aws
  - neptune
  - graph database
  - gremlin
  - sparql
  - cloudops
  - deploy
  - provisioning
  - read replica
  - cluster
  - neptune ml
  - iam auth
  - encryption
  - kms
  - neptune streams
  - global database
  - bulk loader
  - auto scaling
tags:
  - aws
  - neptune
  - graph-database
  - gremlin
  - sparql
  - cloudops
  - deploy
  - databases
  - provisioning
  - read-replica
  - encryption
  - neptune-ml
  - global-database
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
    - neptune
    - graph-database
    - gremlin
    - sparql
    - cloudops
    - deploy
    - databases
    - provisioning
    - read-replica
    - encryption
    - neptune-ml
    - global-database
  dependencies:
    - aws-orchestrator
  keywords:
    - create neptune cluster
    - neptune graph database
    - gremlin sparql cluster
    - neptune ml
    - neptune global database
    - neptune streams
    - neptune iam auth
    - neptune bulk loader
    - neptune read replica autoscaling
  when_to_use: >-
    Invoke when the user wants to create an Amazon Neptune graph
    database cluster, configure primary and read replicas, enable
    Neptune ML integration, configure IAM database authentication,
    enable encryption at rest with KMS, set parameter groups
    (neptune_enforce_ssl, neptune_query_timeout), configure Neptune
    Streams for change logging, create a Neptune Global Database for
    cross-region disaster recovery, choose between Gremlin and SPARQL
    query languages, set up auto-scaling read replicas, or run the
    Neptune bulk loader. Do NOT invoke for Amazon Neptune Analytics
    (serverless graph analytics), Amazon RDS/Aurora (relational
    databases), or Amazon OpenSearch (search/document databases).
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

Three misconceptions dominate Neptune misdesign at provisioning time:

- **"Instance storage is just disk — IOPS don't matter for a graph
  database."** They DO. Neptune uses instance storage for the graph
  working set. Graph traversals (especially multi-hop Gremlin queries)
  are I/O-intensive. Undersized instance storage or insufficient
  provisioned IOPS cause query timeouts and high latency. Choose the
  instance type based on BOTH memory (graph working set fit) AND IOPS
  (traversal concurrency).

- **"Read replicas scale writes too."** They do NOT. Neptune read
  replicas serve only read queries (Gremlin traversals, SPARQL SELECT).
  ALL writes go to the primary instance. If write throughput is the
  bottleneck, a larger primary instance type is needed — not more
  replicas. Read replicas solve read concurrency, not write throughput.

- **"Gremlin and SPARQL require separate clusters."** They do NOT.
  Neptune supports BOTH query languages on the same cluster. Gremlin
  queries the property graph; SPARQL queries the RDF view of the same
  data (if the RDF feature is enabled). Choose the query language based
  on the use case, not the cluster.

## Configuration dependency graph (novel heuristic)

Neptune configurations are NOT independent. Encryption must be enabled
at creation. Parameter groups control SSL enforcement and query
timeouts. Neptune Streams must be explicitly enabled. Global Database
requires matching engine versions. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subnet group | >= 2 AZs (multi-AZ); same VPC | Cross-VPC subnets rejected | cluster creation |
| Security group | Port 8182 (Neptune default) | No ingress = client timeout | client connectivity |
| DB cluster parameter group | Created before cluster | neptune_enforce_ssl is static (requires instance reboot) | SSL enforcement |
| Cluster (primary) | Subnet group + parameter group + SG | Encryption at rest CANNOT be toggled after creation | graph storage |
| Read replicas | Cluster exists; replicas in different AZs | Replicas do NOT help write throughput | read scaling |
| IAM database authentication | Must be enabled at cluster creation | Cannot toggle without recreating | IAM-based access |
| Encryption at rest (KMS) | KMS key exists; set at creation | CANNOT enable on existing cluster | compliance |
| Neptune Streams | Streams parameter set to TRUE in parameter group | Stream records exist only after enablement | change capture |
| Neptune ML | S3 bucket for model artifacts; SageMaker IAM role | ML inference endpoint adds latency to queries | graph ML |
| Global Database | Primary cluster in region A; same engine version | Secondary is read-only until failover | cross-region DR |
| Auto-scaling read replicas | Cluster exists; scaling policy defined | Min/max must be within replica limits (0-15) | read elasticity |
| Bulk loader | Cluster exists; S3 bucket with source data; IAM role | Loader is for initial/batch loads, not streaming | data ingestion |

**The encryption-at-creation row is the one a baseline model misses.**
Like RDS and ElastiCache, Neptune encryption at rest is creation-time-
only. The procedure forces an explicit encryption decision before
cluster creation.

**Cross-dependency gotchas:**
- IAM database authentication must be enabled at cluster creation. It
  cannot be toggled on afterward.
- `neptune_enforce_ssl` is a static parameter — changing it requires an
  instance reboot to take effect.
- Neptune Streams must be explicitly enabled in the parameter group
  (`neptune_streams = 1`). Stream records only start flowing after
  enablement — past changes are NOT captured.
- Read replica auto-scaling adds replicas based on CPU utilization, but
  replicas take minutes to become available. Spikes can still cause
  timeouts during the scale-out period.
- Global Database requires matching engine versions. The secondary
  cluster is read-only until a planned failover.
- Bulk loader is for batch ingestion, not continuous streaming. For
  streaming, use Neptune Streams consumer pattern.

## Expert heuristic: instance storage vs IOPS provisioning + read replica scaling for graph traversal concurrency + Stream filter patterns

A baseline model says "create a Neptune cluster with a few replicas."
The correct heuristic matches instance storage type and IOPS to the
graph working set size and traversal concurrency, scales read replicas
based on Gremlin traversal patterns, and configures Neptune Streams
with appropriate filter patterns.

```text
Instance type selection (IOPS + storage):

  Graph working set:   50 GB    → r5.large (16 GB RAM, EBS-optimized)
  Graph working set:  200 GB    → r5.4xlarge (128 GB RAM, 8,000 baseline IOPS)
  Graph working set:  500 GB+   → r5.8xlarge (256 GB RAM, provisioned IOPS)
  Traversal-heavy:     any      → x2g instance (extended memory, SSD)

  Provisioned IOPS (io2 EBS): for high-concurrency multi-hop traversals
    IOPS budget = concurrent_traversals x avg_IO_per_traversal
    e.g., 100 concurrent 5-hop traversals x ~50 IO each = ~5000 IOPS minimum

Read replica scaling:
  Read replicas = ceil(max_concurrent_traversals / traversals_per_replica)
  Each replica serves its own copy of the graph (independent I/O pool)
  Auto-scaling target: EngineCPUUtilization 60% (scale-out threshold)

Neptune Streams filter patterns:
  Stream records contain: commitTimestamp, eventId, op, data
  Filter patterns:
    {"op": "ADD"}        → only insertions
    {"op": "REMOVE"}     → only deletions
    {"op": ["ADD","UPDATE"]} → insertions and updates
  Empty filter → all changes (highest volume)
```

**Key implication:** instance type determines both memory (graph working
set fit) and IOPS (traversal throughput). Read replica count scales
traversal concurrency horizontally. Stream filter patterns control
downstream processing volume — filter aggressively to reduce consumer
load.

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

```bash
# Create the cluster (with parameter group, encryption, IAM auth)
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-cluster \
  --engine neptune \
  --engine-version 1.3.2.1 \
  --master-username neptuneadmin \
  --master-user-password "SecureP@ssw0rd!2026" \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122 \
  --db-cluster-parameter-group-name my-neptune-params \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/aaa11122 \
  --enable-iam-database-authentication \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:05:00-mon:06:00"

# Create the primary instance
aws neptune create-db-instance \
  --db-instance-identifier my-neptune-primary \
  --db-instance-type db.r5.4xlarge \
  --engine neptune \
  --db-cluster-identifier my-neptune-cluster

# Create a read replica in a different AZ
aws neptune create-db-instance \
  --db-instance-identifier my-neptune-replica-1 \
  --db-instance-type db.r5.4xlarge \
  --engine neptune \
  --db-cluster-identifier my-neptune-cluster \
  --availability-zone us-east-1b
```

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

```bash
# List available instance options for Neptune
aws neptune describe-orderable-db-instance-options \
  --engine neptune \
  --query 'OrderableDBInstanceOptions[*].DBInstanceClass' --output text | sort -u
```

## Step 4 — Subnet groups and security groups

**Create a DB subnet group (requires >= 2 AZs):**

```bash
aws neptune create-db-subnet-group \
  --db-subnet-group-name my-neptune-subnet-group \
  --db-subnet-group-description "Neptune subnet group" \
  --subnet-ids subnet-aaa11122 subnet-bbb22233 subnet-ccc33344
```

**Security group (Neptune port 8182):**

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name neptune-cluster-sg --description "Neptune SG" \
  --vpc-id vpc-aaa11122 --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" --protocol tcp --port 8182 \
  --source-security-group-id sg-app11122
```

**Critical:** Neptune uses port 8182 for all client connections (both
Gremlin and SPARQL). The security group must allow inbound from the
application SG on port 8182.

## Step 5 — Parameter groups (neptune_enforce_ssl, neptune_query_timeout)

Parameter groups control engine-level configuration including SSL
enforcement, query timeouts, and Streams.

```bash
aws neptune create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-neptune-params \
  --db-parameter-group-family neptune1.3 \
  --description "Custom Neptune parameters"

aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-neptune-params \
  --parameters \
    ParameterName=neptune_enforce_ssl,ParameterValue=1,ApplyMethod=pending-reboot \
    ParameterName=neptune_query_timeout,ParameterValue=120000,ApplyMethod=immediate \
    ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot
```

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

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-iam \
  --engine neptune \
  --enable-iam-database-authentication \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122 \
  --db-cluster-parameter-group-name my-neptune-params
```

**IAM policy for Neptune access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["neptune-db:connect"],
      "Resource": "arn:aws:neptune:us-east-1:123456789012:cluster/my-neptune-iam/*"
    }
  ]
}
```

**Critical:** IAM database authentication MUST be enabled at cluster
creation. It cannot be toggled on afterward. The application uses SigV4
signing instead of a static password.

## Step 7 — Encryption at rest (KMS)

**Encryption is creation-time-only for Neptune clusters.** It CANNOT be
toggled on after the cluster exists.

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-encrypted \
  --engine neptune \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/aaa11122 \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122
```

To encrypt an existing non-encrypted cluster, create a new encrypted
cluster and load data via the bulk loader or Neptune Export/Import.

## Step 8 — Neptune Streams (change log)

Neptune Streams captures every graph mutation (ADD, UPDATE, REMOVE) in
a change log. Enable it in the parameter group.

```bash
# Enable Streams (static parameter — requires reboot)
aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-neptune-params \
  --parameters ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot

# Reboot the primary instance to apply
aws neptune reboot-db-instance \
  --db-instance-identifier my-neptune-primary
```

**Stream consumer pattern (polling the stream):**

```bash
# Query the stream for recent changes
curl -s "https://my-neptune-cluster.cluster-aaa11122.us-east-1.neptune.amazonaws.com:8182/streams" \
  -H "Content-Type: application/json" \
  -d '{
    "lastEventId": {"commitNum": 1, "opNum": 1},
    "limit": 100
  }'
```

**Stream filter patterns:**

```json
{"op": "ADD"}              // only insertions
{"op": "REMOVE"}           // only deletions
{"op": ["ADD","UPDATE"]}   // insertions and updates
{}                          // all changes (no filter)
```

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

```bash
# Export graph data for ML training
aws neptune start-ml-model-training-job \
  --job-id my-neptune-ml-job \
  --s3-url s3://my-neptune-ml-bucket/training/ \
  --role-arn arn:aws:iam::123456789012:role/NeptuneMLRole \
  --model-type NODE_CLASSIFICATION \
  --db-instance-identifier my-neptune-primary
```

**Key implication:** Neptune ML inference endpoints add latency to
queries. Use them for batch inference, not real-time low-latency paths.

## Step 10 — Global Database (cross-region)

Neptune Global Database provides cross-region read replicas for disaster
recovery and low-latency multi-region reads.

```bash
# Create the global cluster
aws neptune create-global-cluster \
  --global-cluster-identifier my-neptune-global \
  --source-db-cluster-identifier arn:aws:neptune:us-east-1:123456789012:cluster:my-neptune-cluster

# Add a secondary cluster in another region
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-secondary \
  --global-cluster-identifier my-neptune-global \
  --engine neptune \
  --db-subnet-group-name my-neptune-subnet-euwest \
  --vpc-security-group-ids sg-euwest111 \
  --region eu-west-1

# Create a read replica in the secondary region
aws neptune create-db-instance \
  --db-instance-identifier my-neptune-secondary-replica \
  --db-instance-type db.r5.4xlarge \
  --engine neptune \
  --db-cluster-identifier my-neptune-secondary \
  --region eu-west-1
```

**Constraints:** same engine version across regions; secondary cluster
is read-only until failover; replication lag depends on cross-region
network distance.

## Step 11 — Auto-scaling read replicas

Neptune supports Application Auto Scaling for read replicas based on
CloudWatch metrics.

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace neptune \
  --resource-id cluster:my-neptune-cluster \
  --scalable-dimension neptune:cluster:ReadReplicaCount \
  --min-capacity 1 --max-capacity 15

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --service-namespace neptune \
  --resource-id cluster:my-neptune-cluster \
  --scalable-dimension neptune:cluster:ReadReplicaCount \
  --policy-name my-scaling-policy --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"NeptuneReadReplicaLag"},"TargetValue":60.0,"ScaleOutCooldown":300,"ScaleInCooldown":300}'
```

**Key implication:** read replica auto-scaling adds replicas (0-15 max)
based on CPU utilization or replica lag. Replicas take minutes to become
available — spikes can still cause timeouts during scale-out.

## Step 12 — Bulk loader

The Neptune bulk loader is for initial or batch data ingestion from S3.

```bash
# Load data from S3 (Gremlin CSV format)
curl -s -X POST \
  "https://my-neptune-cluster.cluster-aaa11122.us-east-1.neptune.amazonaws.com:8182/loader" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "s3://my-neptune-data-bucket/nodes/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::123456789012:role/NeptuneBulkLoadRole",
    "mode": "NEW",
    "region": "us-east-1",
    "failOnError": true,
    "parallelism": "HIGH"
  }'
```

**Best practice:** use mode `NEW` for initial loads (fails if data
exists), mode `RESUME` for retrying partial loads. Set `parallelism`
to `HIGH` for large datasets.

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

```bash
# Monitor CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/Neptune \
  --metric-name EngineCPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=my-neptune-primary \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average

# Monitor graph storage growth
aws cloudwatch get-metric-statistics \
  --namespace AWS/Neptune \
  --metric-name VolumeBytesUsed \
  --dimensions Name=DBClusterIdentifier,Value=my-neptune-cluster \
  --start-time $(date -u -v-1D +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 --statistics Average
```

**Key metrics to alert on:**
- EngineCPUUtilization > 80% sustained → scale up or add replicas.
- BufferCacheHitRatio < 90% → graph working set exceeds memory; larger
  instance needed.
- VolumeBytesUsed approaching limit → storage scaling needed.
- GremlinErrorsPerSec > 0 → query errors or timeouts.

## Step 14 — Snapshot management

| Snapshot type | How | Retention |
|---|---|---|
| Automated | Within backup window | 1-35 days (backup-retention-period) |
| Manual | On-demand via API | Until manually deleted |

```bash
# Create manual snapshot
aws neptune create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier my-neptune-snapshot-20260805 \
  --db-cluster-identifier my-neptune-cluster

# Restore from snapshot
aws neptune restore-db-cluster-from-snapshot \
  --db-cluster-identifier my-neptune-restored \
  --snapshot-identifier my-neptune-snapshot-20260805 \
  --engine neptune \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122
```

## Step 15 — Recent features

- **Neptune Analytics (2023-2024):** Serverless graph analytics for
  ad-hoc analysis without provisioning a cluster. Separate service from
  Neptune Database.
- **OpenCypher support (2023-2024):** Added OpenCypher query language
  support alongside Gremlin and SPARQL on the same cluster.
- **Improved bulk loader performance (2023-2024):** Higher throughput
  and better error handling for large graph loads.
- **Enhanced Streams (2024-2025):** Stream metrics in CloudWatch,
  improved filtering capabilities.
- **Global Database improvements (2024-2025):** Lower replication lag,
  more regions, faster failover.
- **Graviton-based instances (2024-2025):** r7g instance types for
  improved price/performance.

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

```text
NEPTUNE: my-neptune-prod (db.r5.4xlarge, 1.3.2.1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Query language: Gremlin (primary), SPARQL (available)
  [✓] Topology: Primary + 2 read replicas (across 3 AZs)
  [✓] Instance type: db.r5.4xlarge (128 GB, 8000 baseline IOPS)
  [✓] Subnet group: my-neptune-subnet-group (3 AZs)
  [✓] Security group: sg-aaa11122 (port 8182)
  [✓] Parameter group: my-neptune-params (neptune_enforce_ssl=1, neptune_query_timeout=120000, neptune_streams=1)
  [✓] IAM database authentication: Enabled
  [✓] At-rest encryption (KMS): Enabled (key arn:aws:kms:us-east-1:...:key/aaa11122)
  [✓] Neptune Streams: Enabled (filter: {"op": ["ADD","UPDATE","REMOVE"]})
  [✓] Neptune ML: Not configured
  [✓] Global Database: Not configured
  [✓] Auto-scaling: Target tracking (EngineCPUUtilization, target 60%, min 1, max 5)
  [✓] Backup: Automated (retention 7 days, window 03:00-04:00 UTC)
  [✓] Snapshot window: 03:00-04:00 UTC (no overlap with maintenance mon:05:00-mon:06:00)
  [✓] Bulk loader: Ready (S3 s3://my-neptune-data/, IAM role arn:aws:iam::...:role/NeptuneBulkLoadRole)
  [✓] Tags: Environment=production, Application=fraud-detection
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier my-neptune-prod --region us-east-1
  aws neptune describe-db-instances --db-instance-identifier my-neptune-primary --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/Neptune --metric-name EngineCPUUtilization --dimensions Name=DBInstanceIdentifier,Value=my-neptune-primary --region us-east-1
```

## Error handling

### Cluster creation fails with "encryption not supported"

- Verify the engine version and instance type support encryption. All
  current Neptune instance types support storage encryption.

### Clients cannot connect to the cluster

- Check the security group allows inbound from the application SG on
  port 8182. Verify `neptune_enforce_ssl=1` requires clients to use TLS
  (wss:// for Gremlin, https:// for SPARQL).

### Read replicas lagging behind primary

- Check instance type — replicas should match the primary's type. Monitor
  `NeptuneReadReplicaLag` in CloudWatch. If lag is persistent, upgrade
  the replica instance type or reduce write throughput.

### Neptune Streams returning no records

- Verify `neptune_streams=1` in the parameter group and that the primary
  instance has been rebooted since the change. Streams only capture
  changes after enablement.

### Global Database replication failing

- Verify engine versions match across primary and secondary regions.
  Check the secondary cluster's security group and subnet group are
  correctly configured.

### Bulk loader errors

- Verify the S3 bucket is in the same region as the Neptune cluster.
  Check the IAM role has `s3:GetObject` and `s3:ListBucket` permissions.
  Use `mode: RESUME` to retry partial loads.

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
