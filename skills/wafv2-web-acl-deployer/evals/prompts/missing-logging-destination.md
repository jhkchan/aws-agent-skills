# Eval: missing-logging-destination

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — logging destination required but not provided

## Prompt

Provision a WAFv2 Web ACL in us-east-1 for the payments API.
Name: payments-api-waf. Scope: REGIONAL. Managed rules:
AWSManagedRulesCommonRuleSet. Enable WAF logging to Kinesis
Firehose. ALB association: arn:aws:elasticloadbalancing:us-east-1:
123456789012:loadbalancer/app/payments-alb/50dc6c495c0c9188.
I have not created the Firehose delivery stream yet.
