# Eval: production-namespace-workgroup

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with namespace, workgroup, usage limits, Data API

## Prompt

Deploy a production Redshift Serverless namespace named
"analytics-ns-prod" and workgroup "analytics-wg-prod" in
us-east-1. Database name dev, admin user admin with Secrets
Manager secret redshift/admin. Customer-managed KMS key
alias/redshift-prod. Namespace IAM role RedshiftNSRole with
S3 GetObject on ingest-bucket and Glue GetTable. Subnet group
redshift-subnet-group spanning subnet-aaa, subnet-bbb,
subnet-ccc across us-east-1a/b/c. Security group sg-redshift-prod
with inbound 5439 from sg-analytics-app. Workgroup base capacity
128 RPU, public access disabled, enhanced VPC routing enabled,
Data API enabled, query editor v2 associated. Usage limits:
daily 500 RPU-hours (log), monthly 12000 RPU-hours
(emit-metric). Log exports: userlog, connectionlog,
useractivitylog. Account: 123456789012.
