# Eval: ml-inference-arm64

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ARM64, FireLens sidecar, 4 vCPU/16GB sizing

## Prompt

Deploy a production ECS Fargate ML inference service named
"image-tagger-prod" in cluster "ml-prod" in us-east-1. Image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/image-tagger:v4.0-arm64.
Architecture ARM64 (Graviton). Container port 8500 with health
check GET /healthz (startPeriod 120 for model warmup). Task size
4 vCPU / 16 GB. Desired count 2 across subnet-priv-a,
subnet-priv-b. ALB target group tg-image-tagger (target_type=ip).
Deployment circuit breaker enabled. Execution role tagger-exec.
Task role tagger-task with S3 GetObject on models bucket. Use
FireLens log routing via aws-for-fluent-bit sidecar to CloudWatch
/ecs/image-tagger with 60-day retention. Auto-scaling target
tracking 70% CPU, min 2 max 6. Account: 123456789012.
