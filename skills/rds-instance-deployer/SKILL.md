---
name: rds-instance-deployer
description: 'Provisions RDS and Aurora databases with production-grade defaults: instance class selection (burstable t-series vs memory-optimized r-series vs general-purpose m-series), security group scoping to app SG on the correct engine port (3306/5432/1433/1521), KMS encryption-at-creation (immutable), Multi-AZ for HA with automatic failover, automated backups with 1-35 day retention, Enhanced Monitoring + Performance Insights, parameter group tuning, option group engine-specific options, Aurora Serverless v2 with min/max capacity, Aurora Global Database for cross-region reads, Backtrack for MySQL rewinds, deletion protection, Blue/Green deployments, and Aurora LTES planning. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a new RDS instance, hardening Aurora clusters, sizing instances, or generating IaC skeletons. Triggers: create RDS instance, provision Aurora, Multi-AZ setup, Aurora Serverless v2, Aurora Global Database, Blue/Green deployment.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with rds, ec2, kms, iam, and cloudwatch access. Works with Terraform aws_db_instance / aws_rds_cluster resources and CloudFormation AWS::RDS::DBInstance / AWS::RDS::DBCluster templates.'
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
  lifecycle_status: experimental
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, rds, aurora, cloudops, deploy, databases, provisioning, multi-az, encryption, backups, performance-insights, parameter-group
  dependencies: aws-orchestrator
  keywords: aws, rds, aurora, cloudops, deploy, provisioning, instance class, burstable, t-series, memory-optimized, r-series, general-purpose, m-series, security group, kms encryption, multi-az, standby, automatic failover, automated backups, backup retention, pitr, enhanced monitoring, performance insights, parameter group, option group, aurora serverless v2, aurora global database, backtrack, deletion protection, blue/green deployment, aurora ltes, aurora dsql
  when_to_use: Invoke when the user wants to create a new RDS or Aurora database with production defaults, harden an existing database for production, validate Multi-AZ posture, size an instance class for a workload, design Aurora Serverless v2 capacity bounds, set up Aurora Global Database, plan a Blue/Green deployment, or generate provisioning CLI commands / IaC templates. Do NOT invoke for auditing existing RDS posture (use rds-instance-auditor), query tuning, certificate/TLS expiry, or non-RDS databases (DynamoDB, ElastiCache, DocumentDB, Neptune).
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

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## RDS configuration dependency graph (novel heuristic)

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


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

> Moved verbatim to [`references/instance-classes-and-parameter-tuning.md`](references/instance-classes-and-parameter-tuning.md) — load on demand.


### Step 2 — Network: subnet group + security group

Tighten network access BEFORE `create-db-instance`. Starting permissive
creates exposure windows; loosening post-launch is the safe direction.

**DB subnet group** must span at least 2 AZs (Multi-AZ requirement). For
Aurora, span all 3 AZs in the region for optimal quorum behavior.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


**Security group** inbound rule: scope to the application's security group
on the engine port. NEVER use `0.0.0.0/0` on a DB port.

| Engine | Default port |
|---|---|
| MySQL / Aurora MySQL / MariaDB | 3306 |
| PostgreSQL / Aurora PostgreSQL | 5432 |
| SQL Server | 1433 |
| Oracle | 1521 |
| Aurora PostgreSQL with Babelfish | 1433 (TDS) + 5432 (PostgreSQL) |

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


**Defense-in-depth**: also enable TLS at the engine level via the parameter
group (`rds.force_ssl=1` for PostgreSQL, `require_secure_transport=ON`
for MySQL) so the database rejects plaintext connections even if the SG
is later loosened.

### Step 3 — Encryption (immutable — decide at creation)

`StorageEncrypted` cannot be toggled in place. The ONLY path to encrypt
an unencrypted instance is snapshot → encrypted copy → restore-new →
cutover — a multi-hour migration. Decide at creation.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


For Aurora, encryption is set on the DBCluster:
> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


### Step 4 — Multi-AZ (high availability)

Multi-AZ provides a synchronous standby in a second AZ with automatic
failover (60-120 seconds). The standby is NOT usable for reads —
read-scaling requires separate Read Replicas.

**Non-Aurora:**
> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


**Aurora**: Multi-AZ is implicit — the cluster spans AZs by default. Add
Reader instances in different AZs for read-scaling and to act as failover
targets.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


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

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


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

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


Intervals: 1/5/10/15/30/60 seconds. Default recommendation: **30 seconds**
(balance of granularity vs. CloudWatch Logs cost).

**Performance Insights** — query-level performance analysis. Retention:
7 days (free) or 731 days (long-term, additional cost).

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


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

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


**Option group** — engine-specific features (audit, encryption, extensions).

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


**Apply at creation**: `create-db-instance --db-parameter-group-name <name>-params --option-group-name <name>-options`.

### Step 8 — Aurora-specific features (Serverless v2, Global Database, Backtrack)

For `aurora-*` engines, several features are cluster-scoped.

**Aurora Serverless v2** (recommended over v1 — v1 is being deprecated):
scaling is governed by `ServerlessV2ScalingConfiguration` on the cluster.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


- **MinCapacity**: 0.5-128 ACU (Aurora Capacity Units). Too-low causes
  cold-start latency on the first query after idle. 0.5 is fine for
  dev/test; 2-4 for production.
- **MaxCapacity**: caps cost. Too-high wastes spend; size to peak workload.
- **SecondsUntilAutoPause**: 0 means "never pause" (recommended for
  production). Serverless v2 does not pause to zero like v1 did.

**Aurora Global Database** (cross-region read scaling + DR):

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


Each region's cluster has its OWN KMS CMK. Replication is typically
< 1 second latency. **Failover is one-way** — after promoting a
secondary, you must explicitly re-establish the reverse replication
topology.

**Backtrack** (Aurora MySQL only — fast in-place rewind):

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


Backtrack is NOT a snapshot restore — it rewinds the cluster in place,
typically in minutes. Useful for "oops" DDL/DML without PITR restore.
Does not work with Aurora Serverless v1.

### Step 9 — Deletion protection + tags

**Deletion protection** — blocks `delete-db-instance` / `delete-db-cluster`.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


Note: `delete-db-instance` on a cluster member does NOT delete the cluster.
To fully remove an Aurora DB, you must delete the cluster after removing
all instances (with deletion protection disabled).

**Tags** — cost allocation, automation, ownership.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


### Step 10 — Latest features: Blue/Green, LTES, Aurora DSQL

**Blue/Green deployments** (GA 2024) — create a staging "Green" environment
that replicates from "Blue" (current production). Switch over with
no-downtime. Use for major-version upgrades and risky schema changes.

> Moved verbatim to [`references/provisioning-cli-commands.md`](references/provisioning-cli-commands.md) — load on demand.


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

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## References (load on demand)

- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — every step's create/modify CLI listing (subnet group, SG, encryption, Multi-AZ, backups, monitoring, parameter/option groups, Aurora features, tags, Blue/Green).
- [references/instance-classes-and-parameter-tuning.md](references/instance-classes-and-parameter-tuning.md) — instance class families, Graviton preference, and sizing rules.
- [references/advanced-patterns.md](references/advanced-patterns.md) — reasoning framework, dependency graph, KMS CMK deep dive, recent AWS features.

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
