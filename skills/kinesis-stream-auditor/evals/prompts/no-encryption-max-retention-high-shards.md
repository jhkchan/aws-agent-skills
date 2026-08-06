# Eval prompt: no-encryption-max-retention-high-shards

Audit the following Kinesis Data Streams configuration for security, cost,
and operational exposure. Emit the standard VERDICT block (STREAM, VERDICT,
REASON, FINDINGS, REMEDIATION).

Stream name: no-encryption-max-retention-high-shards
Stream configuration (describe-stream-summary):
  StreamName: no-encryption-max-retention-high-shards
  StreamStatus: ACTIVE
  StreamMode: PROVISIONED
  OpenShardCount: 50
  RetentionPeriodHours: 8760
  EncryptionType: NONE
  EnhancedMonitoring:
    - ShardLevelMetrics: [IncomingBytes, IncomingRecords, OutgoingBytes, OutgoingRecords, IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded]
  ConsumerCount: 1
