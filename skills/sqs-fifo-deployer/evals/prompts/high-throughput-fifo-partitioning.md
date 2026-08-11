# Eval: high-throughput-fifo-partitioning

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — high-throughput FIFO, DeduplicationScope=messageGroup, ThroughputLimit=messagesPerGroupId, explicit dedup IDs

## Prompt

Create a high-throughput SQS FIFO queue named
high-throughput-events.fifo in us-east-1.
DeduplicationScope=messageGroup,
ThroughputLimit=messagesPerGroupId. Per-entity message group
IDs (event ID) for parallel processing. Explicit
MessageDeduplicationId from event ID. Visibility timeout 60
seconds. No DLQ needed. Tags: Environment=production,
Application=event-processor.
