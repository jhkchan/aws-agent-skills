---
name: documentdb-cluster-deployer
description: 'Provisions Amazon DocumentDB (MongoDB compatibility) clusters with production defaults: cluster creation (create-db-cluster), instance types (r5.large through r5.24xlarge, t3.medium), storage autoscaling, multi-AZ replication (primary + replicas), parameter groups, subnet groups, security groups, KMS encryption at rest, backup retention (1-35 days), global clusters (cross-region), change streams for CDC, indexing strategy (single vs compound vs text), MongoDB API compatibility version (3.6/4.0/5.0), connect via mongo shell, TLS (enable/disable), and CloudWatch metrics. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a DocumentDB cluster, adding instances, configuring change streams, setting up a global cluster, enabling storage autoscaling, or managing backup retention. Triggers: create documentdb cluster, documentdb instance, documentdb change streams, documentdb global cluster, documentdb storage autoscaling, documentdb subnet group, documentdb
  parameter group, documentdb...'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with docdb access. Works with Terraform aws_docdb_cluster / aws_docdb_cluster_instance / aws_docdb_subnet_group / aws_docdb_global_cluster resources and CloudFormation AWS::DocDB::DBCluster templates.'
keywords:
- aws
- documentdb
- mongodb
- document database
- cloudops
- deploy
- provisioning
- cluster
- change streams
- global cluster
- storage autoscaling
- kms encryption
- backup retention
- indexing
- multi-az
- parameter group
- subnet group
- tls
tags:
- aws
- documentdb
- mongodb
- cloudops
- deploy
- databases
- provisioning
- cluster
- change-streams
- global-cluster
- storage-autoscaling
- kms
- backup
- indexing
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
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
  - aws
  - documentdb
  - mongodb
  - cloudops
  - deploy
  - databases
  - provisioning
  - cluster
  - change-streams
  - global-cluster
  - storage-autoscaling
  - kms
  - backup
  - indexing
  dependencies:
  - aws-orchestrator
  keywords:
  - create documentdb cluster
  - documentdb instance
  - documentdb change streams
  - documentdb global cluster
  - documentdb storage autoscaling
  - documentdb subnet group
  - documentdb parameter group
  - documentdb kms encryption
  - documentdb backup retention
  - documentdb index
  - mongo shell connect documentdb
  when_to_use: Invoke when the user wants to create an Amazon DocumentDB cluster, add instances to a cluster, configure change streams for CDC, set up a global cluster for cross-region disaster recovery, enable storage autoscaling, manage backup retention, create indexes, or connect via mongo shell. Do NOT invoke for Amazon RDS (use RDS skills), Amazon DynamoDB (use DynamoDB skills), Amazon ElastiCache (use ElastiCache skills), or Amazon Neptune (use Neptune skills).
---

# DocumentDB Cluster Deployer

An AWS CloudOps agent skill that provisions Amazon DocumentDB (MongoDB
compatibility) clusters with correct defaults. The skill walks the
operator through cluster creation, instance-type selection (r5/t3),
storage autoscaling with ceiling, multi-AZ replication, parameter
groups, subnet groups, security groups, KMS encryption, backup
retention, global clusters, change streams, and indexing strategy,
captures workload and durability decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create DocumentDB cluster, DocumentDB instance, DocumentDB change
streams, DocumentDB global cluster, DocumentDB storage autoscaling,
DocumentDB subnet group, DocumentDB parameter group, DocumentDB KMS
encryption, DocumentDB backup retention, DocumentDB index, mongo shell
connect DocumentDB.

## STRICT output contract

When this skill is invoked with a DocumentDB-provisioning request
(create a cluster, add instances, configure change streams, set up a
global cluster, enable storage autoscaling, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`DOCUMENTDB_CLUSTER:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Cluster architecture (cluster + instances) | Core model |
| Step 2 — Instance types (r5 vs t3) | Sizing |
| Step 3 — Storage autoscaling | Storage growth |
| Step 4 — Multi-AZ replication | High availability |
| Step 5 — Subnet groups and security groups | Network |
| Step 6 — Parameter groups | Configuration |
| Step 7 — KMS encryption | Security |
| Step 8 — Backup retention and point-in-time recovery | Durability |
| Step 9 — Change streams for CDC | Change data capture |
| Step 10 — Indexing strategy (no query optimizer) | Performance |
| Step 11 — Global clusters | Cross-region DR |
| Step 12 — MongoDB compatibility and connecting | Client access |
| Step 13 — TLS configuration | Security |
| Step 14 — CloudWatch metrics | Observability |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/storage-and-changestreams.md | Storage autoscaling + CDC detail |
| references/global-clusters-and-indexing.md | Global cluster + indexing detail |

## Mindset

**One-line takeaway:** Amazon DocumentDB is a managed MongoDB-compatible
database that separates compute (instances) from storage (cluster volume
that auto-expands). There is NO query optimizer — you MUST create indexes
BEFORE running queries, or every query is a collection scan. Change
streams are the recommended CDC mechanism.

Three misconceptions dominate DocumentDB misdesign at provisioning time:

- **"DocumentDB has a query optimizer like MongoDB."** It does NOT.
  DocumentDB lacks a query planner. Every query without a matching index
  is a full collection scan. Unlike MongoDB (which can create indexes on
  the fly or choose among indexes), DocumentDB requires explicit index
  creation BEFORE issuing queries. Failing to index before query is the
  #1 cause of production latency in DocumentDB.

- **"Storage autoscaling means I never need to think about storage."** It
  does not. DocumentDB storage autoscaling automatically grows the
  cluster volume, but there is a ceiling. If storage hits the ceiling
  (default 50 TB, or your configured maximum), the cluster stops
  accepting writes. You MUST set the autoscaling ceiling to match your
  projected growth, and monitor storage utilization against it.

- **"Change streams are optional for CDC."** They are the recommended
  approach. DocumentDB change streams provide ordered, resumable change
  events. Without change streams, you are limited to polling (full table
  scans), which is expensive and imprecise. Enable change streams at
  cluster creation if any downstream system needs CDC.

## Configuration dependency graph (novel heuristic)

DocumentDB configurations are NOT independent. The cluster must exist
before instances. The subnet group must exist before the cluster. Change
streams require parameter-group configuration. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subnet group | at least 2 subnets across 2 AZs | subnets must be private; no public DocumentDB | cluster creation |
| Security group | VPC exists | SG must allow port 27017 (or custom) from app tier | cluster network access |
| Parameter group | none (uses default initially) | change streams parameter requires cluster modification + reboot | change streams, TTL, profiling |
| KMS key | KMS key exists (if customer-managed) | KMS key cannot be changed after cluster creation without snapshot/restore | encryption at rest |
| Cluster (create-db-cluster) | subnet group, security group, KMS key, parameter group | cluster endpoint is immutable once created; storage volume auto-grows | instances, endpoints |
| Instances (create-db-instance) | cluster exists; instance class chosen | instances are created one at a time; failover priority is set per instance | compute capacity |
| Storage autoscaling | cluster exists | autoscaling ceiling must be set explicitly; hitting the ceiling stops writes | storage growth |
| Change streams | parameter group with change_streams_log_retention_duration > 0 | change stream retention can be 1-3 days; expired events are lost | CDC pipelines |
| Global cluster | primary cluster exists and is healthy | secondary clusters are read-only; failover is not automatic (must be scripted) | cross-region DR |
| Backup retention | cluster exists (set at creation or modify) | retention 1-35 days; point-in-time recovery enabled automatically with backup | PITR, snapshot restore |
| Indexes | cluster is accessible via mongo shell | creating an index on a large collection blocks; use background index builds | query performance |

**The storage-autoscaling-ceiling and index-before-query rows are the
ones a baseline model misses.** DocumentDB auto-grows storage but stops
at the ceiling. And without explicit indexes, every query is a scan. The
procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- The subnet group must span at least 2 AZs for multi-AZ clusters.
  Single-AZ subnet groups block multi-AZ deployment.
- Change streams require the parameter
  `change_streams_log_retention_duration` to be greater than 0 in the
  cluster parameter group. The default is 0 (disabled).
- KMS key is set at cluster creation. Changing it later requires a
  snapshot-restore cycle (downtime).
- Global cluster secondary clusters are read-only. Applications must
  be designed to read from the secondary or wait for promotion during
  failover.

## Expert heuristic: the storage autoscaling ceiling

A baseline model says "storage auto-grows." The correct heuristic
recognizes that autoscaling has a ceiling, and hitting it stops writes.

```text
DocumentDB storage autoscaling:
  Cluster volume starts at 10 GB (minimum), auto-grows in 10 GB increments.
  Ceiling: configurable up to 64 TB.

  When storage hits the ceiling:
    → Cluster enters STORAGE_FULL state
    → ALL writes are rejected (inserts, updates, deletes fail)
    → Resolution: increase the ceiling (modify-db-cluster) or delete data

  Expert rule:
    Set ceiling = projected_growth_12_months × 1.5 (50% headroom)
    Alert when free storage < 20% of ceiling
```

## Expert heuristic: index before query (no query optimizer)

DocumentDB does NOT have a query optimizer. A query without a matching
index is a full collection scan.

| Index type | When to use | Example |
|---|---|---|
| Single-field | Simple equality or range on one field | `{email: 1}` for user lookup |
| Compound | Multi-field equality + range (ESR rule: Equality, Sort, Range) | `{status: 1, created_at: -1}` |
| Text | Full-text search across string fields | `{description: "text"}` |
| TTL | Auto-expire documents after a duration | `{createdAt: 1}` with expireAfterSeconds |
| Unique | Enforce uniqueness | `{orderId: 1}` with unique: true |

**Expert rule:** create indexes BEFORE deploying queries that need them.
A query without a matching index is a full collection scan — on a 10M
document collection, that is seconds of latency and high CPU.

## Expert heuristic: change streams for CDC

Change streams provide ordered, resumable change events. They are the
recommended CDC mechanism for real-time data pipelines.

```text
Change stream flow:
  1. Enable change_streams_log_retention_duration (1-3 days) in parameter group
  2. Application opens a change stream via MongoDB driver:
     const stream = db.collection.watch([], { startAtOperationTime: timestamp })
  3. DocumentDB emits events: insert, update, delete, replace
  4. Application processes events and checkpoints resume token
  5. On restart, application resumes from last checkpoint token

  Expert rule:
    Enable change streams at CLUSTER CREATION (parameter group).
    Retention: 2 days (gives 48h of buffer for pipeline recovery).
    Always checkpoint resume tokens in a durable store.
```

**Resume-token invalidation gotcha:** the change stream resume token
encodes the cluster timestamp and log sequence number. If the change
stream log retention period expires (e.g., the consumer was offline
longer than `change_streams_log_retention_duration`), the token
becomes invalid — `resumeAfter` throws a `ChangeStreamHistoryLost`
error. The consumer must restart with `startAtOperationTime` set to
a timestamp within the current retention window. Expert rule: set
retention to 3 days (maximum) for critical CDC pipelines, and
checkpoint tokens to a durable store (DynamoDB, SQS) after each
batch, not in memory.

## Expert heuristic: index build blocking writes (foreground vs background)

A baseline model says "just create indexes." The expert knows that
DocumentDB index builds behave differently from MongoDB and can lock
a production cluster.

```text
DocumentDB index build behavior:
  ├── Foreground (default for createIndex):
  │     └── Blocks ALL writes to the collection for the duration
  │         of the build. On a 10M-document collection, this can
  │         be 5-20 minutes of write lockout.
  ├── Background ("background: true" option):
  │     └── NON-blocking — allows concurrent reads and writes.
  │         DocumentDB supports background builds on 4.0+.
  └── DocumentDB does NOT support the MongoDB "createIndexes"
        shell helper's automatic background detection.

Expert rule:
  1. ALWAYS use { background: true } for production index creation
  2. Schedule large index builds during low-traffic windows
  3. Monitor DatabaseCpuUtilization during build (> 80% = throttle)
  4. For compound indexes on > 5M docs, build on a replica first,
     then failover — the index replicates to the primary
```

**Key implication:** A foreground index build on a large collection
silently blocks all writes. Always pass `{ background: true }` and
monitor the build progress via `db.currentOp()`.

## Expert heuristic: MongoDB API compatibility gaps

DocumentDB implements the MongoDB wire protocol but does NOT support
100% of MongoDB's API surface. A baseline model assumes "MongoDB
compatible = drop-in replacement." The expert knows the gaps.

```text
Unsupported aggregation pipeline stages (DocumentDB 5.0):
  ├── $graphLookup — NOT supported (no graph traversal)
  ├── $merge — NOT supported (use $out for materialization)
  ├── $facet — limited support (no nested $facet)
  └── $bucket / $bucketAuto — NOT supported

Unsupported features:
  ├── Transactions — supported on 4.0+ but with constraints:
  │     cross-shard transactions NOT supported (single-shard only)
  ├── Retryable writes — NOT supported (retryWrites=false always)
  ├── Change stream $lookup stage — NOT supported in pipeline
  └── Collation in indexes — NOT supported

Expert rule:
  1. Audit aggregation pipelines BEFORE migrating from MongoDB
  2. Replace $graphLookup with application-side traversal
  3. Replace $merge with a two-step $out + application merge
  4. Test with the actual driver version, not just the shell
```

**Key implication:** "MongoDB-compatible" means wire-protocol-level
compatibility, not feature parity. Unmapped aggregation stages cause
runtime errors, not syntax errors — they fail at execution time, not
parse time.

## Expert heuristic: TLS certificate rotation downtime

DocumentDB clusters use a cluster certificate for TLS connections.
A baseline model assumes certificates rotate transparently. The
expert knows the rotation can cause connectivity blips.

```text
DocumentDB TLS certificate lifecycle:
  ├── Certificate is managed by AWS RDS/DocumentDB infrastructure
  ├── Rotation is automatic but NOT instant — the cluster endpoint
  │     gets a new cert, and existing connections using the old
  │     cert's fingerprint break on next TLS handshake
  ├── The rds-combined-ca-bundle.pem contains BOTH the old and
  │     new CA certs — clients using this bundle survive rotation
  └── Clients pinning a SPECIFIC certificate fingerprint break

Expert rule:
  1. NEVER pin a specific certificate fingerprint in the client
  2. ALWAYS use rds-combined-ca-bundle.pem (contains all CAs)
  3. When AWS announces CA rotation, update the CA bundle in
     application containers BEFORE the rotation date
  4. Use connection pooling with health checks — pools that don't
     validate TLS on reconnect will mask rotation failures
```

**Key implication:** TLS certificate rotation is transparent ONLY
if clients use the combined CA bundle. Pinned certificates or stale
CA bundles cause silent connection failures during rotation.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC with at least 2 AZs | DocumentDB requires multi-AZ subnet group for HA | `aws ec2 describe-subnets` |
| Subnet group (or subnets to create one) | Cluster needs a subnet group | `aws docdb describe-db-subnet-groups` |
| Security group allowing port 27017 | Client connectivity | `aws ec2 describe-security-groups` |
| KMS key (if customer-managed encryption) | Encryption at rest | `aws kms describe-key --key-id <alias>` |
| Instance class decision (r5 vs t3) | Compute sizing | Assess workload |
| Backup retention decision (1-35 days) | PITR window | Assess compliance needs |
| Storage autoscaling ceiling | Write outage prevention | Assess projected growth |
| MongoDB compatibility version (4.0/5.0) | Feature set depends on version | Assess driver compatibility |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Cluster architecture (cluster + instances)

DocumentDB uses a cluster architecture: one cluster endpoint, a primary
instance, and 0-15 replica instances. Storage is a shared cluster volume
(separated from compute).

| Component | Role | API |
|---|---|---|
| Cluster | Endpoint management, storage volume, backups, parameter group | `create-db-cluster` |
| Primary instance | Read + write | `create-db-instance` |
| Replica instances | Read-only (up to 15) | `create-db-instance` |
| Cluster endpoint | Writer endpoint (always points to primary) | automatic |
| Reader endpoint | Round-robin across replicas | automatic |

**The cluster is the storage and management boundary. Instances are
compute.** Adding instances adds read capacity; storage is shared.

## Step 2 — Instance types (r5 vs t3)

| Instance class | vCPU | Memory (GiB) | Use case |
|---|---|---|---|
| db.r5.large | 2 | 16 | Small production |
| db.r5.xlarge | 4 | 32 | Medium production |
| db.r5.2xlarge | 8 | 64 | Large production |
| db.r5.4xlarge | 16 | 128 | X-large production |
| db.r5.8xlarge | 32 | 256 | XX-large production |
| db.r5.16xlarge | 64 | 512 | Max primary |
| db.r5.24xlarge | 96 | 768 | Largest primary |
| db.t3.medium | 2 | 4 | Development/test |

**r5 instances** are memory-optimized — recommended for production.
**t3.medium** is burstable — suitable for development only. NOT
recommended for production because CPU credits deplete under sustained
load.

## Step 3 — Storage autoscaling

DocumentDB storage auto-grows from 10 GB. Set an explicit ceiling to
prevent STORAGE_FULL write outages.

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier my-docdb-cluster \
  --engine docdb \
  --master-username admin \
  --master-user-password 'UseAStrongPassword123!' \
  --db-subnet-group-name my-subnet-group \
  --vpc-security-group-ids sg-abc123 \
  --backup-retention-period 7 \
  --deletion-protection \
  --region us-east-1

# Monitor free storage
aws cloudwatch get-metric-statistics \
  --namespace AWS/DocDB \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBClusterIdentifier,Value=my-docdb-cluster \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average \
  --region us-east-1
```

**Expert rule:** set ceiling = projected 12-month growth x 1.5. Alert
when free storage drops below 20% of ceiling.

## Step 4 — Multi-AZ replication

DocumentDB provides multi-AZ availability with a primary instance in one
AZ and replicas in other AZs. If the primary fails, DocumentDB
automatically promotes a replica (failover takes ~30 seconds).

```bash
# Create the primary instance
aws docdb create-db-instance \
  --db-instance-identifier my-docdb-primary \
  --db-instance-class db.r5.large \
  --engine docdb \
  --db-cluster-identifier my-docdb-cluster \
  --region us-east-1

# Create a replica in a different AZ with failover priority
aws docdb create-db-instance \
  --db-instance-identifier my-docdb-replica-1 \
  --db-instance-class db.r5.large \
  --engine docdb \
  --db-cluster-identifier my-docdb-cluster \
  --preferred-availability-zone us-east-1b \
  --promotion-tier 0 \
  --region us-east-1
```

**Failover priority:** each instance has a priority (0 = highest). The
highest-priority replica is promoted during failover.

## Step 5 — Subnet groups and security groups

```bash
# Subnet group (requires at least 2 AZs)
aws docdb create-db-subnet-group \
  --db-subnet-group-name my-subnet-group \
  --db-subnet-group-description "DocumentDB subnet group" \
  --subnet-ids subnet-aaa111 subnet-bbb222 subnet-ccc333 \
  --region us-east-1

# Security group (port 27017 from app tier)
aws ec2 authorize-security-group-ingress \
  --group-id sg-docdb-cluster \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=27017,ToPort=27017,IpRanges=[{CidrIp=10.0.0.0/16}]" \
  --region us-east-1
```

## Step 6 — Parameter groups

Parameter groups control cluster-level settings including change streams,
profiling, and TLS.

```bash
aws docdb create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-param-group \
  --db-parameter-group-family docdb4.0 \
  --description "DocumentDB parameter group with change streams" \
  --region us-east-1

# Enable change streams (retention in seconds: 86400 = 1 day, 172800 = 2 days, 259200 = 3 days)
aws docdb modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-param-group \
  --parameters \
    ParameterName=change_streams_log_retention_duration,ParameterValue=172800,ApplyMethod=immediate \
    ParameterName=audit_logs,ParameterValue=enabled,ApplyMethod=immediate \
  --region us-east-1
```

**Key parameters:**

| Parameter | Default | Expert value | Why |
|---|---|---|---|
| change_streams_log_retention_duration | 0 (disabled) | 172800 (2 days) | Enables CDC with 48h recovery buffer |
| audit_logs | disabled | enabled | Compliance and security auditing |
| tls | enabled | enabled | Always keep TLS enabled in production |

## Step 7 — KMS encryption

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier my-docdb-cluster \
  --engine docdb \
  --master-username admin \
  --master-user-password 'UseAStrongPassword123!' \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --storage-encrypted \
  --db-subnet-group-name my-subnet-group \
  --vpc-security-group-ids sg-abc123 \
  --region us-east-1
```

**Critical:** KMS key cannot be changed after cluster creation without
snapshot-restore. Choose customer-managed key at creation for maximum
control.

## Step 8 — Backup retention and point-in-time recovery

```bash
# Set backup retention at creation (1-35 days)
aws docdb create-db-cluster \
  --db-cluster-identifier my-docdb-cluster \
  --engine docdb \
  --backup-retention-period 7 \
  ...

# Modify backup retention
aws docdb modify-db-cluster \
  --db-cluster-identifier my-docdb-cluster \
  --backup-retention-period 14 \
  --apply-immediately \
  --region us-east-1

# Restore to a point in time
aws docdb restore-db-cluster-to-point-in-time \
  --source-db-cluster-identifier my-docdb-cluster \
  --db-cluster-identifier my-docdb-restored \
  --restore-to-time 2026-08-05T12:00:00Z \
  --region us-east-1
```

Point-in-time recovery is automatically enabled when backup retention is
> 0.

## Step 9 — Change streams for CDC

Change streams must be enabled in the parameter group (see Step 6). Once
enabled, applications subscribe via the MongoDB driver.

```bash
# Enable change streams + reboot for parameter to take effect
aws docdb modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-param-group \
  --parameters \
    ParameterName=change_streams_log_retention_duration,ParameterValue=172800,ApplyMethod=immediate \
  --region us-east-1

aws docdb reboot-db-instance \
  --db-instance-identifier my-docdb-primary \
  --region us-east-1
```

```javascript
// Consume change streams (Node.js)
const { MongoClient } = require('mongodb');
const client = await MongoClient.connect(
  'mongodb://admin:password@cluster-endpoint:27017/?tls=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false',
  { tlsCAFile: 'rds-combined-ca-bundle.pem' }
);
const stream = client.db('mydb').collection('orders').watch();
stream.on('change', (next) => {
  console.log('Change event:', JSON.stringify(next));
  // Process and checkpoint resume token
});
```

## Step 10 — Indexing strategy (no query optimizer)

DocumentDB has NO query optimizer. Indexes MUST be created BEFORE
queries that need them.

```bash
# Connect to the cluster
mongo "mongodb://admin:password@cluster-endpoint:27017/?tls=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" \
  --tlsCAFile rds-combined-ca-bundle.pem
```

```javascript
// Single-field index
db.users.createIndex({ email: 1 })
// Compound index (ESR rule: Equality, Sort, Range)
db.orders.createIndex({ status: 1, created_at: -1 })
// Text index for search
db.products.createIndex({ name: "text", description: "text" })
// Unique index
db.accounts.createIndex({ accountId: 1 }, { unique: true })
// TTL index (auto-expire after 3600 seconds)
db.sessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 3600 })
// List indexes
db.users.getIndexes()
```

## Step 11 — Global clusters

DocumentDB global clusters provide cross-region replication with
typically under 1 second latency. One primary region (read-write) and
up to 5 secondary regions (read-only).

```bash
# Create the global cluster
aws docdb create-global-cluster \
  --global-cluster-identifier my-global-cluster \
  --source-db-cluster-identifier my-docdb-cluster \
  --region us-east-1

# Add a secondary cluster in another region
aws docdb create-db-cluster \
  --db-cluster-identifier my-docdb-cluster-eu \
  --engine docdb \
  --global-cluster-identifier my-global-cluster \
  --master-username admin \
  --master-user-password 'UseAStrongPassword123!' \
  --db-subnet-group-name my-subnet-group-eu \
  --region eu-west-1
```

**Key limitation:** global cluster failover is NOT automatic. You must
script it (typically with Lambda + EventBridge). Secondary clusters are
read-only until promoted.

## Step 12 — MongoDB compatibility and connecting

| Engine version | MongoDB wire compatibility | Key features |
|---|---|---|
| 5.0.0 | MongoDB 5.0 | Time series collections, stable API |
| 4.0.0 | MongoDB 4.0 | Transactions, change streams improvements |
| 3.6.0 | MongoDB 3.6 | Baseline — change streams, retries |

```bash
# Connect via mongo shell (with TLS)
mongo "mongodb://admin:password@cluster-endpoint:27017/?tls=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" \
  --tlsCAFile rds-combined-ca-bundle.pem

# Download the CA bundle
wget https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem
```

**Connection string:** `tls=true` (required), `replicaSet=rs0`,
`readPreference=secondaryPreferred`, `retryWrites=false` (DocumentDB
does not support retryable writes).

## Step 13 — TLS configuration

TLS is enabled by default on DocumentDB clusters. Disabling TLS is NOT
recommended for production.

```bash
# Check TLS status (parameter group)
aws docdb describe-db-cluster-parameters \
  --db-cluster-parameter-group-name my-param-group \
  --query 'Parameters[?ParameterName==`tls`]' \
  --region us-east-1
```

**Expert rule:** always keep TLS enabled. Disabling TLS exposes database
traffic in plaintext. Only disable for local development testing.

## Step 14 — CloudWatch metrics

| Metric | What it measures | Alert threshold |
|---|---|---|
| DatabaseCpuUtilization | CPU across instances | > 80% sustained 5 min |
| DatabaseFreeStorageSpace | Free storage (bytes) | < 20% of ceiling |
| DatabaseConnections | Active connections | Approaching max |
| DatabaseMemoryUsagePercentage | RAM utilization | > 90% sustained |
| DatabaseReplicaLag | Replica lag (seconds) | > 30 seconds |

## NEVER do these things

1. **NEVER deploy queries without creating indexes first.** DocumentDB
   has NO query optimizer. A query without a matching index is a full
   collection scan.

2. **NEVER leave the storage autoscaling ceiling at default without
   assessment.** Hitting the ceiling causes STORAGE_FULL and ALL writes
   are rejected. Set the ceiling with 50% headroom.

3. **NEVER disable TLS in production.** TLS is enabled by default for a
   reason. Only disable for local development testing.

4. **NEVER use t3.medium instances for production.** T3 instances are
   burstable — CPU credits deplete under sustained load. Use r5.

5. **NEVER create a single-instance cluster for production.** Always
   deploy at least 1 primary + 1 replica in different AZs.

6. **NEVER forget to enable change streams at creation.** Enabling
   later requires a parameter group change and cluster reboot.

7. **NEVER use retryWrites=true in the connection string.** DocumentDB
   does not support retryable writes. Always set `retryWrites=false`.

8. **NEVER assume global cluster failover is automatic.** Secondary
   promotion requires scripting (Lambda + EventBridge).

9. **NEVER change the KMS key after cluster creation without planning
   downtime.** Changing encryption requires a snapshot-restore cycle.

10. **NEVER skip deletion protection for production clusters.**

## Output format

```text
DOCUMENTDB_CLUSTER: <cluster-identifier> (<engine-version>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Cluster identifier: <name>
  [✓|✗] Engine version: <4.0|5.0> (MongoDB compatibility)
  [✓|✗] Instance class: <db.r5.large|db.t3.medium> — <purpose>
  [✓|✗] Instance count: <n> primary + <n> replicas (multi-AZ: yes|no)
  [✓|✗] Subnet group: <name> (spans <n> AZs)
  [✓|✗] Security group: <sg-id> (port 27017 from <cidr>)
  [✓|✗] Parameter group: <name> (change_streams: <enabled|disabled>, retention: <n> days)
  [✓|✗] KMS encryption: <customer-managed|aws-managed> (<key-id>)
  [✓|✗] Backup retention: <n> days (PITR: enabled)
  [✓|✗] Storage autoscaling ceiling: <n> TB (headroom: <n>%)
  [✓|✗] Change streams: <enabled|disabled> (retention: <n> days)
  [✓|✗] Indexing strategy: <single|compound|text|ttl|unique> indexes documented
  [✓|✗] Global cluster: <none|primary in <region>, secondary in <region>>
  [✓|✗] TLS: enabled (production default)
  [✓|✗] Deletion protection: enabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws docdb describe-db-clusters --db-cluster-identifier <cluster-id> --region <region>
  aws docdb describe-db-instances --query 'DBInstances[?DBClusterIdentifier==`<cluster-id>`]' --region <region>
  aws cloudwatch get-metric-statistics --namespace AWS/DocDB --metric-name DatabaseCpuUtilization --dimensions Name=DBClusterIdentifier,Value=<cluster-id> --region <region>
```

### Worked example — production multi-AZ cluster with change streams

```text
DOCUMENTDB_CLUSTER: orders-docdb (5.0.0)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster identifier: orders-docdb
  [✓] Engine version: 5.0.0 (MongoDB 5.0 compatibility)
  [✓] Instance class: db.r5.large — production
  [✓] Instance count: 1 primary + 2 replicas (multi-AZ: yes)
  [✓] Subnet group: docdb-subnet-group (spans 3 AZs)
  [✓] Security group: sg-docdb-001 (port 27017 from 10.0.0.0/16)
  [✓] Parameter group: docdb-prod-params (change_streams: enabled, retention: 2 days)
  [✓] KMS encryption: customer-managed (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Backup retention: 7 days (PITR: enabled)
  [✓] Storage autoscaling ceiling: 10 TB (headroom: 50%)
  [✓] Change streams: enabled (retention: 2 days)
  [✓] Indexing strategy: compound {status, created_at} + single {email} + text {name, description}
  [✓] Global cluster: none
  [✓] TLS: enabled (production default)
  [✓] Deletion protection: enabled
  [✓] Tags: Environment=production, Application=orders
VERIFICATION_COMMANDS:
  aws docdb describe-db-clusters --db-cluster-identifier orders-docdb --region us-east-1
  aws docdb describe-db-instances --query 'DBInstances[?DBClusterIdentifier==`orders-docdb`]' --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/DocDB --metric-name DatabaseCpuUtilization --dimensions Name=DBClusterIdentifier,Value=orders-docdb --region us-east-1
```

## Error handling

### Cluster stuck in STORAGE_FULL
- Storage has hit the autoscaling ceiling. Increase the ceiling with
  `modify-db-cluster` or delete data. All writes are rejected until free
  space is available.

### Queries are slow (seconds of latency)
- Missing indexes. DocumentDB has no query optimizer. Connect via mongo
  shell, run `db.collection.getIndexes()` to verify. Create indexes
  before redeploying the application queries.

### Change stream not emitting events
- `change_streams_log_retention_duration` is 0 in the parameter group.
  Set it to 172800 (2 days) and reboot the cluster.

### Connection failures (TLS handshake error)
- TLS is enabled but the client is not using the CA bundle. Download
  `rds-combined-ca-bundle.pem` and pass it via `--tlsCAFile`.

### Replica lag is high
- Check if the primary is overloaded (CPU, memory). Consider scaling up
  the instance class or adding replicas.

## Domain

AWS CloudOps / Amazon DocumentDB Cluster Provisioning & MongoDB-Compatible
Database Management.

## AWS documentation

- **DocumentDB Guide** — https://docs.aws.amazon.com/documentdb/latest/developerguide/what-is.html
- **Create a cluster** — https://docs.aws.amazon.com/documentdb/latest/developerguide/db-cluster-create.html
- **Change streams** — https://docs.aws.amazon.com/documentdb/latest/developerguide/change_streams.html
- **Storage autoscaling** — https://docs.aws.amazon.com/documentdb/latest/developerguide/limits.html#limits-storage
- **Global clusters** — https://docs.aws.amazon.com/documentdb/latest/developerguide/global-clusters.html
- **Indexing** — https://docs.aws.amazon.com/documentdb/latest/developerguide/best_practices.html
- **Connecting with mongo shell** — https://docs.aws.amazon.com/documentdb/latest/developerguide/connect_programmatically.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/documentdb/latest/developerguide/cloud_watch.html
