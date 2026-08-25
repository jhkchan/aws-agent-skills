# Error handling - API Gateway 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### For BACKEND_RESPONSE_FORMAT — Lambda proxy malformed response

1. Update the Lambda function to return the proxy response format:
   ```javascript
   // Node.js — correct format
   return {
     statusCode: 200,                    // integer, not string
     body: JSON.stringify(result),       // body MUST be a string
     headers: { "Content-Type": "application/json" }
   };
   ```
   ```python
   # Python — correct format
   return {
       "statusCode": 200,
       "body": json.dumps(result),
       "headers": {"Content-Type": "application/json"}
   }
   ```
2. Deploy the Lambda function (`aws lambda update-function-code`).
3. Deploy the API: `aws apigateway create-deployment --rest-api-id <id>
   --stage-name <stage>`.
4. Verify: the endpoint returns 200 with the expected body.

### For BACKEND_LAMBDA_ERROR — Lambda runtime crash

1. Identify the exception in the Lambda CloudWatch Logs.
2. Fix the code (add null checks, env var validation, IAM permissions).
3. Redeploy the function and verify with a test invoke.

### For BACKEND_HTTP_INVALID — HTTP backend invalid response

1. Test the backend directly with `curl -v`.
2. If SSL handshake fails: renew/replace the backend certificate.
3. If the backend returns malformed HTTP: fix the backend application.
4. If the backend is unreachable: check the backend instance/ALB health.

### For BACKEND_VPC_LINK — NLB target unhealthy

1. Fix the target health:
   ```bash
   aws elbv2 describe-target-health --target-group-arn <tg-arn>
   # Address the unhealthy reason (Target.FailedHealthChecks, Target.Timeout)
   ```
2. Verify the VPC Link is `AVAILABLE`:
   `aws apigateway get-vpc-links`.
3. Verify the integration `connectionId` matches the VPC Link ID.

### For TIMEOUT_LAMBDA — Lambda too slow

1. Optimize the function (database query tuning, caching, async I/O).
2. Increase the integration timeout (if < 29s for REST):
   `aws apigateway update-integration --rest-api-id <id> --resource-id <rid>
   --http-method <verb> --patch-operations
   op=replace,path=/timeoutInMillis,value=29000`.
3. If the function genuinely needs > 29s: migrate to an async pattern
   (API Gateway returns 202; client polls or receives a webhook).

### For TIMEOUT_MISMATCH — Lambda timeout > integration timeout

1. Reduce the Lambda Timeout to ≤ 29s:
   `aws lambda update-function-configuration --function-name <fn> --timeout 29`.
2. Optimize the function to complete within 29s.
3. For long-running workloads: use Step Functions or async invocation.

### For THROTTLE_STAGE — stage-level throttling

1. Raise the stage throttle (verify the backend can handle it):
   ```bash
   aws apigateway update-stage --rest-api-id <id> --stage-name <stage> \
     --patch-operations \
     op=replace,path=/methods/*/throttling/rateLimit,value=1000,\
     op=replace,path=/methods/*/throttling/burstLimit,value=2000
   ```
2. Add a usage plan for per-key throttling.

### For THROTTLE_CONCURRENCY — Lambda concurrency limit

1. Request a concurrency quota increase via the Lambda console or:
   ```bash
   aws lambda put-function-concurrency --function-name <fn> \
     --reserved-concurrent-configurations ReservedConcurrentExecutions=500
   ```
2. Or add an SQS queue + Lambda consumer to smooth traffic spikes.

### For INTERNAL_ERROR — corrupted deployment

1. Create a new deployment:
   ```bash
   aws apigateway create-deployment --rest-api-id <id> --stage-name <stage>
   ```
2. If the 500 persists: escalate to AWS Support.

### For ESCALATE — AWS-side incident

1. Surface the AWS Health event ARN and API id.
2. Open a Support case with the time window and request IDs from access logs.
