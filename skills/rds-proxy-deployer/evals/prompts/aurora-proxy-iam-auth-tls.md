# Eval: aurora-proxy-iam-auth-tls

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Aurora PostgreSQL proxy with IAM auth (requires TLS), TLS enforced, Secrets Manager secret format verified, rotation pairing enabled, proxy endpoint noted

## Prompt

Create an RDS Proxy named my-app-proxy for Aurora PostgreSQL
cluster my-aurora-cluster in us-east-1, account 123456789012.
Enable IAM authentication and require TLS. Secrets Manager secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc
(format: username, password, engine, host, port, dbClusterIdentifier).
IAM role arn:aws:iam::123456789012:role/rds-proxy-role. Enable
Secrets Manager rotation every 30 days via Lambda
arn:aws:lambda:us-east-1:123456789012:function:secretsmanager-rds-rotation.
Subnet group my-proxy-subnet-group (subnets in us-east-1a, 1b, 1c).
Proxy security group sg-proxy111. Database security group
sg-database222. Tags: Environment=production.
