# Eval: missing-vpc-connector

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — VPC connector required for private VPC resources

## Prompt

Deploy an App Runner service named "internal-api-prod" in
us-east-1. Source: ECR image
123456789012.dkr.ecr.us-east-1.amazonaws.com/internal-api:1.0.0
on port 8080. Instance: 2 vCPU / 4096 MB. Access role
AppRunnerECRAccess. Instance role internal-instance. The
application connects to an Aurora PostgreSQL cluster at
db.cluster-xxx.us-east-1.rds.amazonaws.com in private subnets
subnet-priv-a, subnet-priv-b. No VPC connector is configured.
Secret DB_PASSWORD from secretsmanager:internal/db. Auto-scaling
min 2 / max 8. Account: 123456789012.
