# Eval prompt: hardened-multi-az-prod

Audit the following RDS DB instance configuration for security and operational
posture. Emit the standard VERDICT block (INSTANCE, VERDICT, REASON, FINDINGS,
REMEDIATION).

DBInstanceIdentifier: db-hardened-multi-az-prod
Engine: postgres
DBInstanceStatus: available
PubliclyAccessible: false
StorageEncrypted: true
KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/hardened-key
MultiAZ: true
DeletionProtection: true
BackupRetentionPeriod: 7
AutoMinorVersionUpgrade: true
MonitoringInterval: 60
