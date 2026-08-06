# Eval prompt: cost-risk-on-demand-low-volume

Audit the following Kinesis Data Streams configuration for security, cost,
and operational exposure. Emit the standard VERDICT block (STREAM, VERDICT,
REASON, FINDINGS, REMEDIATION).

Stream name: cost-risk-on-demand-low-volume
Stream configuration (describe-stream-summary):
  StreamName: cost-risk-on-demand-low-volume
  StreamStatus: ACTIVE
  StreamMode: ON_DEMAND
  OpenShardCount: 4
  RetentionPeriodHours: 24
  EncryptionType: KMS
  KeyId: arn:aws:kms:us-east-1:111111111111:key/efgh-5678-cmk
  EnhancedMonitoring:
    - ShardLevelMetrics: [IncomingBytes, OutgoingBytes, IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded]
  ConsumerCount: 1

Estimated daily ingest volume: 80 MB/day
