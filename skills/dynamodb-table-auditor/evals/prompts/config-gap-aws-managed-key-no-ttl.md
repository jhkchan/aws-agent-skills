# Eval prompt: config-gap-aws-managed-key-no-ttl

Audit the following DynamoDB table configuration for security and compliance
posture. Emit the standard VERDICT block (TABLE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Table name: config-gap-aws-managed-key-no-ttl
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/config-gap-aws-managed-key-no-ttl
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PAY_PER_REQUEST
  SSEDescription:
    Status: ENABLED
    SSEType: KMS
    KMSMasterKeyArn: arn:aws:kms:us-east-1:111111111111:alias/aws/dynamodb
  GlobalSecondaryIndexes: []
  LocalSecondaryIndexes: []
  DeletionProtectionEnabled: false
  StreamSpecification:
    StreamEnabled: true
    StreamViewType: NEW_IMAGE
  TableSizeBytes: 134217728
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: ENABLED
  PointInTimeRecoveryDescription:
    PointInTimeRecoveryStatus: ENABLED
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: DISABLED
