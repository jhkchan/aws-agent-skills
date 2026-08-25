# Error Handling — kinesis-stream-deployer

Error-handling deep dives moved verbatim from SKILL.md.

### Stream stuck in CREATING
- Large shard counts take longer. Wait 1-2 minutes (small) to several
  minutes (hundreds of shards). Use `wait stream-exists`.

### WriteProvisionedThroughputExceeded (provisioned)
- Shard count undersized. Scale up via `update-shard-count` (double the
  count), or switch to on-demand. Verify producer uses `PutRecords`
  (batch) not `PutRecord` (single).

### Consumer access denied
- Verify consumer IAM has `GetRecords` AND `GetShardIterator` AND
  `DescribeStream` on the stream ARN. If SSE-KMS with CMK, verify
  `kms:Decrypt` on the key ARN.

### Enhanced fan-out not receiving data
- Verify consumer is registered (`list-stream-consumers`). Verify
  application uses SubscribeToShard (not GetRecords). Verify IAM has
  `kinesis:SubscribeToShard` on stream AND consumer ARN.

### SSE-KMS enable fails (access denied)
- KMS key policy does NOT permit the Kinesis service principal. Add a
  statement allowing `kinesis.amazonaws.com` to call
  `kms:GenerateDataKey` and `kms:Decrypt`.

