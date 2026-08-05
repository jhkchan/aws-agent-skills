# Eval prompt: no-encryption-none

Audit the following Kinesis Data Streams configuration for security, cost,
and operational exposure. Emit the standard VERDICT block (STREAM, VERDICT,
REASON, FINDINGS, REMEDIATION).

Stream name: no-encryption-none
Stream configuration (describe-stream-summary):
  StreamName: no-encryption-none
  StreamStatus: ACTIVE
  StreamMode: PROVISIONED
  OpenShardCount: 4
  RetentionPeriodHours: 24
  EncryptionType: NONE
  EnhancedMonitoring:
    - ShardLevelMetrics: [IncomingBytes, OutgoingBytes, IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded]
  ConsumerCount: 2
