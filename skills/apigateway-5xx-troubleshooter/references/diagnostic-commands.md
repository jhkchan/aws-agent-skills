# Diagnostic commands - API Gateway 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight: account-wide gather-info gate

```bash
# 1. REST API (v1) — stage config (throttling, deploymentId, access logs)
aws apigateway get-stage --rest-api-id <id> --stage-name <stage> --output json

# 2. HTTP API (v2) — stage config (throttling, route settings)
aws apigatewayv2 get-stage --api-id <id> --stage-name <stage> --output json

# 3. Integration type and timeout (REST)
aws apigateway get-resources --rest-api-id <id> --output json | \
  jq '.items[].resourceMethods'
aws apigateway get-integration --rest-api-id <id> --resource-id <rid> \
  --http-method <verb> --output json

# 4. Integration type and timeout (HTTP API v2)
aws apigatewayv2 get-integrations --api-id <id> --output json

# 5. Lambda function configuration (timeout, memory, runtime)
aws lambda get-function-configuration --function-name <fn> --output json

# 6. CloudWatch metrics — 5xxError, 4xxError, Count, Latency (per stage)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=<api> Name=Stage,Value=<stage> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Average --output json

# 7. AWS Health (regional events for API Gateway or Lambda)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

## Step 1b: gather access logs

If the operator reports "we're getting 5xx" without a specific code, or
the code varies request-to-request, enable or fetch access logs first.

**REST API access log format (recommended JSON):**
```json
{
  "requestId": "$context.requestId",
  "status": "$context.status",
  "integrationStatus": "$context.integrationStatus",
  "integrationErrorMessage": "$context.integrationErrorMessage",
  "responseLatency": "$context.responseLatency",
  "integrationLatency": "$context.integrationLatency",
  "httpMethod": "$context.httpMethod",
  "resourcePath": "$context.resourcePath",
  "sourceIp": "$context.identity.sourceIp"
}
```

```bash
# Fetch access logs from CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/apigateway/<api>/<stage> \
  --filter-pattern '"status":50' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'
```

The `integrationErrorMessage` field is the single most valuable signal —
it pinpoints the exact failure (Malformed Lambda proxy response, Execution
failed due to a timeout error, etc.).

## Step 2a: Lambda runtime error probes

```bash
# Fetch the Lambda function's recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern '"ERROR"' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'

# Also check for runtime-level errors (Task timed out, Runtime.LogError)
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern 'Task timed out' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'

# CloudTrail — confirm the Lambda was invoked and check for errors
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Invoke \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --output json | \
  jq '.Events[] | select(.ResourceName == "<function-name>")'
```

## Step 2b: Lambda proxy response-shape probes

```bash
# Check the Lambda function's return shape by inspecting recent logs
# Lambda proxy logs the return value in some runtimes; otherwise test:
aws lambda invoke \
  --function-name <function-name> \
  --payload file://test-event.json \
  --log-type Tail \
  /tmp/response.json --query 'LogResult' --output text | base64 -d

# Inspect the response body
cat /tmp/response.json | jq .
```

## Step 2c: HTTP backend probes

```bash
# Test the backend directly (bypassing API Gateway)
curl -v -X <method> https://<backend-host>/<path> -d '<test-payload>'

# Check the backend's health endpoint
curl -v https://<backend-host>/health

# If the backend is an ALB, check target health
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json
```

## Step 2d: VPC Link / NLB probes

```bash
# Identify the VPC Link and its associated NLB
aws apigateway get-integration --rest-api-id <id> --resource-id <rid> \
  --http-method <verb> --output json | \
  jq '.connectionId'  # This is the VPC Link ID (vpcl-xxx)

# Check the NLB target group health (find the NLB behind the VPC Link)
aws elbv2 describe-target-groups --load-balancer-arn <nlb-arn> --output json
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json

# Check the VPC Link itself
aws apigateway get-vpc-links --output json
```

## Step 2e: mapping template probes

```bash
# Check the integration response mapping template
aws apigateway get-integration-response --rest-api-id <id> \
  --resource-id <rid> --http-method <verb> \
  --status-code 200 --output json | jq '.responseTemplates'

# Check CloudWatch Logs for mapping template evaluation errors
aws logs filter-log-events \
  --log-group-name /aws/apigateway/<api>/<stage> \
  --filter-pattern 'MappingTemplate' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json
```

## Step 3a: Lambda duration probes

```bash
# Lambda function configured timeout
aws lambda get-function-configuration --function-name <fn> --output json | \
  jq '.Timeout'

# Lambda Duration metric (actual execution time)
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# API Gateway Latency metric (what the client experienced)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=<api> Name=Stage,Value=<stage> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

## Step 3b: HTTP backend latency probes

```bash
# Test the backend response time directly
time curl -X <method> https://<backend-host>/<path> -d '<test-payload>'

# If the backend is an ALB, check target_processing_time in access logs
# ALB access logs in S3:
aws s3 ls s3://<access-log-bucket>/<prefix>/ \
  --recursive | tail -20
```

## Step 3c: timeout mismatch probes

```bash
# Compare Lambda timeout to the integration timeout
LAMBDA_TIMEOUT=$(aws lambda get-function-configuration \
  --function-name <fn> --output json | jq '.Timeout')
echo "Lambda Timeout: ${LAMBDA_TIMEOUT}s"
echo "API Gateway integration timeout: 29s (REST) / 30s (HTTP API)"

# Check the integration timeout setting (if explicitly configured)
aws apigateway get-integration --rest-api-id <id> \
  --resource-id <rid> --http-method <verb> --output json | \
  jq '.timeoutInMillis'
```

## Step 4a: stage throttling probes

```bash
# REST API stage throttling
aws apigateway get-stage --rest-api-id <id> --stage-name <stage> --output json | \
  jq '.methodSettings, .throttle'

# HTTP API stage throttling
aws apigatewayv2 get-stage --api-id <id> --stage-name <stage> --output json | \
  jq '.defaultRouteSettings'

# API Gateway Count metric (total requests)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=<api> Name=Stage,Value=<stage> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 60 --statistics Sum --output json
```

## Step 4b: Lambda concurrency probes

```bash
# Lambda account-level concurrency settings
aws lambda get-account-settings --output json | \
  jq '.AccountLimit'

# Lambda ConcurrentExecutions metric
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json

# Lambda Throttles metric (the smoking gun)
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

## Step 4c: usage plan probes

```bash
# Check usage plans associated with the API stage
aws apigateway get-usage-plans --output json | \
  jq '.items[] | select(.apiStages[]?.apiId == "<api-id>")'

# Check the usage for a specific API key in the failure window
aws apigateway get-usage --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --start-date 2026-08-01 --end-date 2026-08-09 --output json
```

## Step 5: AWS Health / deployment probes

```bash
# Check AWS Health Dashboard for API Gateway events
aws health describe-events \
  --filter services=APIGATEWAY,eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json

# Check for a corrupted deployment (if 500 started after a deployment)
aws apigateway get-stage --rest-api-id <id> --stage-name <stage> --output json | \
  jq '.deploymentId'
aws apigateway get-deployment --rest-api-id <id> \
  --deployment-id <dep-id> --output json
```
