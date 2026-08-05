# Eval prompt: config-gap-stale

Audit the following RDS DB instance configuration for security and operational
posture. Emit the standard VERDICT block (INSTANCE, VERDICT, REASON, FINDINGS,
REMEDIATION).

DBInstanceIdentifier: db-config-gap-stale
Engine: mysql
DBInstanceStatus: available
PubliclyAccessible: false
StorageEncrypted: true
KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/stale-key
MultiAZ: true
DeletionProtection: true
BackupRetentionPeriod: 0
AutoMinorVersionUpgrade: false
MonitoringInterval: 0
