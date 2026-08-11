# Eval: cost-controls-usage-limits

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — usage limits (daily + monthly), cost controls

## Prompt

Deploy a production Redshift Serverless namespace "bi-ns-prod"
and workgroup "bi-wg-prod" in us-east-1. Database reporting,
admin user admin via Secrets Manager secret redshift/bi-admin.
Customer-managed KMS key alias/redshift-bi. Namespace IAM role
RedshiftBIRole with S3 GetObject on bi-ingest-bucket. Subnet
group bi-subnet-group across 3 AZs. Security group sg-redshift-bi
with inbound 5439 from sg-bi-tool. Base capacity 64 RPU, public
access disabled, enhanced VPC routing enabled, Data API enabled.
Usage limits: daily 200 RPU-hours (log), monthly 8000 RPU-hours
(emit-metric). Log exports: userlog, connectionlog. No
cross-Region snapshots needed. Account: 123456789012.
