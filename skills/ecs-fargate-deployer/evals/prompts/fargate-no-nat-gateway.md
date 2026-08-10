# Eval: fargate-no-nat-gateway

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — NAT Gateway or VPC endpoints required

## Prompt

Deploy an ECS Fargate service named "report-worker-prod" in
cluster "workers-prod" in us-east-1. Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/report-worker:v1.5.
The task runs in private subnets subnet-priv-a, subnet-priv-b
(private subnets, no NAT Gateway configured, no VPC endpoints).
The application makes DynamoDB API calls. Task size 1 vCPU /
2048 MB. Desired count 2. Execution role exists. Account:
123456789012.
