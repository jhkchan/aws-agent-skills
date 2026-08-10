# Eval: dev-t3-single-node

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — small dev domain with t3.small.search, 1 node, public access acceptable for dev, AWS-managed KMS

## Prompt

Provision a small dev OpenSearch domain named "dev-search" in
us-east-1 for testing search features. Use t3.small.search with 1 node
(no Multi-AZ needed for dev). EBS gp3 10GB. Public access is fine for
dev (with strong FGAC — IAM master user
arn:aws:iam::123456789012:role/dev-search-master). AWS-managed KMS for
encryption at rest. Engine OpenSearch 2.11. Tags: Environment=dev,
Workload=test. Account: 123456789012.
