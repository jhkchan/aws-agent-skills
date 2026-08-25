# Advanced patterns — rds-instance-deployer (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Reasoning framework — why provisioning order matters (constraints 1-7)

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

## KMS CMK choice, key policy, cross-region replicas, rotation (moved from Step 3)

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

