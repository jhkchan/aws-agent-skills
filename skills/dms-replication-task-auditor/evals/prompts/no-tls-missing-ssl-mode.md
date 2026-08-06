# Eval prompt: no-tls-missing-ssl-mode

Audit the following DMS replication task configuration for security exposure.
Emit the standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task ARN: arn:aws:dms:us-east-1:111111111111:task:no-tls-missing-ssl-mode
MigrationType: full-load
Status: running

Source endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: prod-pg.internal.example.com
  Port: 5432
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/src-key-3
  (Note: no SslMode field present on this endpoint)

Target endpoint (S3):
  EngineName: s3
  ServiceAccessRoleArn: arn:aws:iam::111111111111:role/dms-s3-role
  S3Settings:
    BucketName: dms-export-bucket
    ServiceAccessRoleArn: arn:aws:iam::111111111111:role/dms-s3-role

Replication instance:
  ReplicationInstanceClass: dms.r5.large
  MultiAZ: true
  PubliclyAccessible: false
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/inst-key-3

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":true,"LogLevel":"info","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_INFO"}]},"ValidationSettings":{"EnableValidation":true}}
