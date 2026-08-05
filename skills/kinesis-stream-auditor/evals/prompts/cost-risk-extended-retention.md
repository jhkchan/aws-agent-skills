# Eval prompt: cost-risk-extended-retention

Audit the following Kinesis Data Streams configuration for security, cost,
and operational exposure. Emit the standard VERDICT block (STREAM, VERDICT,
REASON, FINDINGS, REMEDIATION).

Stream name: cost-risk-extended-retention
Stream configuration (describe-stream-summary):
  StreamName: cost-risk-extended-retention
  StreamStatus: ACTIVE
  StreamMode: PROVISIONED
  OpenShardCount: 8
  RetentionPeriodHours: 720
  EncryptionType: KMS
  KeyId: arn:aws:kms:us-east-1:111111111111:key/abcd-1234-cmk
  EnhancedMonitoring:
    - ShardLevelMetrics: [IncomingBytes, OutgoingBytes, IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded]
  ConsumerCount: 3
