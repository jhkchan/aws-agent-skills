# Eval: cloudfront-global-with-bot-control

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CLOUDFRONT scope, Bot Control with category overrides, geo-block, FORWARDED_IP rate rule

## Prompt

Provision a WAFv2 Web ACL for a CloudFront distribution.
Name: payments-cdn-waf. Scope: CLOUDFRONT. Managed rules:
AWSManagedRulesCommonRuleSet (priority 10),
AWSManagedRulesBotControlRuleSet (priority 200, allow
CategorySearchEngine, block CategorySpam),
AmazonIpReputationList (priority 100). Custom geo-block
rule: block RU, KP, IR at priority 1000. Rate-based rule:
1000 req/5min aggregate key FORWARDED_IP with
X-Forwarded-For Position FIRST on all paths, priority 5000.
Logging: Kinesis Firehose aws-waf-logs-payments-cdn.
Tags: Environment=production, Application=payments-cdn.
