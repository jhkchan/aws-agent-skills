# Eval prompt: no-logging-cdc-silent

Audit the following DMS replication task configuration for security exposure.
Emit the standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task ARN: arn:aws:dms:us-east-1:111111111111:task:no-logging-cdc-silent
MigrationType: full-load-and-cdc
Status: running

Source endpoint (Oracle):
  EngineName: oracle
  ServerName: prod-oracle.internal.example.com
  Port: 1521
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/src-key-2

Target endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: target-pg.internal.example.com
  Port: 5432
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/tgt-key-2

Replication instance:
  ReplicationInstanceClass: dms.r5.large
  MultiAZ: true
  PubliclyAccessible: false
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/inst-key-2

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":false,"LogLevel":"info"},"ValidationSettings":{"EnableValidation":true,"ValidationMode":"ROW_LEVEL"}}
