# Eval: public-api-alb-autoscale

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with ALB, circuit breaker, auto-scaling

## Prompt

Deploy a production ECS Fargate service named "payments-api-prod" in
cluster "payments-prod" in us-east-1. Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3.
Container port 8080 with health check GET /healthz. Task size:
0.5 vCPU / 1024 MB. Desired count: 3 across subnets subnet-aaa,
subnet-bbb in different AZs with security group sg-payments-api.
ALB target group tg-payments-api (target_type=ip). Deployment
circuit breaker enabled with rollback. Minimum healthy percent
100%, maximum 200%. Execution role payments-exec with ECR +
Secrets Manager + CloudWatch Logs permissions. Task role
payments-task with DynamoDB + S3 scoped. Secret DB_PASSWORD from
secretsmanager:payments/db. Logging to CloudWatch
/ecs/payments-api with 30-day retention. Auto-scaling target
tracking 60% CPU, min 3 max 12. Account: 123456789012.
