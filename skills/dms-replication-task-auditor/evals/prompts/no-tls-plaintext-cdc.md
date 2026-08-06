# Eval prompt: no-tls-plaintext-cdc

Audit the following DMS replication task configuration for security exposure.
Emit the standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task ARN: arn:aws:dms:us-east-1:111111111111:task:no-tls-plaintext-cdc
MigrationType: cdc
Status: running

Source endpoint (MySQL):
  EngineName: mysql
  ServerName: prod-mysql.internal.example.com
  Port: 3306
  SslMode: none
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/src-key-1

Target endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: target-pg.internal.example.com
  Port: 5432
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/tgt-key-1

Replication instance:
  ReplicationInstanceClass: dms.r5.large
  MultiAZ: true
  PubliclyAccessible: false
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/inst-key-1

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":true,"LogLevel":"info","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_INFO"}]},"ValidationSettings":{"EnableValidation":true,"ValidationMode":"ROW_LEVEL"}}
