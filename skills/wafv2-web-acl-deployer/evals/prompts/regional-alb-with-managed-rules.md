# Eval: regional-alb-with-managed-rules

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — REGIONAL scope, Common+SQLi+IPReputation managed rules, IP-set allow rule, rate-based IP rule, Firehose logging, ALB association

## Prompt

Provision a WAFv2 Web ACL in us-east-1 for the payments
API ALB. Name: payments-api-waf. Scope: REGIONAL. Default
action: Allow. Managed rules: AWSManagedRulesCommonRuleSet
(priority 10), AWSManagedRulesSQLiRuleSet (priority 20),
AmazonIpReputationList (priority 100). Custom rule: allow
partner IPs from IP set partner-ips at priority 0. Rate-based
rule: 2000 req/5min on /api/ paths, aggregate key IP, priority
5000. Logging: Kinesis Firehose delivery stream
aws-waf-logs-payments. Association: ALB arn:aws:elasticload
balancing:us-east-1:123456789012:loadbalancer/app/
payments-alb/50dc6c495c0c9188. Tags: Environment=production,
Application=payments.
