# Eval: production-multi-az-changestreams

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — multi-AZ cluster, r5.large primary + 2 replicas, change streams 2-day retention, KMS customer-managed key, 7-day backup, storage autoscaling ceiling, compound + single indexes

## Prompt

Create a DocumentDB cluster named orders-docdb in us-east-1.
Engine version 5.0. Instance class db.r5.large with 1 primary and
2 replicas across 3 AZs. Enable change streams with 2-day retention.
KMS key arn:aws:kms:us-east-1:123456789012:key/abc123.
Backup retention 7 days. Storage autoscaling ceiling 10 TB.
Subnet group docdb-subnet-group. Security group sg-docdb-001
(port 27017 from 10.0.0.0/16). Indexes on {status, created_at}
compound and {email} single. Tags: Environment=production,
Application=orders.
