# Eval: distributed-map-10k-items

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Distributed Map, exactly 10000 items, MaxItems 10000, ItemBatchSize 200, ToleratedFailurePercentage 10, 50 child executions

## Prompt

Create a Distributed Map state named ProcessLargeDataset for
exactly 10000 items in a JSON array at $.records. Each batch of
200 items processed by Lambda function process-batch.
MaxConcurrency 50. ToleratedFailurePercentage 10. MaxItems 10000.
Tags: Environment=production, Scale=large.
