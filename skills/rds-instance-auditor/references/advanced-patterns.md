# Advanced patterns — rds-instance-auditor (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Philosophy — three senior-engineer behaviours

Three behaviours separate a senior database engineer from a generalist:

- **`PubliclyAccessible: true` is an internet-exposed database.** This is the
  single highest-impact RDS misconfiguration — a public IP on a database is an
  open invitation to credential stuffing, brute force, and exploitation of any
  auth-layer weakness. Network-layer controls (security groups) reduce but do
  not eliminate the risk; the flag itself is the verdict driver.
- **`StorageEncrypted` is immutable after creation.** Unlike S3 or EFS where
  encryption is a property toggle, an unencrypted RDS instance CANNOT be
  encrypted in place. Remediation is a migration: snapshot → encrypted copy →
  restore-new → endpoint cutover. This is why UNENCRYPTED is a high-severity
  verdict rather than a "toggle and move on" finding.
- **Aurora engines are cluster-scoped, not instance-scoped.** For `aurora-*`
  engines, encryption, deletion protection, and Multi-AZ are properties of the
  DBCluster, not the individual DB instance. Auditing instance-level fields on
  an Aurora instance produces false positives — the cluster block is the source
  of truth.

## Step 0 — Expert knowledge: non-obvious RDS behaviours that change classification

These are the operational gotchas a senior RDS engineer knows from incident
experience — NOT the basic AWS-docs descriptions of what each field does.
Each one changes a verdict if ignored:

- **`modify-db-instance` is last-write-wins per field, per maintenance window.**
  Two modifications to the SAME field queued without `--apply-immediately` do
  not stack — the later value silently overwrites the earlier one. The default
  maintenance window is weekly (e.g. `sun:03:00-sun:04:00`), so an operator
  who queues `--backup-retention-period 1` then `--backup-retention-period 7`
  a few days later sees only `7` applied, not a 1→7 progression. Modifications
  to DIFFERENT fields apply together in the same window. Always surface queued
  values in REMEDIATION so the operator knows which changes will land.

- **Multi-AZ failover recovers the database, not the application.** The
  60-120 second RDS failover covers standby promotion only. JVM clients cache
  DNS for 60 seconds by default (`networkaddress.cache.ttl=60`); many JDBC
  connection pools pin TCP to the old writer's IP until the pool is recycled;
  some HTTP-tier retry policies treat `Connection refused` as fatal rather
  than transient. Without client-side retry/backoff + DNS-cache tuning, a
  Multi-AZ failover still presents as a 5-30 minute outage to the application.
  Treat SINGLE_AZ as an RPO/RTO primitive, not a complete recovery solution —
  note client-side retry requirements in REMEDIATION when flagging SINGLE_AZ
  on production databases.

- **`gp3` IOPS are capped by a storage ratio that silently blocks
  modification.** gp3 includes 3000 IOPS and 125 MB/s throughput at no extra
  cost; above 3000 IOPS you pay per-IOPS-month. But provisioned IOPS cannot
  exceed 500× allocated-GB for MySQL/PostgreSQL (lower ratios for some
  legacy engines — SQL Server ~64:1, Oracle ~250:1). A `modify-db-instance`
  requesting 15000 IOPS on a 20 GB instance fails validation with
  `IopsToStorageRatio` — the operator must either raise storage or drop IOPS.
  When the audit surfaces storage-class or IOPS changes, note the ratio cap so
  the operator does not chase a remediation the API will reject.

- **KMS CMK rotation does NOT re-encrypt existing RDS data.** Enabling
  automatic annual rotation on the backing CMK generates new key material for
  NEW encrypt operations, but existing ciphertext (data files, automated
  backups, manual snapshots) continues to decrypt with the prior key material
  indefinitely. There is no in-place CMK re-encryption path for RDS — rotating
  OFF a compromised CMK requires the same snapshot → re-encrypt → restore-new
  migration as the initial encryption cutover. Operators who enable KMS
  rotation believing it addresses key compromise have a false sense of safety;
  surface this when the instance is encrypted with a CMK the customer
  suspects is compromised.

- **`MultiAZ: true` standby is NOT usable for reads.** The standby is a
  failover target only — it does not accept client connections. This is a
  common misconception: teams enable Multi-AZ expecting read-scaling and are
  surprised when connections to the standby fail. Read-scaling requires
  separate Read Replicas. For SQL Server, Multi-AZ uses Always On / mirroring
  semantics with additional feature constraints.

- **Aurora instances are cluster members, not standalone databases.** For
  `aurora-*` engines, `StorageEncrypted`, `DeletionProtection`, `MultiAZ`, and
  `BackupRetentionPeriod` are properties of the `DBCluster`, not the
  `DBInstance`. `describe-db-instances` returns instance-level echoes of some
  of these, but the cluster block is authoritative. Auditing Aurora at the
  instance level produces false positives on every dimension except public
  accessibility (which IS instance-level even for Aurora — each instance has
  its own `PubliclyAccessible` flag).

- **`EnhancedMonitoring` (`MonitoringInterval > 0`) requires a role and emits
  to CloudWatch Logs.** RDS assumes `MonitoringRoleARN` to emit OS-level
  metrics (CPU steal, swap, file systems) at the configured interval
  (1/5/10/15/30/60 seconds). `0` means off — only engine-level CloudWatch
  metrics exist. Enhanced Monitoring is distinct from Performance Insights
  (query-level) and from RDS Events; this skill audits Enhanced Monitoring
  specifically because it is the gap most often missing on instances that
  later suffer unexplained OS-level incidents.

- **`PendingModifiedValues` is a queue, not the current state.** Always audit
  the top-level CURRENT value; note the pending change via the `[PENDING]`
  annotation in FINDINGS so the operator can decide whether to force-apply or
  wait. See the output-format section for the annotation shape.

- **Read Replicas and Multi-AZ are independent.** A Read Replica can itself
  be Multi-AZ (rare) or single-AZ (common). The replica exists for read
  scaling or cross-region DR; the primary's Multi-AZ posture is the write
  availability gate. Flagging a single-AZ Read Replica as a hard SINGLE_AZ
  finding over-states the risk for read-only workloads.

- **The `--apply-immediately` flag changes blast radius.** For the PUBLIC
  finding, removal of public IP should use `--apply-immediately` (existing
  public-IP connections drop, but the gap closes now). For non-urgent
  dimensions (minor-version upgrade, enhanced monitoring), prefer the
  maintenance window to avoid stacking modifications. Encryption has no
  `--apply-immediately` path at all — it is the snapshot-migration workflow.

- **Cross-Region Read Replicas inherit the source encryption state.** You
  cannot create an encrypted cross-region read replica from an unencrypted
  source — the KMS key is region-scoped, so the replica must reference a CMK in
  the destination region. An unencrypted primary silently blocks the entire
  cross-region DR topology. If a cross-region replica exists for this instance,
  flag its encryption state as a DR-readiness signal, not just a data-protection
  finding.

- **Setting `BackupRetentionPeriod` to 0 is immediately destructive.** It does
  not merely "stop future backups" — it triggers immediate deletion of all
  existing automated backups, transaction logs, and PITR history for the
  instance. The only recovery path after that is a manual snapshot (if one
  exists). When remediating in the other direction (0 → 7), the first automated
  backup is triggered within the next backup window, not instantly.

- **`StorageType: magnetic` is deprecated and cannot skip generations.**
  Instances on `magnetic` (standard HDD) cannot be modified directly to `io1`/
  `io2`/`gp3` — they must transition through `gp2` first. Separately, `gp3`
  (the current default for new instances) provisions IOPS and throughput
  independently of storage capacity, so a `gp3` instance with low allocated
  storage but high IOPS needs is valid and should not be flagged as
  under-provisioned from capacity alone.

## Reference — edge cases

- **Aurora cluster scope.** When `Engine` is `aurora-mysql` or
  `aurora-postgresql`, encryption, deletion protection, Multi-AZ, and backup
  retention are DBCluster properties. `describe-db-instances` returns
  instance-level echoes that may lag the cluster. Always request the
  `DBCluster` block. If only instance metadata is available, emit
  `AURORA_CLUSTER_SCOPE: audit the DBCluster for encryption/deletion/Multi-AZ/
  retention — instance-level echoes are not authoritative for Aurora.` and do
  NOT flag those dimensions from instance fields. `PubliclyAccessible` IS
  instance-level for Aurora and is audited normally.

- **Read Replica SINGLE_AZ downgrade.** A Read Replica
  (`ReadReplicaSourceDBInstanceIdentifier` present) is read-only by design.
  Flag its MultiAZ posture as a note rather than a hard SINGLE_AZ finding —
  the primary's Multi-AZ is the write-availability gate. Promote the note to
  a finding only if the replica is a documented production read endpoint.

- **`PendingModifiedValues` interaction.** If a dimension's pending value
  differs from the current value, audit the CURRENT value and append a note:
  `PENDING: <field> is queued to change to <value> at the next window / on
  --apply-immediately.` This prevents both false alarms (gap already being
  fixed) and silent gaps (operator believes a pending change is already live).

- **Aurora Serverless.** `db.serverless` classes (Aurora Serverless v1) and
  Aurora Serverless v2 scaling are cluster-governed. Multi-AZ semantics
  differ (v1 is single-AZ-capable; v2 supports Multi-AZ). Defer to cluster
  metadata and do not flag SINGLE_AZ on the instance class alone.

- **SQL Server Multi-AZ.** SQL Server Multi-AZ uses Always On Availability
  Groups / database mirroring. Certain features (memory-optimized tables,
  cross-database transactions in some modes) have constraints under
  Multi-AZ. This does not change the SINGLE_AZ verdict but should be noted in
  REMEDIATION so the operator plans the upgrade window.

- **`StorageEncrypted: true` without `KmsKeyId`.** This is normal — RDS uses
  the AWS-managed `aws/rds` CMK. Do NOT flag. If the customer needs key
  control (rotation, policy, CloudTrail data events), that is the
  kms-key-policy-auditor's scope.

- **`DBInstanceStatus: deleting`.** Skip audit — modifications against a
  deleting instance fail with `InvalidDBInstanceState`. Emit OK with a note.

- **`BackupRetentionPeriod` > 0 but < 7 on a regulated workload.** This
  skill treats `0` as the CONFIG_GAP trigger (PITR disabled). A non-zero but
  short retention is a compliance nuance, not a hard config gap — note it in
  FINDINGS as a compliance advisory, do not drive the verdict from it.

## Recent AWS features (2024-2026)

- **Blue/Green deployments GA (2024):** RDS Blue/Green deployments create a staging environment with replicated data for zero-downtime database updates. Auditors should verify that production databases use Blue/Green for major version upgrades — the switch is safer than in-place upgrades.
- **Aurora Serverless v2 scaling improvements (2024-2025):** Enhanced Aurora Serverless v2 with faster scaling and more predictable capacity. Auditors should verify that Serverless v2 `MinCapacity` and `MaxCapacity` settings are appropriate — too-low MinCapacity causes cold-start latency, too-high MaxCapacity wastes cost.
- **IAM database authentication enhancements (2024):** Improved IAM database auth with longer token validity and broader engine support. Auditors should verify that IAM auth is used instead of password auth for application database connections where the engine supports it.
- **RDS Custom enhancements (2024):** RDS Custom for SQL Server and Oracle with more OS-level customization. Auditors should verify that RDS Custom instances have appropriate OS-level patching — AWS manages the database engine but not the OS.
- **Multi-tenant databases (2025):** RDS for Oracle supports multi-tenant container databases (CDB/PDB). Auditors should verify that PDB-level security configurations are equivalent across all tenant PDBs.

