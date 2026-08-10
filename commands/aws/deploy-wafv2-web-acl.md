---
description: Provision an AWS WAFv2 Web ACL with production-grade configuration (correct scope — CLOUDFRONT for CloudFront, REGIONAL for ALB/API Gateway/AppSync/Cognito/App Runner; managed rule groups — CommonRuleSet, SQLiRuleSet, LinuxRuleSet, WindowsRuleSet, AmazonIpReputationList, BotControlRuleSet, ATP, ACFP; custom rules — byte match, IP set, regex, geo, size, rate-based; rule priority ordering; logging to Kinesis Firehose / CloudWatch Logs / S3; resource association; CAPTCHA and Challenge actions; rate-based rules with IP / FORWARDED_IP aggregate keys). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create waf web acl"
  - "provision waf"
  - "wafv2 web acl"
  - "waf managed rules"
  - "waf rate limiting"
  - "waf logging"
  - "waf captcha"
  - "waf challenge action"
  - "bot control rule set"
  - "account takeover prevention"
  - "waf atp"
  - "waf acfp"
  - "waf custom rules"
  - "waf ip set"
  - "waf geo match"
  - "waf byte match"
  - "waf regex pattern"
  - "waf size constraint"
  - "cloudfront waf"
  - "regional waf"
  - "alb waf association"
  - "api gateway waf"
  - "waf forwarded ip"
  - "waf rate based rule"
routes_to: wafv2-web-acl-deployer
---

# /aws:deploy-wafv2-web-acl

Activate the `wafv2-web-acl-deployer` skill and provision an AWS WAFv2
Web ACL with production-grade configuration.

## What it does

The skill walks a 9-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Scope selection (CLOUDFRONT vs REGIONAL — immutable)
2. Default action (Allow vs Block)
3. Managed rule groups (Common, SQLi, Linux, Windows, IP Reputation,
   Bot Control, ATP, ACFP)
4. Custom rules (byte match, IP set, regex, geo, size)
5. Rule priority ordering (allow-lists first, managed rules, custom
   blocks, rate-based last)
6. Rate-based rules (aggregate keys: IP, FORWARDED_IP, URI, query,
   method, header)
7. Logging (Kinesis Firehose, CloudWatch Logs, S3 via Firehose)
8. Association (ALB, API Gateway, CloudFront)
9. CAPTCHA / Challenge actions (bot defense, ATP login protection)

## When to use

- You need to create a new WAFv2 Web ACL with production defaults.
- You are configuring managed rule groups (Common, SQLi, Bot Control,
  ATP).
- You need rate-based rules with the correct aggregate key (IP vs
  FORWARDED_IP).
- You are enabling WAF logging to Firehose / CloudWatch Logs / S3.
- You want to associate a Web ACL with an ALB, API Gateway, or
  CloudFront distribution.
- You are configuring CAPTCHA or Challenge actions for bot defense.
- You want to check for provisioning blockers (wrong scope, missing
  logging destination, missing IP set).

## How to invoke

### Slash command

```
/aws:deploy-wafv2-web-acl
```

Then provide: Web ACL name, scope (CLOUDFRONT / REGIONAL), target
resource ARN, managed rule groups, custom rules, rate-based rules,
logging destination, and CAPTCHA / Challenge requirements.

### Natural language

Any of these routes to the same skill:

- "create a WAF Web ACL for my ALB"
- "provision a CloudFront WAF with Bot Control"
- "set up WAF rate limiting with forwarded IP"
- "configure WAF logging to Firehose"
- "add CAPTCHA to the signup endpoint"
- "enable ATP for login protection"

### CLI routing

```bash
node cli/bin/cli.js route "deploy waf web acl"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and audit
skills (e.g., a WAF Web ACL auditor for post-provisioning checks).

## Example

```
You: /aws:deploy-wafv2-web-acl

     Provision a WAFv2 Web ACL in us-east-1 for the payments API ALB.
     Name: payments-api-waf. REGIONAL scope. Managed rules: CommonRuleSet,
     SQLiRuleSet, AmazonIpReputationList. Custom rule: allow partner IPs.
     Rate-based: 2000 req/5min on /api/. Logging: Firehose
     aws-waf-logs-payments. Association: ALB payments-alb.

Skill:
  ACL: payments-api-waf
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Scope — REGIONAL (us-east-1)
    [✓]      Default action — Allow
    [✓]      Managed rules — AWSManagedRulesCommonRuleSet (priority 10), AWSManagedRulesSQLiRuleSet (priority 20), AmazonIpReputationList (priority 100)
    [✓]      Custom rule — allow partner IPs from IP set partner-ips (priority 0)
    [✓]      Rate-based rule — 2000 req/5min, aggregate key IP, scope /api/ (priority 5000)
    [✓]      Visibility config — metrics enabled, sampled requests enabled
    [✓]      Logging — Kinesis Firehose aws-waf-logs-payments
    [✓]      Association — arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-alb/50dc6c495c0c9188
    [✓]      Tags — Environment=production, Application=payments
  VERIFICATION_COMMANDS:
    aws wafv2 list-web-acls --scope REGIONAL --region us-east-1
    aws wafv2 get-web-acl --scope REGIONAL --id <web-acl-id> --region us-east-1
    aws wafv2 list-resources-for-web-acl --web-acl-arn <web-acl-arn> --region us-east-1
    aws wafv2 get-logging-configuration --web-acl-arn <web-acl-arn> --region us-east-1
```

## References

- Skill definition: `skills/wafv2-web-acl-deployer/SKILL.md`
- Deployment CLI commands: `skills/wafv2-web-acl-deployer/references/deployment-cli-commands.md`
- Managed rules, logging, CAPTCHA, ATP guide: `skills/wafv2-web-acl-deployer/references/managed-rules-and-logging-guide.md`
- Eval suite: `skills/wafv2-web-acl-deployer/evals/evals.json`
