# Eval: missing-secret-access

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — Lambda role has redshift-data:ExecuteStatement but lacks secretsmanager:GetSecretValue on the target secret

## Prompt

Create a Redshift Data API query for cluster my-redshift-cluster,
database dev. Use SecretArn auth with secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx.
Lambda function query-runner executes the query. The Lambda
execution role has redshift-data:ExecuteStatement but does NOT
have secretsmanager:GetSecretValue permission.
