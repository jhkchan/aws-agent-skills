# Eval: ecr-private-with-auth

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ECR private image, medium power, 3 nodes, ECR access key, CloudWatch Logs

## Prompt

Create a Lightsail Container Service named api-service in
us-east-1. Power: medium. Scale: 3 nodes. Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/api-service:v2.1
from ECR private registry. ECR access key: AKIAABCDE12345 with
secret key provided. Container port 8080 mapped to HTTP. Public
endpoint with health check on /health every 5 seconds. Enable
CloudWatch Logs. Tags: Environment=production, Team=backend.
