# Eval: vpc-no-nat-gateway

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — NAT Gateway required for internet access

## Prompt

Deploy a Lambda function named "webhook-sender" in us-east-1.
Runtime: nodejs20.x. Handler: index.handler. The function is
attached to VPC subnets subnet-private-a, subnet-private-b (private
subnets, no NAT Gateway configured). It needs to send HTTP POST to
https://api.partner.com/webhook (external internet endpoint).
Memory: 512 MB, Timeout: 10s. Execution role exists with
AWSLambdaBasicExecutionRole. Account: 123456789012.
