# Eval prompt: ok-clean-production

Audit the following DynamoDB table configuration for security and compliance
posture. Emit the standard VERDICT block (TABLE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Table name: ok-clean-production
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/ok-clean-production
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PAY_PER_REQUEST
  SSEDescription:
    Status: ENABLED
    SSEType: KMS
    KMSMasterKeyArn: arn:aws:kms:us-east-1:111111111111:key/prod-cmk-67890
  GlobalSecondaryIndexes:
    - IndexName: gsi-status-index
      IndexStatus: ACTIVE
      KeySchema:
        - AttributeName: status
          KeyType: HASH
      Projection:
        ProjectionType: ALL
    - IndexName: gsi-created-at-index
      IndexStatus: ACTIVE
      KeySchema:
        - AttributeName: created_at
          KeyType: HASH
      Projection:
        ProjectionType: ALL
  LocalSecondaryIndexes: []
  DeletionProtectionEnabled: true
  StreamSpecification:
    StreamEnabled: true
    StreamViewType: NEW_AND_OLD_IMAGES
  TableSizeBytes: 5368709120
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: ENABLED
  PointInTimeRecoveryDescription:
    PointInTimeRecoveryStatus: ENABLED
    EarliestRestorableDateTime: "2026-07-01T00:00:00Z"
    LatestRestorableDateTime: "2026-08-05T12:00:00Z"
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: ENABLED
    AttributeName: expire_at
