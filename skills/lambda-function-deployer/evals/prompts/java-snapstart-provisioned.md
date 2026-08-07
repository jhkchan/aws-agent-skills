# Eval: java-snapstart-provisioned

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SnapStart + provisioned concurrency on alias

## Prompt

Deploy a production Java Lambda function named
"enterprise-api-prod" in us-east-1. Runtime: java21. Handler:
com.example.ApiHandler::handleRequest. It is a Spring Boot API
behind API Gateway with strict latency requirements (P99 < 200ms).
Enable SnapStart to reduce cold starts. Provisioned concurrency:
20 on the "prod" alias. Memory: 2048 MB, Timeout: 30s. X-Ray
tracing active. On-failure destination: enterprise-api-dlq (SQS).
ECR image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/enterprise-api:latest.
CloudWatch retention: 90 days. Execution role: enterprise-api-exec.
Account: 123456789012.
