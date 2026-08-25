# Error Handling — Kinesis Stream Auditor

Per-verdict remediation guidance moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Remediation guidance (moved from SKILL.md)

### For NO_ENCRYPTION — EncryptionType: NONE

1. **Enable KMS encryption** immediately. Use a customer-managed CMK for
   compliance-sensitive workloads:
   ```bash
   aws kinesis start-stream-encryption \
     --stream-name <name> \
     --encryption-type KMS \
     --key-id arn:aws:kms:us-east-1:111111111111:key/<cmk-id>
   ```
   Or with the AWS-managed key (minimum viable):
   ```bash
   aws kinesis start-stream-encryption \
     --stream-name <name> \
     --encryption-type KMS \
     --key-id alias/aws/kinesis
   ```
2. **Note:** existing plaintext records are NOT retroactively encrypted. Only
   new records are encrypted. Old records expire from the retention window
   naturally. If immediate encryption of all data is required, create a new
   encrypted stream and migrate producers.
3. **Verify:** `aws kinesis describe-stream-summary --stream-name <name>` and
   confirm `EncryptionType: KMS`.

### For COST_RISK — Extended retention (> 168 hours)

1. **Reduce retention** to the minimum consumers need for replay:
   ```bash
   aws kinesis decrease-stream-retention-period \
     --stream-name <name> \
     --retention-period-hours 24
   ```
2. **Verify** no consumer requires the extended replay window before
   decreasing. Records older than the new retention period are deleted
   immediately and irreversibly.
3. **Calculate savings:** extended retention charges are proportional to
   (retention_hours - 24) x shard_count x average_data_rate. Reducing from
   720h to 24h on a 10-shard stream at 1 MB/s/shard saves ~25 TB of
   extended-retention storage per month.

### For COST_RISK — On-demand at low volume (< 200 MB/day)

1. **Switch to provisioned mode:**
   ```bash
   aws kinesis update-stream-mode \
     --stream-arn arn:aws:kinesis:us-east-1:111111111111:stream/<name> \
     --stream-mode PROVISIONED
   ```
2. **Set shard count** to match peak throughput:
   ```bash
   aws kinesis update-shard-count \
     --stream-name <name> \
     --target-shard-count 1 \
     --scaling-type UNIFORM_SCALING
   ```
3. **Savings:** on-demand per-stream-hour (~$29/month) + per-GB charges
   vs provisioned 1-shard (~$11/month). For < 200 MB/day, provisioned is
   cheaper.

### For COST_RISK — Provisioned approaching shard quota (> 400 shards)

1. **Evaluate partition-key distribution.** Uneven distribution causes hot
   shards, which forces over-provisioning. Fix the partition key strategy
   before reducing shards.
2. **Reduce shard count** if throughput allows:
   ```bash
   aws kinesis update-shard-count \
     --stream-name <name> \
     --target-shard-count 200 \
     --scaling-type UNIFORM_SCALING
   ```
3. **Request a quota increase** if the shard count is justified:
   ```bash
   aws service-quotas request-service-quota-increase \
     --service-code kinesis \
     --quota-code L-7B8615C9 \
     --desired-value 1000
   ```

### For CONFIG_GAP — Missing enhanced-monitoring metrics

1. **Enable essential shard-level metrics:**
   ```bash
   aws kinesis enable-enhanced-monitoring \
     --stream-name <name> \
     --shard-level-metrics IteratorAgeMilliseconds WriteProvisionedThroughputExceeded
   ```
2. **Set a CloudWatch alarm** on iterator age approaching retention:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name kinesis-<name>-iterator-age \
     --namespace AWS/Kinesis \
     --metric-name GetRecords.IteratorAgeMilliseconds \
     --dimensions Name=StreamName,Value=<name> \
     --threshold <RetentionPeriodHours * 3600000 * 0.8> \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 1 \
     --period 300
   ```

### For CONFIG_GAP — No consumers (ConsumerCount: 0)

1. **Register a consumer** or verify a Kinesis Firehose is attached:
   ```bash
   aws kinesis register-stream-consumer \
     --stream-arn arn:aws:kinesis:us-east-1:111111111111:stream/<name> \
     --consumer-name my-consumer
   ```
2. If no consumer is needed yet, set a CloudWatch alarm on
   `GetRecords.IteratorAgeMilliseconds` to alert when data is at risk of
   expiring unread.

### For OK

1. No remediation required.
2. Recommend a CloudWatch alarm on `GetRecords.IteratorAgeMilliseconds`
   approaching the retention threshold (defense-in-depth).
3. For provisioned streams, recommend periodic shard-utilization review to
   catch partition-key hot spots before they cause throttling.

