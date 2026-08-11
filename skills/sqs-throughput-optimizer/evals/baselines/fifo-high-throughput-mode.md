# Baseline (no-skill) response: fifo-high-throughput-mode

This file captures what a generic assistant produces WITHOUT the
sqs-throughput-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, FIFO high-throughput mode citation,
DeduplicationScope/ThroughputLimit configuration, CONFIRM gate).

---

Your FIFO queue is hitting the throughput limit. The default for FIFO
queues is 300 transactions per second, and you're trying to send 500
TX/s. That's why messages are backing up.

You can enable high-throughput mode on your FIFO queue to increase the
limit to 9000 TX/s with batching. Set these attributes:

```
aws sqs set-queue-attributes \
  --queue-url <fifo-url> \
  --attributes DeduplicationScope=MessageGroup,ThroughputLimit=PerMessageGroupId
```

This should allow each MessageGroupId to have its own throughput limit
and dramatically increase your overall throughput. Make sure your
workload doesn't need cross-group deduplication before enabling this.
