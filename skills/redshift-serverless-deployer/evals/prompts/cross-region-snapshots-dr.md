# Eval: cross-region-snapshots-dr

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — scheduled snapshots, cross-Region copy, destination-Region CMK

## Prompt

Deploy a production Redshift Serverless namespace "analytics-ns-prod"
and workgroup "analytics-wg-prod" in us-east-1. Database dev,
admin user admin via Secrets Manager secret redshift/admin.
Customer-managed KMS key alias/redshift-prod. Namespace IAM role
RedshiftNSRole. Subnet group redshift-subnet-group across 3 AZs.
Security group sg-redshift-prod with inbound 5439 from
sg-analytics-app. Base capacity 128 RPU, public access disabled,
enhanced VPC routing enabled, Data API enabled. Usage limits:
daily 500 RPU-hours (log). Snapshots: automated every 8 hours,
7-day retention, cross-Region copy to us-west-2 with
destination-Region KMS key alias/redshift-dr and snapshot copy
grant analytics-copy-grant. Account: 123456789012.
