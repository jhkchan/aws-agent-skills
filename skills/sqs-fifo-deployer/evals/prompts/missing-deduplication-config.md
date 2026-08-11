# Eval: missing-deduplication-config

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — ContentBasedDeduplication=false and no explicit dedup ID strategy; FIFO requires dedup

## Prompt

Create an SQS FIFO queue named events.fifo in us-east-1.
ContentBasedDeduplication is false. Producers will send
messages without MessageDeduplicationId. Visibility timeout
30 seconds. Tags: Environment=development.
