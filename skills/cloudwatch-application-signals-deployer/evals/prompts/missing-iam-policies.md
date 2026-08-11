# Eval: missing-iam-policies

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — required IAM policy missing

## Prompt

Enable CloudWatch Application Signals on the orders-api service
running on ECS Fargate in us-east-1. Runtime: Java 17. The task
role orders-api-task currently has only AWSXrayWriteOnlyAccess
attached; it does NOT have
CloudWatchApplicationSignalsReportServiceAccess. X-Ray sampling
is set up (FixedRate=0.05). Account: 123456789012.
