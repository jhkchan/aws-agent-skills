---
description: Audit an RDS DB instance for public accessibility, encryption-at-rest, deletion protection, Multi-AZ, automated backups, minor-version upgrade, and Enhanced Monitoring — emits VERDICT per instance.
nl_triggers:
  - "audit this RDS instance"
  - "check RDS encryption"
  - "is my database public"
  - "RDS deletion protection"
  - "are automated backups on"
  - "Multi-AZ check"
  - "minor version upgrade"
  - "Enhanced Monitoring off"
  - "harden RDS instance"
  - "PubliclyAccessible true"
  - "BackupRetentionPeriod zero"
  - "RDS config gap"
  - "StorageEncrypted false"
  - "review database configuration"
  - "RDS security audit"
routes_to: rds-instance-auditor
---

# /aws:audit-rds-instance

Activate the `rds-instance-auditor` skill and audit one or more RDS DB
instances for security exposure and configuration gaps.

## What it does

Reads an RDS DB instance configuration (describe-db-instances metadata,
optionally paired with the DBCluster block for Aurora engines) and applies
the ordered classification logic:

1. Public accessibility — `PubliclyAccessible: true` is PUBLIC (internet-
   exposed database; the highest-impact RDS misconfiguration).
2. Encryption-at-rest — `StorageEncrypted: false` is UNENCRYPTED (immutable
   post-creation; remediation is a snapshot migration, not a toggle).
3. Deletion protection — `DeletionProtection: false` is
   NO_DELETION_PROTECTION (single API call can destroy the instance).
4. Multi-AZ — `MultiAZ: false` on a primary non-Aurora instance is SINGLE_AZ
   (no standby; AZ failure causes outage). Read Replicas are downgraded.
5. Automated backups — `BackupRetentionPeriod: 0` disables PITR (CONFIG_GAP).
6. Minor-version upgrade — `AutoMinorVersionUpgrade: false` is CONFIG_GAP.
7. Enhanced Monitoring — `MonitoringInterval: 0` is CONFIG_GAP (no OS-level
   metrics).
8. Aggregation — worst finding wins (PUBLIC > UNENCRYPTED >
   NO_DELETION_PROTECTION > SINGLE_AZ > CONFIG_GAP > OK).

Aurora engines are deferred to the DBCluster block for encryption, deletion
protection, Multi-AZ, and backup retention — those are cluster-level
properties. PubliclyAccessible is still audited at the instance level.

Emits a deterministic VERDICT per instance:

```text
INSTANCE: <db-instance-identifier>
VERDICT: PUBLIC | UNENCRYPTED | NO_DELETION_PROTECTION | SINGLE_AZ | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [PUBLIC] <finding description (Step 1)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an RDS DB instance configuration and ask any of:

- "audit this RDS instance"
- "is my database public?"
- "is encryption enabled on this RDS instance?"
- "is deletion protection on?"
- "are automated backups configured?"
- "is Multi-AZ enabled?"
- "is Enhanced Monitoring on?"

A bare DB instance identifier + any audit verb ("audit this database",
"check RDS config") also routes here via the orchestrator.

## Inputs

- DB instance metadata: DBInstanceIdentifier, Engine, DBInstanceStatus,
  PubliclyAccessible, StorageEncrypted, KmsKeyId, MultiAZ, DeletionProtection,
  BackupRetentionPeriod, AutoMinorVersionUpgrade, MonitoringInterval,
  ReadReplicaSourceDBInstanceIdentifier, PendingModifiedValues.
- For Aurora engines: provide the DBCluster block (StorageEncrypted,
  DeletionProtection, MultiAZ, BackupRetentionPeriod are cluster-level).
- For live-account audits: the skill references describe-db-instances and
  describe-db-clusters.

## Outputs

- One VERDICT block per instance (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding verdict tag and step citation.
- Specific remediation: remove public IP, plan encryption migration, enable
  deletion protection, enable Multi-AZ, set backup retention, enable minor-
  version upgrade, enable Enhanced Monitoring.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for RDS database security and availability).
- `/aws:audit-kms-key-policy` for auditing the KMS key policy when the
  instance uses a customer-managed KMS key for encryption-at-rest.
