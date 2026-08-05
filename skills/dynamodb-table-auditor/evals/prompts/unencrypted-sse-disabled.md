# Eval prompt: unencrypted-sse-disabled

Audit the following DynamoDB table configuration for security and compliance
posture. Emit the standard VERDICT block (TABLE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Table name: unencrypted-sse-disabled
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/unencrypted-sse-disabled
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PAY_PER_REQUEST
  SSEDescription:
    Status: DISABLED
    SSEType: AES256
  GlobalSecondaryIndexes: []
  LocalSecondaryIndexes: []
  DeletionProtectionEnabled: true
  StreamSpecification:
    StreamEnabled: true
    StreamViewType: NEW_AND_OLD_IMAGES
  TableSizeBytes: 1073741824
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: ENABLED
  PointInTimeRecoveryDescription:
    PointInTimeRecoveryStatus: ENABLED
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: ENABLED
    AttributeName: expire_at
