# Eval prompt: config-gap-no-validation-no-kms

Audit the following DMS replication task configuration for security exposure.
Emit the standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task ARN: arn:aws:dms:us-east-1:111111111111:task:config-gap-no-validation-no-kms
MigrationType: full-load-and-cdc
Status: running

Source endpoint (SQL Server):
  EngineName: sqlserver
  ServerName: prod-sqlsrv.internal.example.com
  Port: 1433
  SslMode: verify-full
  (Note: no KmsKeyId on this endpoint)

Target endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: target-pg.internal.example.com
  Port: 5432
  SslMode: verify-full
  (Note: no KmsKeyId on this endpoint)

Replication instance:
  ReplicationInstanceClass: dms.r5.2xlarge
  MultiAZ: true
  PubliclyAccessible: false
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/inst-key-5

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":true,"LogLevel":"info","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_INFO"},{"Id":"COMMON_AGENT","Severity":"LOGGER_SEVERITY_ONLY_INFO"}]},"ValidationSettings":{"EnableValidation":false},"DeletionProtection":false}
