# Eval: missing-secrets-manager-secret

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — Secrets Manager secret does not exist; proxy cannot authenticate to the database

## Prompt

Create an RDS Proxy named my-broken-proxy for Aurora PostgreSQL
cluster my-aurora-cluster in us-east-1, account 123456789012.
Reference Secrets Manager secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/nonexistent-secret
which does NOT exist in Secrets Manager. IAM role
arn:aws:iam::123456789012:role/rds-proxy-role.
