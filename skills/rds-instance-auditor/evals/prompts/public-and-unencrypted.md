# Eval prompt: public-and-unencrypted

Audit the following RDS DB instance configuration for security and operational
posture. Emit the standard VERDICT block (INSTANCE, VERDICT, REASON, FINDINGS,
REMEDIATION).

DBInstanceIdentifier: db-public-and-unencrypted
Engine: mysql
DBInstanceStatus: available
PubliclyAccessible: true
StorageEncrypted: false
MultiAZ: true
DeletionProtection: false
BackupRetentionPeriod: 7
AutoMinorVersionUpgrade: true
MonitoringInterval: 60
