# Eval: dedicated-master-large-cluster

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — large managed cluster with 12 data nodes, 3 dedicated masters, UltraWarm, cold storage, manual snapshots to S3

## Prompt

Provision a large production OpenSearch domain named "prod-logs" in
us-east-1 for log analytics. ~5 TB of hot logs, ~20 TB of warm logs
(last 90 days), ~50 TB of cold logs (1 year retention). Use managed
cluster with 12 data nodes (r6g.4xlarge.search) Multi-AZ across 3 AZs.
3 dedicated master nodes (c6g.2xlarge.search). UltraWarm 6 nodes
(ultrawarm1.medium.search). Cold storage enabled. Customer CMK
alias/logs-kms. VPC-only — subnets subnet-0aaa/0bbb/0ccc, SG
sg-logs-search inbound 443 from sg-fluent-bit. FGAC with IAM master
user role arn:aws:iam::123456789012:role/logs-master. Manual snapshots
to s3://logs-snapshots-prod via role
arn:aws:iam::123456789012:role/logs-snapshot. Tags:
Environment=production, Workload=log-analytics. Account ID:
123456789012.
