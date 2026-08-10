# Eval: rate-based-forwarded-ip-api-gateway

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — API Gateway REST stage association, FORWARDED_IP rate rule with scope-down, CloudWatch Logs

## Prompt

Provision a WAFv2 Web ACL in us-west-2 for an API Gateway
REST API. Name: orders-api-waf. Scope: REGIONAL. Managed
rules: AWSManagedRulesCommonRuleSet (priority 10),
AWSManagedRulesSQLiRuleSet (priority 20). Rate-based rule:
500 req/5min aggregate key FORWARDED_IP, header
X-Forwarded-For, Position FIRST, FallbackBehavior NO_MATCH,
scope down to /v1/orders path, priority 5000. Logging:
CloudWatch Logs log group /aws/wafv2/orders-api.
Association: API Gateway stage
arn:aws:apigateway:us-west-2::/restapis/abc123/stages/prod.
Tags: Environment=production, Application=orders-api.
