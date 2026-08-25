---
name: documentdb-cluster-deployer
description: 'Provisions Amazon DocumentDB (MongoDB compatibility) clusters with production defaults: cluster creation (create-db-cluster), instance types (r5.large through r5.24xlarge, t3.medium), storage autoscaling, multi-AZ replication (primary + replicas), parameter groups, subnet groups, security groups, KMS encryption at rest, backup retention (1-35 days), global clusters (cross-region), change streams for CDC, indexing strategy (single vs compound vs text), MongoDB API compatibility version (3.6/4.0/5.0), connect via mongo shell, TLS (enable/disable), and CloudWatch metrics. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a DocumentDB cluster, adding instances, configuring change streams, setting up a global cluster, enabling storage autoscaling, or managing backup retention. Triggers: create documentdb cluster, documentdb instance, documentdb change streams, documentdb global cluster, documentdb storage autoscaling, documentdb subnet group, documentdb parameter group, documentdb...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with docdb access. Works with Terraform aws_docdb_cluster / aws_docdb_cluster_instance / aws_docdb_subnet_group / aws_docdb_global_cluster resources and CloudFormation AWS::DocDB::DBCluster templates.'
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
  tags: aws, documentdb, mongodb, cloudops, deploy, databases, provisioning, cluster, change-streams, global-cluster, storage-autoscaling, kms, backup, indexing
  dependencies: aws-orchestrator
  keywords: aws, documentdb, mongodb, document database, cloudops, deploy, provisioning, cluster, change streams, global cluster, storage autoscaling, kms encryption, backup retention, indexing, multi-az, parameter group, subnet group, tls
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
Activation keyword list moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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
Full dependency table and cross-dependency gotchas moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: the storage autoscaling ceiling
Autoscaling-ceiling heuristic moved to
[references/storage-and-changestreams.md](references/storage-and-changestreams.md).

## Expert heuristic: index before query (no query optimizer)
Index-type selection heuristic moved to
[references/global-clusters-and-indexing.md](references/global-clusters-and-indexing.md).

## Expert heuristic: change streams for CDC
Change-stream flow and resume-token gotcha moved to
[references/storage-and-changestreams.md](references/storage-and-changestreams.md).

## Expert heuristic: index build blocking writes (foreground vs background)
Foreground-vs-background index build behavior moved to
[references/global-clusters-and-indexing.md](references/global-clusters-and-indexing.md).

## Expert heuristic: MongoDB API compatibility gaps
Unsupported aggregation stages and feature gaps moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: TLS certificate rotation downtime
TLS certificate rotation lifecycle moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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
Enablement commands and driver consumption example moved to
[references/storage-and-changestreams.md](references/storage-and-changestreams.md).

## Step 10 — Indexing strategy (no query optimizer)
Connect and create-index commands moved to
[references/global-clusters-and-indexing.md](references/global-clusters-and-indexing.md).

## Step 11 — Global clusters
Global cluster creation commands moved to
[references/global-clusters-and-indexing.md](references/global-clusters-and-indexing.md).

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
Metrics and alert-threshold table moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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
Failure-mode deep dives (STORAGE_FULL, slow queries, change streams,
TLS handshake, replica lag) moved to [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/storage-and-changestreams.md](references/storage-and-changestreams.md) — storage autoscaling + CDC detail (now also holds the autoscaling-ceiling and change-stream heuristics and the Step 9 commands moved from this file)
- [references/global-clusters-and-indexing.md](references/global-clusters-and-indexing.md) — global cluster + indexing detail (now also holds the indexing heuristics and Step 10/11 commands moved from this file)
- [references/error-handling.md](references/error-handling.md) — STORAGE_FULL, slow queries, change-stream, TLS, replica-lag failure modes (moved from this file)
- [references/advanced-patterns.md](references/advanced-patterns.md) — dependency graph, MongoDB API gaps, TLS rotation, CloudWatch metrics, activation keywords (moved from this file)

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
