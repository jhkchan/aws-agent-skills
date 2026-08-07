# Eval: compliance-audit-log-table

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — audit log with provisioned capacity, no TTL (immutable retention), no Streams

## Prompt

Provision a DynamoDB table for compliance audit logging in us-east-1.
Table name: "audit-events-prod". Workload is steady high-throughput
(10k events/sec sustained, predictable). Use provisioned capacity
with autoscaling. Use SSE-KMS with customer-managed CMK
alias/audit-kms-key. Items must NEVER expire (regulatory retention).
No downstream CDC consumer — Streams not needed. Use a composite
partition key (tenantId + yyyy-mm bucket) with eventId as sort key.
Deletion protection on. Tags: Environment=production,
Workload=audit-log, DataClassification=confidential.
Account ID: 123456789012.
