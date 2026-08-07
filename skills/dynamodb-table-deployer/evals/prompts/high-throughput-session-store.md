# Eval: high-throughput-session-store

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, on-demand + customer CMK + PITR + TTL + Streams

## Prompt

Provision a production DynamoDB table named "prod-sessions" in
us-east-1 for a high-throughput session store. Session IDs are UUID v4.
We need a GSI to look up sessions by userId (most sessions have one,
some anonymous sessions do not). Use SSE-KMS with customer-managed CMK
alias/prod-dynamodb-key. Sessions expire after 24 hours via TTL on
the "expiresAt" attribute. Enable DynamoDB Streams with
NEW_AND_OLD_IMAGES — a downstream Lambda publishes session-change
events. Traffic is bursty and unpredictable. Tags: Environment=
production, Workload=session-store. Account ID: 123456789012.
