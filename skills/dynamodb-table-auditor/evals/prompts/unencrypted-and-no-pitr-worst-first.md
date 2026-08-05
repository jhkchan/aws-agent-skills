# Eval prompt: unencrypted-and-no-pitr-worst-first

Audit the following DynamoDB table configuration for security and compliance
posture. Emit the standard VERDICT block (TABLE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Table name: unencrypted-and-no-pitr-worst-first
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/unencrypted-and-no-pitr-worst-first
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PAY_PER_REQUEST
  SSEDescription:
    Status: DISABLED
    SSEType: AES256
  GlobalSecondaryIndexes: []
  LocalSecondaryIndexes: []
  DeletionProtectionEnabled: false
  StreamSpecification:
    StreamEnabled: false
  TableSizeBytes: 268435456
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: DISABLED
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: DISABLED
