# Eval: invalid-access-role

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — access role required for ECR source

## Prompt

Deploy an App Runner service named "report-api-prod" in us-east-1.
Source: ECR image
123456789012.dkr.ecr.us-east-1.amazonaws.com/report-api:1.2.0 on
port 8080. Instance: 1 vCPU / 2048 MB. Access role: NONE PROVIDED
(the operator forgot to create an ECR access role). Instance role
report-instance with DynamoDB scoped. Auto-scaling min 1 / max 4.
No VPC connector. Account: 123456789012.
