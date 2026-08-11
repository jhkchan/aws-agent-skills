# Eval: ecr-source-autoscale

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with VPC connector, auto-scaling, observability

## Prompt

Deploy a production App Runner service named "checkout-api-prod" in
us-east-1. Source: ECR image
123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0
on port 8080 with health check GET /healthz. Instance: 2 vCPU /
4096 MB. Access role AppRunnerECRAccess (managed ECR policy).
Instance role checkout-instance with DynamoDB + S3 scoped. Secret
DB_PASSWORD from secretsmanager:checkout/db. Environment vars
LOG_LEVEL=info, ENV=production. VPC connector checkout-vpc
(subnets subnet-priv-a, subnet-priv-b, subnet-priv-c; security
group sg-priv-app). Auto-scaling min 2 / max 10, concurrency 100.
Deployment trigger automatic. Observability: CloudWatch Logs
/aws/apprunner/checkout-api-prod with 30-day retention, X-Ray
tracing enabled. Custom domain checkout.example.com. Account:
123456789012.
