# Eval: manual-deployment-observability

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — manual deployment, ARM64, full observability, custom domain

## Prompt

Deploy a production App Runner service named "ml-tagger-prod" in
us-east-1. Source: ECR image
123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-tagger:3.0-arm64
on port 8500 with health check GET /healthz. Architecture ARM64
(Graviton). Instance: 4 vCPU / 16384 MB. Access role
AppRunnerECRAccess. Instance role tagger-instance with S3
GetObject on models bucket. No VPC connector needed (no private
resources). Auto-scaling min 2 / max 6, concurrency 50.
Deployment trigger MANUAL (AutoDeploymentsEnabled=false).
Observability: CloudWatch Logs /aws/apprunner/ml-tagger-prod
with 90-day retention, X-Ray tracing enabled. Custom domain
tagger.example.com. Account: 123456789012.
