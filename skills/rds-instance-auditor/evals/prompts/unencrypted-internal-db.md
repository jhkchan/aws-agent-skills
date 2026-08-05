# Eval prompt: unencrypted-internal-db

Audit the following RDS DB instance configuration for security and operational
posture. Emit the standard VERDICT block (INSTANCE, VERDICT, REASON, FINDINGS,
REMEDIATION).

DBInstanceIdentifier: db-unencrypted-internal-db
Engine: postgres
DBInstanceStatus: available
PubliclyAccessible: false
StorageEncrypted: false
MultiAZ: true
DeletionProtection: true
BackupRetentionPeriod: 7
AutoMinorVersionUpgrade: true
MonitoringInterval: 60
