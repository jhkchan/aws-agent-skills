# Eval prompt: no-deletion-protection-prod

Audit the following RDS DB instance configuration for security and operational
posture. Emit the standard VERDICT block (INSTANCE, VERDICT, REASON, FINDINGS,
REMEDIATION).

DBInstanceIdentifier: db-no-deletion-protection-prod
Engine: mysql
DBInstanceStatus: available
PubliclyAccessible: false
StorageEncrypted: true
KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/prod-key
MultiAZ: true
DeletionProtection: false
BackupRetentionPeriod: 7
AutoMinorVersionUpgrade: true
MonitoringInterval: 60
