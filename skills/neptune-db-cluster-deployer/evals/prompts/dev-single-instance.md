# Eval: dev-single-instance

**Difficulty:** easy
**Branch:** READY_TO_DEPLOY — dev cluster with single writer; explicit 'NO failover' notation; AWS-managed KMS; neptune_enforce_ssl=1 hygiene

## Prompt

Provision a dev Neptune DB cluster named "dev-graph" in us-east-1.
Just a single writer instance for functional testing — no Multi-AZ,
no failover needed. Use db.r6g.large. Engine version 1.3.2.0. Enable
neptune_enforce_ssl=1 for good hygiene. AWS-managed KMS key is fine
(no customer CMK). Subnet group dev-neptune-subnet in one AZ is OK
for dev. Security group sg-dev-neptune inbound 8182 from sg-dev-app.
Tags: Environment=dev, Workload=graph. Account ID: 123456789012.
