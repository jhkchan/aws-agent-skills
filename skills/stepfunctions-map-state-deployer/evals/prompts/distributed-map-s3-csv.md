# Eval: distributed-map-s3-csv

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Distributed Map, S3 CSV input via ItemReader/ReaderConfig, ItemBatchSize 100, MaxConcurrency 50, ToleratedFailurePercentage 5, s3:GetObject IAM permission

## Prompt

Create a Step Functions Distributed Map state named ProcessRecords
that reads a CSV file from s3://my-data-bucket/datasets/records.csv
(first row is headers). Process in batches of 100 items with
MaxConcurrency 50. Allow up to 5% batch failures. The Lambda
function process-row handles each row. State machine role needs
S3 read access. Max 10000 items. Tags: Environment=production.
