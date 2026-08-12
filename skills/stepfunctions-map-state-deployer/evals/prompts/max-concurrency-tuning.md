# Eval: max-concurrency-tuning

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Distributed Map, MaxConcurrency 1000 (Distributed max), ItemBatchSize 500, ToleratedFailureCount 100, child execution quota verified

## Prompt

Create a Distributed Map state named HighThroughputProcess for
processing 8000 items from a JSON array. Need maximum throughput.
MaxConcurrency 1000. ItemBatchSize 500. Lambda function
batch-handler handles each batch. ToleratedFailureCount 100.
Account has 100000 concurrent execution quota. Tags:
Environment=production, Profile=high-throughput.
