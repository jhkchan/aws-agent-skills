# Eval prompt: single-az-dev

Audit the following RDS DB instance configuration for security and operational
posture. Emit the standard VERDICT block (INSTANCE, VERDICT, REASON, FINDINGS,
REMEDIATION).

DBInstanceIdentifier: db-single-az-dev
Engine: postgres
DBInstanceStatus: available
PubliclyAccessible: false
StorageEncrypted: true
KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/dev-key
MultiAZ: false
DeletionProtection: true
BackupRetentionPeriod: 7
AutoMinorVersionUpgrade: true
MonitoringInterval: 60
