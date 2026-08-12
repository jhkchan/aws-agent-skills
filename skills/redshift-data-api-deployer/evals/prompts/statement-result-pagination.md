# Eval: statement-result-pagination

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — GetStatementResult pagination via NextToken, UNLOAD to S3 to bypass 100MB payload limit, 500K rows

## Prompt

Create a Data API configuration for querying the customers table
on cluster my-redshift-cluster, database dev. Use SecretArn auth
with secret arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx.
Query: SELECT * FROM customers WHERE region = 'APAC' — expected
~500K rows. Need pagination via NextToken. Results written to
S3 via UNLOAD to avoid GetStatementResult payload limit.
Tags: Environment=production, Workflow=customer-export.
