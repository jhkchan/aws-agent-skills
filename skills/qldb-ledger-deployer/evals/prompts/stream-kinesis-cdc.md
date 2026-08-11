# Eval: stream-kinesis-cdc

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Kinesis stream configured, IAM role for QLDB to write to Kinesis, stream started with inclusive start time

## Prompt

Create a QLDB ledger named realtime-events in us-east-1 with
streaming to Kinesis for real-time CDC. Permissions mode STANDARD.
Deletion protection. KMS key
arn:aws:kms:us-east-1:123456789012:key/stream456. Kinesis stream
qldb-events-stream. IAM role QLDBStreamRole. Stream start time
2026-08-05T00:00:00Z. Tags: Environment=production, Pipeline=CDC.
