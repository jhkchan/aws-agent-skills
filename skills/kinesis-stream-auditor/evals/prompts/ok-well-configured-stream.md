# Eval prompt: ok-well-configured-stream

Audit the following Kinesis Data Streams configuration for security, cost,
and operational exposure. Emit the standard VERDICT block (STREAM, VERDICT,
REASON, FINDINGS, REMEDIATION).

Stream name: ok-well-configured-stream
Stream configuration (describe-stream-summary):
  StreamName: ok-well-configured-stream
  StreamStatus: ACTIVE
  StreamMode: PROVISIONED
  OpenShardCount: 4
  RetentionPeriodHours: 24
  EncryptionType: KMS
  KeyId: arn:aws:kms:us-east-1:111111111111:key/mnop-3456-cmk
  EnhancedMonitoring:
    - ShardLevelMetrics: [IncomingBytes, IncomingRecords, OutgoingBytes, OutgoingRecords, IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded, ReadProvisionedThroughputExceeded]
  ConsumerCount: 2
