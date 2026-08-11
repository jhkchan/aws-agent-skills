# Eval: buffering-hints-tradeoff

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Parquet format conversion, buffering hints at 64+ MB for larger files (Athena performance), Hive-style prefix for partition pruning

## Prompt

Create a Firehose delivery stream named analytics-parquet in
us-east-1, account 123456789012. Source: Direct PUT. Format
conversion to Parquet using Glue database analytics, table
events. S3 destination bucket analytics-lake with Hive-style
prefix data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/.
Buffering hints should be tuned for Parquet + Athena downstream
(larger files for better query performance). KMS encryption.
Tags: Environment=production.
