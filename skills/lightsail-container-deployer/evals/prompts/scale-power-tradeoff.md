# Eval: scale-power-tradeoff

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — medium power with 2 nodes for redundancy instead of large x 1, ECR image

## Prompt

Create a Lightsail Container Service named worker-service in
us-east-1. I want high availability at moderate cost. Power:
medium. Scale: 2 nodes (for redundancy). Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/worker:v1.0 from
ECR. ECR credentials configured. Container port 3000 mapped to
HTTP. Health check on /health. Environment variables:
WORKER_CONCURRENCY=10. Tags: Environment=production,
Strategy=cost-ha-balance.
