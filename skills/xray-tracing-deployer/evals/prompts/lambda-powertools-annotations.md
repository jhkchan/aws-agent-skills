# Eval: lambda-powertools-annotations

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Powertools decorators, custom high-value sampling, annotations

## Prompt

Enable X-Ray tracing on a Lambda function named
"checkout-handler-prod" in us-east-1. Runtime Python 3.11. Use
AWS Lambda Powertools for tracing (capture_lambda_handler and
capture_method decorators). The function calls DynamoDB and SQS
via boto3. Lambda execution role checkout-exec-role (needs X-Ray
write permissions). Custom sampling rule checkout-high-value
(100% sampling, reservoir 5/s) matching the Lambda service name.
Annotations: order_id, customer_id, environment=production.
Metadata: processing_time_ms. Enable CloudWatch ServiceLens.
Account: 123456789012.
