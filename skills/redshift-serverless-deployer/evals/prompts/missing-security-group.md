# Eval: missing-security-group

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — security group inbound rule required for database access

## Prompt

Deploy a Redshift Serverless namespace "analytics-ns-prod" and
workgroup "analytics-wg-prod" in us-east-1. Database dev, admin
user admin via Secrets Manager secret redshift/admin. Customer-
managed KMS key alias/redshift-prod. Subnet group
redshift-subnet-group across subnet-aaa, subnet-bbb, subnet-ccc.
Security group sg-redshift-prod with NO inbound rule for port
5439 (only outbound 443 to S3). Analytics application in
sg-analytics-app needs JDBC access on port 5439. Base capacity
64 RPU, public access disabled, enhanced VPC routing enabled.
Account: 123456789012.
