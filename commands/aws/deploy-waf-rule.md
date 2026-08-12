---
description: Provision an AWS WAFv2 rule set with production-grade defaults (CloudFront vs Regional scope, managed rule groups, custom rules, WCU budget planning, priority ordering, rate-based rules, IP sets, regex pattern sets, label chaining, logging via Firehose, CloudFront association). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create waf rule"
  - "deploy waf rule"
  - "waf managed rule group"
  - "waf custom rule"
  - "waf web acl"
  - "waf byte match"
  - "waf geo match"
  - "waf rate based rule"
  - "waf ip set"
  - "waf regex pattern set"
  - "waf wcu budget"
  - "waf cloudfront acl"
  - "waf logging"
  - "waf bot control"
  - "waf atp"
  - "waf label matching"
  - "waf challenge action"
  - "waf captcha"
routes_to: waf-rule-deployer
---

# /aws:deploy-waf-rule

Activate the `waf-rule-deployer` skill and provision an AWS WAFv2
rule set with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Scope selection (CloudFront scope in us-east-1 vs Regional)
2. Managed rule groups (high coverage first)
3. Custom rules (exceptions and specifics)
4. WCU budget planning (1500 default)
5. Rule priority ordering (specific allow before broad block)
6. Action types (allow, block, count, CAPTCHA, Challenge)
7. IP set and regex pattern set
8. Rate-based rules
9. Bot control and ATP
10. Label matching and rule chaining
11. Logging configuration (Firehose to S3)
12. CloudFront distribution association

## When to use

- You need to create a WAFv2 Web ACL with managed and custom rules.
- You are attaching managed rule groups (CommonRuleSet, SQLiRuleSet,
  AmazonIpReputationList).
- You are writing custom byte-match, geo-match, or rate-based rules.
- You need to plan the WCU capacity budget.
- You need to configure WAF logging to S3 via Kinesis Firehose.
- You need to associate a Web ACL with a CloudFront distribution.
- You need to chain rules using labels.

## When NOT to use

- **AWS Shield Advanced** — use shield skills for DDoS protection.
- **AWS Firewall Manager** — use firewall-manager skills for
  multi-account WAF management.
- **Auditing an existing Web ACL** — use wafv2-web-acl-auditor.
- **Web ACL creation with association focus only** — use
  wafv2-web-acl-deployer for simpler ACL+association workflows.

## How to invoke

### Slash command

```
/aws:deploy-waf-rule
```

Then provide: ACL name, scope (CLOUDFRONT or REGIONAL), region,
managed rule groups, custom rules (with priorities and actions),
IP sets / regex sets, rate-based rules, logging configuration,
CloudFront distribution ARN (if applicable), tags.

### Natural language

Any of these routes to the same skill:

- "create a CloudFront Web ACL with managed rules"
- "add a custom geo-match block to my WAF"
- "configure WAF rate limiting on /login"
- "enable WAF logging to S3 via Firehose"
- "plan my WAF WCU budget"

### CLI routing

```bash
node cli/bin/cli.js route "create a waf web acl"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create WAF rule
sets. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-waf-rule

     Create a CloudFront Web ACL named production-cloudfront-acl
     with CommonRuleSet, SQLiRuleSet, and AmazonIpReputationList.
     Allow partner CIDRs (203.0.113.0/24) at priority 0. Block
     RU and KP at priority 40. Log to Firehose
     aws-waf-logs-production. Associate with distribution
     E1234567890.

Skill:
  WAF_RULE_SET: production-cloudfront-acl (CLOUDFRONT, us-east-1) — 926/1500 WCU
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Scope: CLOUDFRONT (us-east-1)
    [✓] Custom rule: allow-partner-ip — priority 0 — ALLOW — 1 WCU
    [✓] Managed: AWSManagedRulesCommonRuleSet — priority 10 — 700 WCU
    [✓] Managed: AWSManagedRulesSQLiRuleSet — priority 20 — 200 WCU
    [✓] Custom rule: block-high-risk-geo — priority 40 — BLOCK — GeoMatch(RU, KP)
    [✓] WCU budget: 926 / 1500 (574 headroom)
    [✓] Priority order: allow (0) before block (40) — VERIFIED
  VERIFICATION_COMMANDS:
    aws wafv2 get-web-acl --scope CLOUDFRONT --id <acl-id> --region us-east-1
    aws wafv2 get-logging-configuration --web-acl-arn <arn> --region us-east-1
```

## References

- Skill definition: `skills/waf-rule-deployer/SKILL.md`
- Managed rules and WCU guide: `skills/waf-rule-deployer/references/managed-rules-and-wcu.md`
- Custom rules and labels guide: `skills/waf-rule-deployer/references/custom-rules-and-labels.md`
- Eval suite: `skills/waf-rule-deployer/evals/evals.json`
