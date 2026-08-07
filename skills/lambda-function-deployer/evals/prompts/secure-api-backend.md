# Eval: secure-api-backend

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with VPC, NAT Gateway, KMS, tracing

## Prompt

Deploy a production Lambda function named "order-api-prod" in
us-east-1. Runtime: python3.12. Handler: app.handler. It needs to
access an RDS PostgreSQL instance in a VPC (subnets: subnet-aaa,
subnet-bbb; security group: sg-orders-api). The function also calls
Stripe API (needs internet access via NAT Gateway). Use KMS key
alias/lambda-env-key for env var encryption. Environment:
DB_HOST=orders-db.cluster.example.rds.amazonaws.com. STRIPE_API_KEY
referenced via Secrets Manager. Memory: 512 MB, Timeout: 15s.
On-failure destination: order-api-dlq (SQS). X-Ray tracing active.
CloudWatch retention: 30 days. Account: 123456789012.
