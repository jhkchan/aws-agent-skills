# Eval prompt: ok-hardened-full-load-cdc

Audit the following DMS replication task configuration for security exposure.
Emit the standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task ARN: arn:aws:dms:us-east-1:111111111111:task:ok-hardened-full-load-cdc
MigrationType: full-load-and-cdc
Status: running

Source endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: prod-pg.internal.example.com
  Port: 5432
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/src-key-6

Target endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: target-pg.internal.example.com
  Port: 5432
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/tgt-key-6

Replication instance:
  ReplicationInstanceClass: dms.r5.2xlarge
  MultiAZ: true
  PubliclyAccessible: false
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/inst-key-6

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":true,"LogLevel":"info","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_INFO"},{"Id":"COMMON_AGENT","Severity":"LOGGER_SEVERITY_ONLY_INFO"},{"Id":"SOURCE_UNLOAD","Severity":"LOGGER_SEVERITY_ONLY_INFO"},{"Id":"TARGET_LOAD","Severity":"LOGGER_SEVERITY_ONLY_INFO"}]},"ValidationSettings":{"EnableValidation":true,"ValidationMode":"ROW_LEVEL"},"RecoveryTable":{"EnableRecovery":true},"DeletionProtection":true}
