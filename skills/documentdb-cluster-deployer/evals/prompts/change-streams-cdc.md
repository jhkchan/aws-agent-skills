# Eval: change-streams-cdc

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CDC-focused cluster, r5.xlarge, change streams 3-day retention (259200s), KMS encryption, 14-day backup

## Prompt

Create a DocumentDB cluster named events-cdc in us-east-1 for a
change data capture pipeline. Engine 5.0. Instance class
db.r5.xlarge with 1 primary and 1 replica. Change streams with
3-day retention (259200 seconds). KMS encryption with customer
key arn:aws:kms:us-east-1:123456789012:key/def456. Backup 14
days. Subnet group docdb-events-sg. Security group sg-events-001.
Tags: Environment=production, Pipeline=CDC.
