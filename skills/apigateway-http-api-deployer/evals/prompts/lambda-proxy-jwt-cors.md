# Eval prompt: lambda-proxy-jwt-cors

Design a deployment plan for a production HTTP API. Emit the standard
VERDICT block (API_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- API type: HTTP (v2)
- Endpoint type: REGIONAL (us-east-1)
- Routes and authorization:
  - GET /health [NONE] — public health probe
  - GET /users [JWT] — list users
  - POST /users [JWT] — create user
  - GET /users/{userId} [JWT] — get one user
  - ANY /{proxy+} [JWT] — catch-all to Lambda fallback
- Integration: AWS_PROXY to Lambda function `user-service-handler`
  (exists in us-east-1, same account)
- Authorization: JWT, issuer
  `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc/`
  (Cognito, trailing slash present), audience `1a2b3c4d` (app client id)
- CORS: allowOrigins=https://app.example.com,
  allowMethods=GET,POST,OPTIONS, allowHeaders=Authorization,Content-Type,
  allowCredentials=true, maxAge=600
- Stage: `$default` with auto-deploy=true
- Access logging: JSON to CloudWatch log group
  `/aws/apigateway/prod-user-http` with $context.requestId, routeKey,
  status, integrationLatency, sourceIp, errorMessage
- Custom domain: api.example.com (ACM cert
  arn:aws:acm:us-east-1:111111111111:certificate/abc-123, REGIONAL,
  API mapping key empty = apex)
- WAF: REGIONAL scope in us-east-1, CommonRuleSet + SQLiRuleSet +
  rate-based (2000 req/5min per IP)
- Throttle: 1000 rps / 500 burst default; 100/200 on POST /users

Existing-account context: the Cognito user pool has 12,000 active
users. The Lambda function `user-service-handler` already has an IAM
execution role with CloudWatch Logs + DynamoDB CRUD. The Lambda has
NOT yet been granted `lambda:InvokeFunction` permission to the API
Gateway principal. The WAF Web ACL `prod-http-waf` already exists.
