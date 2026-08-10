# Eval: high-throughput-fifo

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — high-throughput FIFO + partial batch responses

## Prompt

Deploy a high-throughput FIFO SQS queue named "bulk-orders.fifo" in
us-east-1. It needs 1500 TPS throughput. Use per-message-group
throughput limit and message-group dedup scope. DLQ
"bulk-orders-dlq.fifo" with maxReceiveCount=10 and 14-day retention.
Lambda consumer "bulk-processor" with partial batch responses
(ReportBatchItemFailures). Visibility timeout 300s. SSE-SQS encryption.
Account: 111111111111.
