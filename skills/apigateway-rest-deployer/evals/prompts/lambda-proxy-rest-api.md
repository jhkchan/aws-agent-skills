# Eval prompt: lambda-proxy-rest-api

Design a deployment plan for a production REST API. Emit the standard
VERDICT block (API_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- API type: REST (v1) — needs usage plans, resource policies, and EDGE
  optionality
- Endpoint type: REGIONAL (us-east-1)
- Resources and methods:
  - /users [GET (list), POST (create)]
  - /users/{userId} [GET (read), PUT (update), DELETE (delete)]
- Integration: AWS_PROXY to Lambda function `user-service-handler`
  (exists in us-east-1, same account)
- Authorization: COGNITO_USER_POOLS (user pool `prod-users-pool` exists
  in us-east-1)
- Usage plan: `prod-consumer-plan` with throttle rate=100, burst=200,
  quota=1,000,000 requests/month
- API keys: required on ALL methods (per-consumer rate limiting)
- Stage throttling: default 1000 rps / 500 burst
- WAF: REGIONAL scope in us-east-1, CommonRuleSet + SQLiRuleSet +
  rate-based (2000 req/5min per IP)
- Access logging: JSON format to CloudWatch log group
  `/aws/apigateway/prod-user-service` with $context.requestId, status,
  responseLatency, sourceIp, errorMessage
- Canary: enabled at 10 percent traffic shifting
- Custom domain: api.example.com with base path mapping `v1`
- ACM cert: arn:aws:acm:us-east-1:111111111111:certificate/abc-123
  (REGIONAL, covers api.example.com)

Existing-account context: the Cognito user pool has 12,000 active users.
The Lambda function `user-service-handler` already has an IAM execution
role with CloudWatch Logs + DynamoDB CRUD. The Lambda has NOT yet been
granted `lambda:InvokeFunction` permission to the API Gateway principal.
