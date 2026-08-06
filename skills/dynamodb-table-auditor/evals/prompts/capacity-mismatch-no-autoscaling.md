# Eval prompt: capacity-mismatch-no-autoscaling

Audit the following DynamoDB table configuration for security and compliance
posture. Emit the standard VERDICT block (TABLE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Table name: capacity-mismatch-no-autoscaling
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/capacity-mismatch-no-autoscaling
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PROVISIONED
    LastUpdateToPayPerRequestDateTime: null
  ProvisionedThroughput:
    NumberOfDecreasesToday: 0
    ReadCapacityUnits: 100
    WriteCapacityUnits: 50
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
  TableSizeBytes: 2147483648
Autoscaling policies (application-autoscaling describe-scaling-policies):
  ScalingPolicies: []
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: ENABLED
  PointInTimeRecoveryDescription:
    PointInTimeRecoveryStatus: ENABLED
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: ENABLED
    AttributeName: expire_at
