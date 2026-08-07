# Eval prompt: canary-rest-api-deploy

Design a deployment plan for a REST API with canary rollout strategy.
Emit the standard VERDICT block (API_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- API type: REST (v1)
- Endpoint type: REGIONAL (us-east-1)
- Resources and methods:
  - /products [GET (list), POST (create)]
  - /products/{id} [GET (read), PUT (update), DELETE (delete)]
- Integration: AWS_PROXY to Lambda function `products-handler`
- Authorization: COGNITO_USER_POOLS (user pool `prod-shoppers-pool`)
- Stage throttling: 1000 rps / 500 burst default
- Per-method throttling override: POST /products at 100 rps / 50 burst
  (write-side protection against batch creation abuse)
- Canary: 10 percent traffic shifting to new deployment (stable
  deployment retains 90 percent)
- Access logging: JSON to CloudWatch with $context.requestId, status,
  responseLatency, sourceIp, errorMessage, authorizerError
- WAF: REGIONAL scope, rate-based 2000 req/5min per IP +
  CommonRuleSet + BotControlRuleSet
- Stage variables: `productsHandlerName=products-handler-v2` (new
  version for canary validation)

Existing-account context: the API has been live for 14 months with
~50M requests/month. The current stable deployment runs
`products-handler:v1`. This deployment introduces `v2` with a new
DynamoDB schema. The team wants canary to catch any 5xx spikes or
latency regressions before full promotion.
