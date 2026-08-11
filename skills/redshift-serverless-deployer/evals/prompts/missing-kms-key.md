# Eval: missing-kms-key

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — customer-managed KMS key required for production encryption

## Prompt

Deploy a production Redshift Serverless namespace "analytics-ns-prod"
and workgroup "analytics-wg-prod" in us-east-1. Database dev,
admin user admin via Secrets Manager secret redshift/admin.
Customer-managed KMS encryption required but NO KMS KEY PROVIDED
(the operator forgot to create the CMK and did not supply an
alias or ARN). Subnet group redshift-subnet-group across 3 AZs.
Security group sg-redshift-prod with inbound 5439 from
sg-analytics-app. Base capacity 128 RPU, public access disabled,
enhanced VPC routing enabled. Cross-Region snapshots to us-west-2
planned. Account: 123456789012.
