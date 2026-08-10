# Eval: wrong-target-type-instance

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — Fargate requires target_type=ip

## Prompt

Deploy an ECS Fargate service named "internal-api-prod" in
cluster "apps-prod" in us-east-1. Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/internal-api:v2.0.
Container port 3000. Task size 0.25 vCPU / 512 MB. Desired
count: 2. ALB target group tg-internal-api with target_type=
instance. Subnets subnet-priv-a, subnet-priv-b. Security group
sg-internal-api. Account: 123456789012.
