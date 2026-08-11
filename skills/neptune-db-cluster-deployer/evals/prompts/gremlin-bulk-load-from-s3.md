# Eval: gremlin-bulk-load-from-s3

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Multi-AZ cluster with bulk load source cited (same-region S3 bucket, IAM role NeptuneLoadRole); loader prerequisites verified

## Prompt

Provision a Neptune DB cluster named "analytics-graph" in us-east-1
for a Gremlin property-graph workload. 1 writer + 1 reader for
Multi-AZ, db.r6g.4xlarge. Engine version 1.3.2.0. Customer CMK
alias/graph-kms. neptune_enforce_ssl=1, IAM database auth. Snapshots
7 days. Deletion protection enabled. We need to load initial data
from s3://graph-data-bucket/v1/ (same region us-east-1) using IAM
role NeptuneLoadRole. Subnet group graph-subnet spans 2 AZs.
Security group sg-graph inbound 8182 from sg-graph-app. Tags:
Environment=production, Workload=graph-bulk-load. Account ID:
123456789012.
