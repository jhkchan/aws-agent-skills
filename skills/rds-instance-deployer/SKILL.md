---
name: rds-instance-deployer
description: >-
  Provisions RDS and Aurora databases with production-grade defaults: instance
  class selection (burstable t-series vs memory-optimized r-series vs
  general-purpose m-series), security group scoping to app SG on the correct
  engine port (3306/5432/1433/1521), KMS encryption-at-creation (immutable),
  Multi-AZ for HA with automatic failover, automated backups with 1-35 day
  retention, Enhanced Monitoring + Performance Insights, parameter group
  tuning, option group engine-specific options, Aurora Serverless v2 with
  min/max capacity, Aurora Global Database for cross-region reads, Backtrack
  for MySQL rewinds, deletion protection, Blue/Green deployments, and Aurora
  LTES planning. Emits a READY_TO_DEPLOY checklist with verification commands.
  Use when creating a new RDS instance, hardening Aurora clusters, sizing
  instances, or generating IaC skeletons. Triggers: create RDS instance,
  provision Aurora, Multi-AZ setup, Aurora Serverless v2, Aurora Global
  Database, Blue/Green deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with rds, ec2, kms, iam, and
  cloudwatch access. Works with Terraform aws_db_instance / aws_rds_cluster
  resources and CloudFormation AWS::RDS::DBInstance / AWS::RDS::DBCluster
  templates.
keywords:
  - aws
  - rds
  - aurora
  - cloudops
  - deploy
  - provisioning
  - instance class
  - burstable
  - t-series
  - memory-optimized
  - r-series
  - general-purpose
  - m-series
  - security group
  - kms encryption
  - multi-az
  - standby
  - automatic failover
  - automated backups
  - backup retention
  - pitr
  - enhanced monitoring
  - performance insights
  - parameter group
  - option group
  - aurora serverless v2
  - aurora global database
  - backtrack
  - deletion protection
  - blue/green deployment
  - aurora ltes
  - aurora dsql
tags:
  - aws
  - rds
  - aurora
  - cloudops
  - deploy
  - databases
  - provisioning
  - multi-az
  - encryption
  - backups
  - performance-insights
  - parameter-group
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
  lifecycle_status: experimental
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - rds
    - aurora
    - cloudops
    - deploy
    - databases
    - provisioning
    - multi-az
    - encryption
    - backups
    - performance-insights
    - parameter-group
  dependencies:
    - aws-orchestrator
  keywords:
    - create rds instance
    - provision aurora
    - multi-az setup
    - performance insights
    - aurora serverless v2
    - parameter group tuning
    - aurora global database
    - backtrack mysql
    - blue/green deployment
    - aurora ltes
    - aurora dsql
    - deletion protection
    - enhanced monitoring
  when_to_use: >-
    Invoke when the user wants to create a new RDS or Aurora database with
    production defaults, harden an existing database for production, validate
    Multi-AZ posture, size an instance class for a workload, design Aurora
    Serverless v2 capacity bounds, set up Aurora Global Database, plan a
    Blue/Green deployment, or generate provisioning CLI commands / IaC
    templates. Do NOT invoke for auditing existing RDS posture (use
    rds-instance-auditor), query tuning, certificate/TLS expiry, or
    non-RDS databases (DynamoDB, ElastiCache, DocumentDB, Neptune).
---

# RDS Instance Deployer

An AWS CloudOps agent skill that provisions RDS and Aurora database
instances with correct defaults. The skill walks the operator through a
10-step provisioning procedure, captures the operator's workload decisions
(engine, instance class, Multi-AZ, capacity bounds), explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create RDS instance, provision Aurora, RDS deployment, Aurora deployment,
instance class selection, burstable t-series, memory-optimized r-series,
general-purpose m-series, security group scoping, KMS encryption at rest,
encryption at creation, Multi-AZ, standby, automatic failover, automated
backups, backup retention, PITR, Enhanced Monitoring, Performance Insights,
parameter group tuning, option group, Aurora Serverless v2, Aurora Global
Database, Backtrack, deletion protection, Blue/Green deployment, Aurora
Long-Term Extended Support, Aurora LTES, Aurora DSQL, RDS Custom.

## Invocation contract (hard requirement)

When this skill is invoked with an RDS/Aurora-provisioning request
(instance/cluster name, engine, workload shape, region, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY checklist
defined in §"Output format" using the literal all-caps labels `INSTANCE:`
(or `CLUSTER:` for Aurora), `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

## Mindset

**One-line takeaway:** RDS encryption and Aurora cluster topology are
decided at creation time — there is no in-place path to add encryption
later, and certain Aurora features (Global Database, Serverless v2 scaling
bounds) are scoped to the cluster, not the instance.

Three misconceptions dominate RDS/Aurora misdesign at provisioning time:

- **"I'll add encryption later."** `StorageEncrypted` is **immutable after
  creation**. The ONLY path to encrypt an unencrypted instance is snapshot
  → encrypted copy → restore-new → endpoint cutover — a multi-hour
  migration with application cutover. Decide encryption at creation, with
  the correct KMS CMK, on day one.

- **"Multi-AZ means the database is highly available to the application."**
  Multi-AZ failover recovers the database in 60-120 seconds. The application
  still needs client-side retry, DNS-cache tuning (`networkaddress.cache.ttl`),
  and connection-pool recycling. JVM clients cache DNS for 60 seconds by
  default — without tuning, a Multi-AZ failover still looks like a 5-30
  minute outage to the app. Provisioning the standby is necessary but
  NOT sufficient.

- **"Aurora instances are standalone databases."** For `aurora-*` engines,
  encryption, deletion protection, Multi-AZ, backup retention, backtrack,
  and Serverless v2 capacity are properties of the **DBCluster**, not the
  individual instance. Provisioning at the instance level only produces
  false confidence — the cluster is the unit of administration.

## Reasoning framework (why provisioning order matters)

RDS/Aurora configurations have **dependency, immutability, and blast-radius
semantics** that make the provisioning order non-trivial:

1. **KMS encryption BEFORE the first byte of data lands** — `StorageEncrypted`
   is immutable after `create-db-instance` / `create-db-cluster`. The KMS
   CMK ARN must be in the same region and its key policy must grant RDS.
   Post-creation encryption requires the snapshot-migration workflow.

2. **Subnet group + security group BEFORE the instance** — the instance
   launches into a VPC. The DB subnet group must span at least two AZs
   (for Multi-AZ) and the security group must scope inbound to the
   application's SG on the correct engine port. Tighten these BEFORE
   `create-db-instance`; loosening post-launch is fine, but starting
   permissive creates exposure windows.

3. **Parameter group BEFORE the instance** — `create-db-instance` accepts
   `--db-parameter-group-name`. Apply the tuned parameter group at creation
   so the database starts with the right settings; modifying the parameter
   group post-creation requires a reboot for `apply-method: pending-reboot`
   parameters.

4. **Option group BEFORE the instance** — engine-specific options (e.g.,
   SQL Server Native Encryption, Oracle OEM, PostgreSQL extensions) attach
   via the option group at creation.

5. **Multi-AZ at creation OR via modify** — Multi-AZ can be enabled at
   creation or later via `modify-db-instance --multi-az`. Enabling later
   causes a brief I/O suspension during standby provisioning. For Aurora,
   Multi-AZ is implicit (cluster instances across AZs).

6. **Aurora cluster topology BEFORE instances** — for Aurora, create the
   DB subnet group, the cluster parameter group, then the DBCluster (which
   creates the primary instance), then add Reader instances. The cluster
   carries encryption, retention, deletion protection, backtrack, and
   Serverless v2 capacity — these are not instance-scoped.

7. **Deletion protection LAST but enabled before production traffic** —
   enable deletion protection after the instance is confirmed available
   but before it accepts production traffic. Aurora deletion protection
   lives on the cluster.

## RDS configuration dependency graph (novel heuristic)

RDS configurations are NOT independent. Many are immutable after creation;
others silently degrade or queue behind maintenance windows.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| `StorageEncrypted` + `KmsKeyId` | KMS key ARN valid + key policy grants RDS | **IMMUTABLE after creation** — only path is snapshot → re-encrypt → restore-new | per-object CloudTrail KMS audit; encrypted snapshots; encrypted cross-region read replicas |
| DB subnet group | must span >= 2 AZs (for Multi-AZ) | a subnet group in 1 AZ silently blocks Multi-AZ enablement | VPC-RDS launch |
| Security group (VPC) | VPC exists; app SG exists | a `0.0.0.0/0` inbound on the DB port silently exposes the DB to the VPC's inbound traffic | network access scoping |
| Parameter group | must exist in same engine family | `apply-method: pending-reboot` params queue until next reboot | engine tuning (max_connections, shared_buffers, etc.) |
| Option group | must exist for engine + major version | some options require reboot; option group version mismatch on engine upgrade | engine features (audit, encryption, extensions) |
| Multi-AZ (non-Aurora) | subnet group spans >= 2 AZs | enabling causes 1-3 minute I/O suspension during standby provisioning | HA with automatic failover (60-120s) |
| Automated backups | none | setting `BackupRetentionPeriod: 0` IMMEDIATELY deletes existing backups + transaction logs | PITR within retention window (1-35 days) |
| Enhanced Monitoring | IAM role `rds-monitoring-role` (or custom) with `monitoring.rds.amazonaws.com` trust | `MonitoringInterval: 0` = off; engine metrics still flow but OS-level do not | OS-level metrics (CPU steal, swap, file systems) |
| Performance Insights | none (engine-supported) | `PerformanceInsightsRetentionPeriod: 7` (default) vs 731 (long-term) | query-level performance analysis |
| Deletion protection | instance/cluster ACTIVE | blocks `delete-db-instance` / `delete-db-cluster`; reversible | accidental-deletion / ransomware guardrail |
| Aurora Serverless v2 | `EngineMode: provisioned` (NOT `serverless`; v1 is deprecated) + `ServerlessV2ScalingConfiguration` | `MinCapacity` too low → cold-start latency; `MaxCapacity` too high → cost waste | burst scaling within bounds |
| Aurora Global Database | primary cluster in region-1; separate KMS CMK per region | replicas are read-only; failover/promotion is one-way (must re-establish reverse) | cross-region DR + cross-region read scaling |
| Backtrack (Aurora MySQL) | `EngineMode: provisioned` + `BacktrackWindow` set at cluster creation | Backtrack is NOT a snapshot restore — fast rewind of the cluster in-place; does not work with Aurora Serverless v1 | rapid recovery from accidental DDL/DML without PITR restore |
| Blue/Green deployments | both Blue (current) and Green (staging) clusters exist; same engine major version | switch-over is one-way per phase; rollback requires a new Green | zero-downtime major-version upgrades and schema changes |
| Aurora DSQL | separate from the Aurora cluster — opt-in feature | new service (2024-2025); not a drop-in replacement for Aurora PostgreSQL | distributed, eventually-consistent multi-Region writes |

**The four immutable-or-near-immutable rows are the ones a baseline model
misses.** Encryption, Aurora Serverless v2 scaling bounds, Global Database
topology, and Backtrack window are decided at creation. The procedure
below forces an explicit decision on each before the create call.

**Cross-dependency gotchas** (not visible in the table):
- Enabling Multi-AZ on a SQL Server instance uses Always On Availability
  Groups — some features (cross-database transactions in certain modes,
  memory-optimized tables) have constraints.
- A Read Replica's Multi-AZ posture is independent of the primary. A
  single-AZ Read Replica is fine for read scaling; the primary's Multi-AZ
  is the write-availability gate.
- Cross-Region Read Replicas require a separate KMS CMK in the destination
  region. An unencrypted primary silently blocks the entire cross-region
  DR topology.
- Setting `BackupRetentionPeriod: 0` is immediately destructive — it does
  NOT mean "stop future backups"; it deletes existing backups, transaction
  logs, and PITR history. The only recovery is a manual snapshot.
- Aurora cluster `DeletionProtection` is on the CLUSTER —
  `delete-db-instance` on a cluster member does not delete the cluster.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If any
are missing, the verdict is **PREREQUISITES_MISSING** with a specific gap
citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with RDS access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | KMS CMKs, subnet groups, and Aurora features are region-scoped | `aws configure get region` |
| VPC + at least 2 subnets in 2 distinct AZs | Multi-AZ requires 2 AZs; Aurora requires 3 AZs for optimal quorum | `aws ec2 describe-subnets` |
| DB subnet group spanning >= 2 AZs | The instance launches into the subnet group | `aws rds describe-db-subnet-groups` |
| Security group scoping inbound to app SG on the engine port | Loose SGs expose the DB | `aws ec2 describe-security-groups` |
| KMS key ARN (encryption is immutable — must decide at creation) | Post-creation encryption requires snapshot migration | `aws kms describe-key --key-id <cmk-id>` |
| Parameter group for the engine family | Default parameter group is not tunable; create a custom one | `aws rds describe-db-parameter-groups` |
| Option group for the engine + major version | Required for engine-specific features | `aws rds describe-option-groups` |
| Enhanced Monitoring IAM role | Required for OS-level metrics | `aws iam get-role --role-name rds-monitoring-role` |
| Master credentials secret (recommended: AWS Secrets Manager) | Hardcoded passwords in commands are an anti-pattern | `aws secretsmanager describe-secret --secret-id <id>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Engine + instance class selection

Choose the database engine and instance class based on the workload's
CPU, memory, and I/O profile.

**Engine selection:**

| Engine | Use when |
|---|---|
| MySQL | open-source OLTP, broad tooling compatibility |
| PostgreSQL | open-source OLTP with rich types, extensions (PostGIS, pgvector) |
| Amazon Aurora MySQL | MySQL-compatible with higher throughput, faster failover, Backtrack |
| Amazon Aurora PostgreSQL | PostgreSQL-compatible with Aurora storage, Serverless v2, Global Database |
| SQL Server | Microsoft ecosystem; Express/Web/Standard/Enterprise editions |
| Oracle | legacy enterprise workloads; BYOL or license-included |
| MariaDB | MySQL-fork compatibility |

**Instance class families:**

| Family | Class prefix | Characteristics | Use when |
|---|---|---|---|
| Burstable | `db.t4g`, `db.t3` | Baseline CPU + burst credits (CloudWatch `CPUCreditBalance`); cheapest | Dev/test, low-traffic apps, microservices with bursty load |
| General-purpose | `db.m7g`, `db.m6i`, `db.m5` | Balanced CPU/memory; balanced network | Most OLTP workloads, web app backends |
| Memory-optimized | `db.r7g`, `db.r6i`, `db.r6g` | High memory-to-CPU ratio | In-memory sorts, large working set, analytics, Aurora (storage is shared, but buffer cache matters) |
| Compute-optimized | `db.c7g`, `db.c6i` | High CPU-to-memory ratio | Compute-heavy workloads (some analytics, batch) |
| Storage-optimized | `db.x2g`, `db.x2iedn` | Very high memory + direct-attached NVMe | Large in-memory databases, Oracle/SAP |

**Graviton (g-series) preference**: Graviton (g) instances typically offer
~20% price/perf improvement over Intel (i) for the same workload. Prefer
`db.m7g`, `db.r7g`, `db.t4g` unless you have a specific Intel/AMD
compatibility requirement.

**Sizing rule of thumb**:
- Buffer cache ~70-80% of total memory for OLTP (PostgreSQL `shared_buffers`
  ~25% is the conservative default; MySQL `innodb_buffer_pool_size` ~75%).
- Plan for `max_connections` based on `(available_memory_MB / per_connection_memory)`.
  Each PostgreSQL connection forks a process (~5-10MB); each MySQL thread
  is lighter (~256KB-2MB).
- For Aurora, the buffer cache is per-instance — Reader instances each
  have their own cache. Size each Reader independently.

**Common mistake**: picking `db.t3.micro` for a "small production workload."
Burstable classes burn CPU credits under sustained load and throttle to
a low baseline once credits are exhausted. Use `db.t*` only for dev/test
or workloads with measurable idle time; use `db.m*` or `db.r*` for
production OLTP.

### Step 2 — Network: subnet group + security group

Tighten network access BEFORE `create-db-instance`. Starting permissive
creates exposure windows; loosening post-launch is the safe direction.

**DB subnet group** must span at least 2 AZs (Multi-AZ requirement). For
Aurora, span all 3 AZs in the region for optimal quorum behavior.

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name <name>-subnet-group \
  --db-subnet-group-description "Subnet group for <name>" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc
```

**Security group** inbound rule: scope to the application's security group
on the engine port. NEVER use `0.0.0.0/0` on a DB port.

| Engine | Default port |
|---|---|
| MySQL / Aurora MySQL / MariaDB | 3306 |
| PostgreSQL / Aurora PostgreSQL | 5432 |
| SQL Server | 1433 |
| Oracle | 1521 |
| Aurora PostgreSQL with Babelfish | 1433 (TDS) + 5432 (PostgreSQL) |

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <db-sg-id> \
  --protocol tcp \
  --port 5432 \
  --source-security-group-id <app-sg-id>
```

**Defense-in-depth**: also enable TLS at the engine level via the parameter
group (`rds.force_ssl=1` for PostgreSQL, `require_secure_transport=ON`
for MySQL) so the database rejects plaintext connections even if the SG
is later loosened.

### Step 3 — Encryption (immutable — decide at creation)

`StorageEncrypted` cannot be toggled in place. The ONLY path to encrypt
an unencrypted instance is snapshot → encrypted copy → restore-new →
cutover — a multi-hour migration. Decide at creation.

```bash
aws rds create-db-instance ... \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:key/<cmk-id>
```

For Aurora, encryption is set on the DBCluster:
```bash
aws rds create-db-cluster ... \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:key/<cmk-id>
```

**KMS CMK choice:**
- **AWS-managed `aws/rds` key**: zero key-management overhead; cannot
  customize the key policy. Fine for dev/test.
- **Customer-managed CMK**: full key-policy control, rotation, CloudTrail
  per-call audit. Required for compliance workloads (PCI-DSS, HIPAA,
  SOC2, FedRAMP) and cross-account scenarios.

**CMK key policy must grant** `kms:GenerateDataKey` + `kms:Decrypt` to
`rds.<region>.amazonaws.com` AND to the calling principal. Verify with
`aws kms get-key-policy` after creation.

**Cross-Region Read Replicas**: each replica region requires a separate
CMK in that region. An unencrypted primary silently blocks the entire
cross-region DR topology — there is no path to create an encrypted
cross-region replica from an unencrypted source.

**KMS CMK rotation**: enabling annual rotation generates new key material
for NEW encrypt operations; existing ciphertext continues to decrypt with
prior key material indefinitely. There is no in-place CMK re-encryption
for RDS.

### Step 4 — Multi-AZ (high availability)

Multi-AZ provides a synchronous standby in a second AZ with automatic
failover (60-120 seconds). The standby is NOT usable for reads —
read-scaling requires separate Read Replicas.

**Non-Aurora:**
```bash
aws rds create-db-instance ... --multi-az
# Or enable later (causes 1-3 minute I/O suspension):
aws rds modify-db-instance --db-instance-identifier <id> --multi-az
```

**Aurora**: Multi-AZ is implicit — the cluster spans AZs by default. Add
Reader instances in different AZs for read-scaling and to act as failover
targets.

```bash
aws rds create-db-instance \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier <cluster> \
  --db-instance-identifier <cluster>-reader-1 \
  --availability-zone us-east-1b
```

**Common mistakes:**
- Expecting the Multi-AZ standby to serve reads. It does not. Read
  Replicas are a separate feature.
- Forgetting client-side retry / DNS-cache tuning. JVM default
  `networkaddress.cache.ttl=60`; without lowering, a failover looks like
  a 60s+ outage to the app.
- Enabling Multi-AZ with `--apply-immediately` on a production instance
  during peak write hours — the I/O suspension interrupts live writes.
  Schedule in the maintenance window.

### Step 5 — Automated backups + PITR

`BackupRetentionPeriod` (1-35 days) controls PITR coverage. Default is 7.
Setting it to 0 is IMMEDIATELY DESTRUCTIVE — deletes existing backups,
transaction logs, and PITR history.

```bash
aws rds create-db-instance ... --backup-retention-period 14
# Or modify:
aws rds modify-db-instance --db-instance-identifier <id> --backup-retention-period 14
```

For Aurora, retention is set on the cluster. Aurora does not accept 0
(API rejects it; continuous backups).

**Recommended retention by workload:**
- Production OLTP: 7-14 days (PITR for accidental writes).
- Regulated (HIPAA/financial): 35 days (maximum).
- Dev/test: 1-3 days (sufficient for "I broke it yesterday").

**Backup window**: a daily window where the full snapshot runs. RDS picks
a random 30-minute window if not specified; choose a low-write period.

### Step 6 — Enhanced Monitoring + Performance Insights (enable both)

These are DIFFERENT features and both should be on for production.

**Enhanced Monitoring** — OS-level metrics (CPU steal, swap, file systems,
process list) emitted by an agent on the DB host. Requires the
`rds-monitoring-role` IAM role.

```bash
aws rds create-db-instance ... \
  --monitoring-interval 30 \
  --monitoring-role-arn arn:aws:iam::<account-id>:role/rds-monitoring-role
```

Intervals: 1/5/10/15/30/60 seconds. Default recommendation: **30 seconds**
(balance of granularity vs. CloudWatch Logs cost).

**Performance Insights** — query-level performance analysis. Retention:
7 days (free) or 731 days (long-term, additional cost).

```bash
aws rds create-db-instance ... \
  --enable-performance-insights \
  --performance-insights-retention-period 7  # or 731
```

**Common mistake**: confusing the two. Enhanced Monitoring is OS-level
(CPU steal, swap); Performance Insights is query-level (top SQL by
load). Both are needed for production observability.

### Step 7 — Parameter group + Option group

**Parameter group** — engine-level tuning. Create a CUSTOM parameter
group (default is not editable).

Common tuning parameters:

| Engine | Parameter | Default | Recommended starting point |
|---|---|---|---|
| PostgreSQL | `shared_buffers` | 128MB | ~25% of instance memory |
| PostgreSQL | `work_mem` | 4MB | 16-64MB (lower if many connections) |
| PostgreSQL | `max_connections` | 150 | size to workload; use a pooler (PgBouncer/RDS Proxy) instead of unbounded |
| PostgreSQL | `rds.force_ssl` | 0 | 1 (defense-in-depth) |
| MySQL | `innodb_buffer_pool_size` | varies | ~75% of instance memory |
| MySQL | `max_connections` | 150 | size to workload |
| MySQL | `require_secure_transport` | OFF | ON (defense-in-depth) |
| SQL Server | `max server memory (MB)` | varies | total memory minus 2-4GB for OS |
| Oracle | `processes` | 150 | size to workload |

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name <name>-params \
  --db-parameter-group-family postgres14 \
  --description "Custom params for <name>"

aws rds modify-db-parameter-group \
  --db-parameter-group-name <name>-params \
  --parameters "ParameterName=shared_buffers,ParameterValue={DBInstanceClassMemory/4},ApplyMethod=pending-reboot" \
               "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=immediate"
```

**Option group** — engine-specific features (audit, encryption, extensions).

```bash
aws rds create-option-group \
  --option-group-name <name>-options \
  --engine-name postgres \
  --major-engine-version 14 \
  --option-group-description "Options for <name>"

aws rds modify-option-group \
  --option-group-name <name>-options \
  --options OptionName=pgaudit,OptionSettings=[{Name=pgaudit.log,Value=write,ddl}]
```

**Apply at creation**: `create-db-instance --db-parameter-group-name <name>-params --option-group-name <name>-options`.

### Step 8 — Aurora-specific features (Serverless v2, Global Database, Backtrack)

For `aurora-*` engines, several features are cluster-scoped.

**Aurora Serverless v2** (recommended over v1 — v1 is being deprecated):
scaling is governed by `ServerlessV2ScalingConfiguration` on the cluster.

```bash
aws rds create-db-cluster ... \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16,SecondsUntilAutoPause=0
```

- **MinCapacity**: 0.5-128 ACU (Aurora Capacity Units). Too-low causes
  cold-start latency on the first query after idle. 0.5 is fine for
  dev/test; 2-4 for production.
- **MaxCapacity**: caps cost. Too-high wastes spend; size to peak workload.
- **SecondsUntilAutoPause**: 0 means "never pause" (recommended for
  production). Serverless v2 does not pause to zero like v1 did.

**Aurora Global Database** (cross-region read scaling + DR):

```bash
aws rds create-global-cluster \
  --global-cluster-identifier <global-name> \
  --source-cluster-identifier <primary-cluster-id> \
  --engine aurora-mysql
```

Each region's cluster has its OWN KMS CMK. Replication is typically
< 1 second latency. **Failover is one-way** — after promoting a
secondary, you must explicitly re-establish the reverse replication
topology.

**Backtrack** (Aurora MySQL only — fast in-place rewind):

```bash
aws rds create-db-cluster ... \
  --backtrack-window 72   # 0-72 hours; default is 0 (disabled)
```

Backtrack is NOT a snapshot restore — it rewinds the cluster in place,
typically in minutes. Useful for "oops" DDL/DML without PITR restore.
Does not work with Aurora Serverless v1.

### Step 9 — Deletion protection + tags

**Deletion protection** — blocks `delete-db-instance` / `delete-db-cluster`.

```bash
aws rds modify-db-instance --db-instance-identifier <id> --deletion-protection
# For Aurora, on the cluster:
aws rds modify-db-cluster --db-cluster-identifier <cluster> --deletion-protection
```

Note: `delete-db-instance` on a cluster member does NOT delete the cluster.
To fully remove an Aurora DB, you must delete the cluster after removing
all instances (with deletion protection disabled).

**Tags** — cost allocation, automation, ownership.

```bash
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:<region>:<account-id>:db:<id> \
  --tags "[{Key=Environment,Value=production},{Key=Workload,Value=orders}]"
```

### Step 10 — Latest features: Blue/Green, LTES, Aurora DSQL

**Blue/Green deployments** (GA 2024) — create a staging "Green" environment
that replicates from "Blue" (current production). Switch over with
no-downtime. Use for major-version upgrades and risky schema changes.

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name <name>-bg \
  --source arn:aws:rds:<region>:<account-id>:cluster:<current-cluster> \
  --target-engine-version 8.0 \
  --target-db-parameter-group-name <new-params>
```

Switchover is one-way; rollback requires creating a new Green.

**Aurora MySQL Long-Term Extended Support (LTES)** (2024-2025): Aurora MySQL
community versions reach end-of-life; LTES provides extended support for
specific versions at additional cost. Plan major-version upgrades BEFORE
the community EOL date to avoid LTES charges.

**Aurora DSQL** (2024-2025): A separate distributed SQL service (not part
of the Aurora cluster). Opt-in for new workloads requiring multi-Region
eventually-consistent writes. Not a drop-in replacement for Aurora
PostgreSQL.

## NEVER do these things

1. **NEVER create an RDS instance without `--storage-encrypted` planning
   to "add encryption later."** `StorageEncrypted` is immutable after
   creation. The ONLY path is snapshot → encrypted copy → restore-new →
   cutover — a multi-hour migration with app cutover. Decide at creation
   with the correct KMS CMK.

2. **NEVER use the AWS-managed `aws/rds` KMS key for compliance workloads
   (PCI-DSS / HIPAA / SOC2 / FedRAMP).** You cannot customize the key
   policy, so you lose the second access gate (`kms:Decrypt`). Always
   provision a customer-managed CMK with an explicit key policy.

3. **NEVER scope the security group inbound to `0.0.0.0/0` on the DB
   port.** Always scope to the application's security group reference
   (or a specific CIDR). Pair with TLS enforcement in the parameter
   group as defense-in-depth.

4. **NEVER set `BackupRetentionPeriod` to 0 without an explicit warning.**
   Setting 0 is IMMEDIATELY DESTRUCTIVE — deletes existing backups,
   transaction logs, and PITR history. The only recovery is a manual
   snapshot.

5. **NEVER treat Aurora instance-level `StorageEncrypted` /
   `DeletionProtection` as authoritative.** For Aurora these are cluster
   properties. Audit and provision at the cluster level.

6. **NEVER enable Multi-AZ with `--apply-immediately` on a production
   instance during peak write hours.** Multi-AZ standby provisioning
   causes a 1-3 minute I/O suspension. Schedule in the maintenance window.

7. **NEVER expect Multi-AZ standby to serve reads.** The standby is a
   failover target only. Read Replicas are a separate feature for
   read-scaling.

8. **NEVER confuse Enhanced Monitoring with Performance Insights.**
   Enhanced Monitoring = OS-level (CPU steal, swap). Performance Insights
   = query-level (top SQL). Both are needed for production observability.

9. **NEVER size Aurora Serverless v2 `MinCapacity: 0.5` for a production
   workload with latency requirements.** Cold-start latency on the first
   query after idle can exceed SLAs. Use `MinCapacity: 2-4` for
   production; reserve 0.5 for dev/test.

10. **NEVER assume a cross-Region Read Replica is encrypted because the
    primary is.** Each region's cluster has its OWN KMS CMK. Verify
    `KmsKeyId` resolves to an active key in the replica's region.

11. **NEVER create an Aurora cluster with `EngineMode: serverless` (v1)
    for new workloads.** Aurora Serverless v1 is being deprecated in
    favor of v2. Use `EngineMode: provisioned` with
    `ServerlessV2ScalingConfiguration`.

12. **NEVER treat `DeletionProtection` as a security control.** Any
    principal with `rds:ModifyDBInstance` / `rds:ModifyDBCluster` can
    disable it. It is an accidental-deletion / ransomware guardrail, not
    a defense against a determined attacker with database-admin rights.

13. **NEVER modify a DB subnet group or security group mid-maintenance
    window without verifying in-flight operations.** Modifications queue
    behind `PendingModifiedValues`. Always confirm `DBInstanceStatus:
    available` before invoking `modify-db-instance`.

## Output format

```text
INSTANCE: <db-instance-identifier>      # or CLUSTER: <db-cluster-identifier> for Aurora
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Engine: <mysql|postgres|aurora-mysql|aurora-postgresql|...> <version>
  [✓|✗] Instance class: <db.x7g.size> (<family rationale>)
  [✓|✗] DB subnet group: spans <N> AZs
  [✓|✗] Security group: scoped to app SG on port <engine-port> (TLS enforced via parameter group)
  [✓|✗] Encryption: KMS <customer-managed CMK | aws/rds> (<key-arn>) — enabled at creation
  [✓|✗] Multi-AZ: Enabled (standby in <az>) | Disabled | Aurora (cluster-spanning AZs)
  [✓|✗] Automated backups: <N>-day retention (backup window: <window>)
  [✓|✗] Enhanced Monitoring: 30-second interval (role: rds-monitoring-role)
  [✓|✗] Performance Insights: Enabled (retention: <7|731> days)
  [✓|✗] Parameter group: <name> (key params: <list>)
  [✓|✗] Option group: <name> (options: <list>)
  [✓|✗] Deletion protection: Enabled | Disabled
  [Aurora-only] Serverless v2: MinCapacity=<n>, MaxCapacity=<n>
  [Aurora-only] Global Database: <regions> | Single-region
  [Aurora MySQL-only] Backtrack: <N>-hour window | Disabled
  [✓|✗] Tags: <list>
VERIFICATION_COMMANDS:
  aws rds describe-db-instances --db-instance-identifier <id>
  aws rds describe-db-clusters --db-cluster-identifier <cluster>   # Aurora
  aws kms describe-key --key-id <cmk-id>
  aws ec2 describe-security-groups --group-ids <db-sg-id>
  aws iam get-role --role-name rds-monitoring-role
```

### Worked example — Aurora PostgreSQL production cluster

```text
CLUSTER: prod-orders-pg
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: aurora-postgresql 16.3
  [✓] Instance class: db.r7g.large (memory-optimized for buffer cache; Graviton for price/perf)
  [✓] DB subnet group: prod-db-subnet-group spanning 3 AZs (us-east-1a/b/c)
  [✓] Security group: sg-prod-db inbound from sg-prod-app on port 5432; rds.force_ssl=1
  [✓] Encryption: KMS customer-managed CMK (alias/prod-rds-key) — enabled at creation
  [✓] Multi-AZ: Aurora cluster spanning 3 AZs (1 writer + 2 readers)
  [✓] Automated backups: 14-day retention (backup window: 03:00-04:00 UTC)
  [✓] Enhanced Monitoring: 30-second interval (role: rds-monitoring-role)
  [✓] Performance Insights: Enabled (retention: 7 days)
  [✓] Parameter group: prod-orders-pg-params (shared_buffers={DBInstanceClassMemory/4}, rds.force_ssl=1, log_statement=ddl)
  [✓] Option group: prod-orders-pg-options (pgaudit)
  [✓] Deletion protection: Enabled (on cluster)
  [✓] Serverless v2: N/A (provisioned instance class)
  [✓] Global Database: Single-region (us-east-1)
  [✓] Backtrack: N/A (Aurora PostgreSQL does not support Backtrack)
  [✓] Tags: Environment=production, Workload=orders, Owner=platform-team
VERIFICATION_COMMANDS:
  aws rds describe-db-clusters --db-cluster-identifier prod-orders-pg
  aws rds describe-db-instances --db-instance-identifier prod-orders-pg-0
  aws kms describe-key --key-id alias/prod-rds-key
  aws ec2 describe-security-groups --group-ids sg-prod-db
  aws iam get-role --role-name rds-monitoring-role
```

## Recent AWS features (2024-2026)

- **Blue/Green deployments GA (2024):** Create a staging environment with
  replicated data for zero-downtime database updates. Use for major
  version upgrades and risky schema changes. Provisioning tip: plan the
  Green cluster's parameter/option groups in advance — switchover is fast,
  preparation is not.
- **Aurora Serverless v2 scaling improvements (2024-2025):** Faster
  scaling and more predictable capacity. Provisioning tip: `MinCapacity`
  of 0.5 is fine for dev/test; 2-4 for production to avoid cold-start
  latency.
- **Aurora MySQL Long-Term Extended Support (LTES) (2024-2025):**
  Extended support for specific Aurora MySQL community versions at
  additional cost. Provisioning tip: plan major-version upgrades BEFORE
  the community EOL date to avoid LTES charges.
- **Aurora DSQL (2024-2025):** Separate distributed SQL service for
  multi-Region eventually-consistent writes. Provisioning tip: not a
  drop-in replacement for Aurora PostgreSQL — new workloads only.
- **IAM database authentication enhancements (2024):** Longer token
  validity and broader engine support. Provisioning tip: prefer IAM
  database auth over password auth for application connections where the
  engine supports it.
- **RDS Custom enhancements (2024):** More OS-level customization for
  SQL Server and Oracle. Provisioning tip: AWS manages the database
  engine but not the OS — plan OS-level patching separately.
- **Graviton (g-series) instance classes (2024-2025):** `db.m7g`,
  `db.r7g`, `db.t4g` offer ~20% price/perf improvement over Intel.
  Provisioning tip: default to Graviton unless a specific Intel/AMD
  compatibility requirement exists.

## Domain

AWS CloudOps / RDS & Aurora Database Provisioning, HA, and Observability.

## AWS documentation

- **Amazon RDS User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- **Amazon Aurora User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html
- **RDS Security** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html
- **Multi-AZ Deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html
- **Aurora Serverless v2** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- **Aurora Global Database** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html
- **Blue/Green Deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html
- **Performance Insights** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html
