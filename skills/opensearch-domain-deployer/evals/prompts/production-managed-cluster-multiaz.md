# Eval: production-managed-cluster-multiaz

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, managed cluster + Multi-AZ (3-zone) + customer CMK + VPC + FGAC + dedicated masters

## Prompt

Provision a production OpenSearch Service domain named "prod-search" in
us-east-1. Workload is a search application with ~500 GB of indices,
latency-sensitive (p99 < 100ms). Use managed cluster with 6 data nodes
(r6g.2xlarge.search) across 3 AZs with 3 dedicated master nodes
(c6g.large.search). EBS gp3 100GB per node. Customer-managed CMK
alias/prod-opensearch-kms for encryption at rest. VPC-only access —
subnets subnet-0aaa/0bbb/0ccc, security group sg-search123 inbound 443
from sg-app456. FGAC with IAM master user (role
arn:aws:iam::123456789012:role/opensearch-master). Automated snapshots
14 day retention. Engine OpenSearch 2.11. Tags: Environment=production,
Workload=search. Account ID: 123456789012.
