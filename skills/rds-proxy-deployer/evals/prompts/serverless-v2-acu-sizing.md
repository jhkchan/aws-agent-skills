# Eval: serverless-v2-acu-sizing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Aurora Serverless v2 proxy, MaxConnectionsPercent set on target group (not proxy), ACU-based sizing noted, target is the cluster

## Prompt

Create an RDS Proxy named serverless-proxy for Aurora Serverless
v2 cluster my-serverless-v2-cluster (8 ACU minimum) in us-east-1,
account 123456789012. Engine POSTGRESQL. Max connections percent
75 based on ACU sizing. Max idle connections percent 50. Secrets
Manager secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/serverless-creds.
IAM role arn:aws:iam::123456789012:role/rds-proxy-role. Subnet
group spanning us-east-1a, us-east-1b. Tags: Environment=production.
