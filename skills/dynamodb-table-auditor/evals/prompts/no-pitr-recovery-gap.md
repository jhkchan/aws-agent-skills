# Eval prompt: no-pitr-recovery-gap

Audit the following DynamoDB table configuration for security and compliance
posture. Emit the standard VERDICT block (TABLE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Table name: no-pitr-recovery-gap
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/no-pitr-recovery-gap
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PAY_PER_REQUEST
  SSEDescription:
    Status: ENABLED
    SSEType: KMS
    KMSMasterKeyArn: arn:aws:kms:us-east-1:111111111111:key/customer-cmk-12345
  GlobalSecondaryIndexes: []
  LocalSecondaryIndexes: []
  DeletionProtectionEnabled: true
  StreamSpecification:
    StreamEnabled: true
    StreamViewType: NEW_AND_OLD_IMAGES
  TableSizeBytes: 536870912
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: DISABLED
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: ENABLED
    AttributeName: expire_at
