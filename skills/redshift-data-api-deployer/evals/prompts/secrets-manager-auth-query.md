# Eval: secrets-manager-auth-query

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SecretArn auth, redshift-data + secretsmanager:GetSecretValue IAM permissions, Lambda poll pattern, result persistence to DynamoDB

## Prompt

Create a Redshift Data API configuration for querying the sales
table on cluster my-redshift-cluster, database dev. Use Secrets
Manager secret arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx
for authentication. Lambda function sales-query will execute:
SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'.
Poll every 2 seconds. Persist results to DynamoDB immediately.
Tags: Environment=production, Workflow=sales-counter.
