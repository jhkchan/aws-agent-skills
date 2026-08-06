# Eval prompt: config-gap-no-enhanced-monitoring

Audit the following Kinesis Data Streams configuration for security, cost,
and operational exposure. Emit the standard VERDICT block (STREAM, VERDICT,
REASON, FINDINGS, REMEDIATION).

Stream name: config-gap-no-enhanced-monitoring
Stream configuration (describe-stream-summary):
  StreamName: config-gap-no-enhanced-monitoring
  StreamStatus: ACTIVE
  StreamMode: PROVISIONED
  OpenShardCount: 3
  RetentionPeriodHours: 24
  EncryptionType: KMS
  KeyId: arn:aws:kms:us-east-1:111111111111:key/ijkl-9012-cmk
  EnhancedMonitoring:
    - ShardLevelMetrics: [IncomingBytes, OutgoingBytes]
  ConsumerCount: 1
