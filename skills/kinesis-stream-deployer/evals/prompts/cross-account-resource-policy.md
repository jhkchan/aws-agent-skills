# Eval: cross-account-resource-policy

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — on-demand stream with cross-account read access via stream ARN resource policy for account 999999999999

## Prompt

Create a Kinesis Data Stream named shared-events in us-east-1.
On-demand mode. Account 123456789012 owns the stream. A consumer
application in account 999999999999 needs to read records (GetRecords
and GetShardIterator). Retention 24 hours. No enhanced fan-out.
Use a stream resource policy for cross-account access. Producer is
in account 123456789012 role stream-producer-role. Tags:
Environment=production, SharedWith=analytics-org.
