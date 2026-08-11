# Eval: missing-subnet-group-multi-az

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — all subnets in same AZ (us-east-1a); multi-AZ proxy requires subnets in at least 2 AZs

## Prompt

Create a highly available RDS Proxy named ha-proxy-broken for
Aurora PostgreSQL cluster my-aurora-cluster in us-east-1, account
123456789012. The proxy must be multi-AZ. However, all provided
subnets (subnet-aaa, subnet-bbb) are in the same AZ
us-east-1a. Secrets Manager secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc.
IAM role arn:aws:iam::123456789012:role/rds-proxy-role.
