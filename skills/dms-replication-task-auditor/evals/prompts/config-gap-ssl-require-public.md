# Eval prompt: config-gap-ssl-require-public

Audit the following DMS replication task configuration for security exposure.
Emit the standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task ARN: arn:aws:dms:us-east-1:111111111111:task:config-gap-ssl-require-public
MigrationType: cdc
Status: running

Source endpoint (MySQL):
  EngineName: mysql
  ServerName: prod-mysql.internal.example.com
  Port: 3306
  SslMode: require
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/src-key-4

Target endpoint (MySQL):
  EngineName: mysql
  ServerName: replica-mysql.internal.example.com
  Port: 3306
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/tgt-key-4

Replication instance:
  ReplicationInstanceClass: dms.r5.large
  MultiAZ: false
  PubliclyAccessible: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/inst-key-4

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":true,"LogLevel":"warning","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_WARNING"}]},"ValidationSettings":{"EnableValidation":true,"ValidationMode":"ROW_LEVEL"}}
