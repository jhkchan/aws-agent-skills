# Eval: multi-az-failover-security-groups

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — multi-AZ proxy across 3 AZs, database SG ingress from proxy SG on port 3306, failover handling for Aurora MySQL cluster

## Prompt

Create a multi-AZ RDS Proxy named ha-proxy for Aurora MySQL
cluster my-aurora-mysql in us-east-1, account 123456789012.
The proxy must be highly available across us-east-1a, us-east-1b,
and us-east-1c. Proxy security group sg-proxy-ha. Database
security group sg-db-ha on port 3306. Failover handling is
critical. Secrets Manager secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/mysql-creds.
IAM role arn:aws:iam::123456789012:role/rds-proxy-role. Tags:
Environment=production, HA=true.
