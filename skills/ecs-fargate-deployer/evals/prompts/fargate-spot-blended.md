# Eval: fargate-spot-blended

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — capacity-provider strategy with base=2 FARGATE

## Prompt

Deploy a stateless ECS Fargate SQS queue consumer service named
"email-worker-prod" in cluster "workers-prod" in us-east-1.
Image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/email-worker:v3.1.
Container port 8080 with health check GET /healthz. Task size
0.5 vCPU / 1024 MB. Desired count 6 with capacity provider
strategy: base=2 on FARGATE, weight 3 on FARGATE, weight 1 on
FARGATE_SPOT. Subnets subnet-priv-a, subnet-priv-b. Security
group sg-email-worker. Execution role email-exec with ECR +
Secrets Manager + logs. Task role email-task with SQS + SES
scoped. Deployment circuit breaker enabled. Logging to
/ecs/email-worker with 14-day retention. Account: 123456789012.
