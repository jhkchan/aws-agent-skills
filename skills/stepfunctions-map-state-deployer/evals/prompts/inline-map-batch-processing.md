# Eval: inline-map-batch-processing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Inline Map, ItemProcessor Mode INLINE, ItemsPath $.items, MaxConcurrency 40 (Inline max), no ItemBatchSize (not supported on Inline)

## Prompt

Create a Step Functions Inline Map state named ProcessItems that
iterates over $.items array (max 5000 items). Each item calls
Lambda function process-item. MaxConcurrency 40. Use ItemProcessor
with Mode INLINE. ItemsPath: $.items. Tags: Environment=staging.
