# Eval: captcha-atp-login-protection

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CAPTCHA action on /signup, ATP managed rule on /api/v1/login with field config, rate-based on login

## Prompt

Provision a WAFv2 Web ACL in us-east-1 for the auth service.
Name: auth-service-waf. Scope: REGIONAL. Managed rules:
AWSManagedRulesCommonRuleSet (priority 10),
AWSManagedRulesSQLiRuleSet (priority 20),
AWSManagedRulesATPRuleSet (priority 200, login path
/api/v1/login, payload JSON, username field "email",
password field "password", OverrideAction Count). Custom
CAPTCHA rule on /signup path at priority 1000. Rate-based
rule: 100 req/5min aggregate key IP on /api/v1/login path,
priority 5000. Logging: Kinesis Firehose
aws-waf-logs-auth-service. Association: ALB
arn:aws:elasticloadbalancing:us-east-1:123456789012:
loadbalancer/app/auth-alb/abc123. Tags: Environment=production,
Application=auth.
