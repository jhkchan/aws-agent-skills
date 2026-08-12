# End-to-End Example: WAF Rule Deployment

A walkthrough showing how to use the `waf-rule-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a CloudFront-scoped Web ACL with managed rule
groups (CommonRuleSet, SQLiRuleSet, AmazonIpReputationList) plus
custom exceptions (partner IP allow, high-risk geo block, login
rate-limit). The ACL needs:

- Scope: CLOUDFRONT (us-east-1)
- Default action: ALLOW
- Managed rules: CommonRuleSet, SQLiRuleSet, AmazonIpReputationList
- Custom allow: partner CIDRs (IP set) at priority 0
- Custom block: high-risk geos (RU, KP) at priority 40
- Custom rate-based: 100 req/5min per IP on /login at priority 50
- Logging: Firehose aws-waf-logs-production → S3 waf-logs-bucket
- Distribution: E1234567890

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-waf-rule
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudFront Web ACL with CommonRuleSet, SQLiRuleSet,
      and AmazonIpReputationList. Allow partner CIDRs at priority 0.
      Block RU and KP at priority 40. Rate-limit /login to 100
      req/5min. Log to Firehose aws-waf-logs-production. Associate
      with distribution E1234567890."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a waf web acl for cloudfront"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
WAF_RULE_SET: production-cloudfront-acl (CLOUDFRONT, us-east-1) — 926/1500 WCU
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Scope: CLOUDFRONT (us-east-1)
  [✓] Default action: ALLOW
  [✓] Custom rule: allow-partner-ip — priority 0 — action ALLOW — IPSetMatch(partner-cidrs) — 1 WCU
  [✓] Managed rule group: AWS/AWSManagedRulesCommonRuleSet (latest) — priority 10 — 700 WCU
  [✓] Managed rule group: AWS/AWSManagedRulesSQLiRuleSet (latest) — priority 20 — 200 WCU
  [✓] Managed rule group: AWS/AWSManagedRulesAmazonIpReputationList (latest) — priority 30 — 20 WCU
  [✓] Custom rule: block-high-risk-geo — priority 40 — action BLOCK — GeoMatch(RU, KP) — 3 WCU
  [✓] Custom rule: rate-limit-login — priority 50 — action BLOCK — RateBased(100/5min, IP) on /login — 2 WCU
  [✓] WCU budget: 926 / 1500 (574 WCU headroom)
  [✓] Priority order: allow-partner-ip (0) before block-high-risk-geo (40) — VERIFIED
  [✓] IP set: partner-cidrs (CLOUDFRONT, us-east-1) — 2 addresses
  [✓] Logging: Firehose aws-waf-logs-production → S3 waf-logs-bucket (redacted: Authorization)
  [✓] CloudFront association: arn:aws:cloudfront::123456789012:distribution/E1234567890
  [✓] Tags: Environment=production, Protected=cloudfront
VERIFICATION_COMMANDS:
  aws wafv2 get-web-acl --scope CLOUDFRONT --id <acl-id> --region us-east-1
  aws wafv2 get-logging-configuration --web-acl-arn <arn> --region us-east-1
  aws cloudfront get-distribution-config --id E1234567890
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create IP set for partner CIDRs (must be us-east-1 for CloudFront scope)
IP_SET_ARN=$(aws wafv2 create-ip-set \
  --scope CLOUDFRONT --region us-east-1 \
  --name "partner-cidrs" \
  --addresses "203.0.113.0/24" "198.51.100.10/32" \
  --ip-address-version IPV4 \
  --query 'Summary.IPSetARN' --output text)

# Step 2: Create the Web ACL
ACL_ARN=$(aws wafv2 create-web-acl \
  --name "production-cloudfront-acl" \
  --scope CLOUDFRONT \
  --region us-east-1 \
  --default-action Allow={} \
  --description "Production WAF for CloudFront" \
  --rules '[
    {
      "Name": "allow-partner-ip",
      "Priority": 0,
      "Action": { "Allow": {} },
      "Statement": {
        "IPSetReferenceStatement": { "ARN": "'"$IP_SET_ARN"'" }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "allow-partner-ip"
      }
    },
    {
      "Name": "common-ruleset",
      "Priority": 10,
      "OverrideAction": { "None": {} },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "Name": "AWSManagedRulesCommonRuleSet",
          "VendorName": "AWS"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "common-ruleset"
      }
    },
    {
      "Name": "sqli-ruleset",
      "Priority": 20,
      "OverrideAction": { "None": {} },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "Name": "AWSManagedRulesSQLiRuleSet",
          "VendorName": "AWS"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "sqli-ruleset"
      }
    },
    {
      "Name": "ip-reputation",
      "Priority": 30,
      "OverrideAction": { "None": {} },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "Name": "AWSManagedRulesAmazonIpReputationList",
          "VendorName": "AWS"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "ip-reputation"
      }
    },
    {
      "Name": "block-high-risk-geo",
      "Priority": 40,
      "Action": { "Block": {} },
      "Statement": {
        "GeoMatchStatement": { "CountryCodes": ["RU", "KP"] }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "block-high-risk-geo"
      }
    },
    {
      "Name": "rate-limit-login",
      "Priority": 50,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 100,
          "AggregateKeyType": "IP",
          "ScopeDownStatement": {
            "ByteMatchStatement": {
              "SearchString": "/login",
              "FieldToMatch": { "UriPath": {} },
              "TextTransformations": [{ "Priority": 0, "Type": "NONE" }],
              "PositionalConstraint": "STARTS_WITH"
            }
          }
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "rate-limit-login"
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=production-cloudfront-acl \
  --tags Key=Environment,Value=production Key=Protected,Value=cloudfront \
  --query 'Summary.ARN' --output text)

# Step 3: Enable logging (Firehose must start with aws-waf-logs-)
aws wafv2 put-logging-configuration \
  --web-acl-arn "$ACL_ARN" \
  --logging-configuration \
    LogDestinationConfigs=arn:aws:firehose:us-east-1:123456789012:deliverystream/aws-waf-logs-production,\
    RedactedFields=[{SingleHeader={Name=Authorization}}] \
  --region us-east-1

# Step 4: Associate with CloudFront distribution
aws wafv2 associate-web-acl \
  --web-acl-arn "$ACL_ARN" \
  --resource-arn arn:aws:cloudfront::123456789012:distribution/E1234567890 \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the Web ACL exists and check WCU
aws wafv2 get-web-acl \
  --scope CLOUDFRONT --region us-east-1 \
  --id $(echo "$ACL_ARN" | cut -d'/' -f2) \
  --query 'WebACL.{Name:Name,Capacity:Capacity,DefaultAction:DefaultAction}'

# Verify logging configuration
aws wafv2 get-logging-configuration \
  --web-acl-arn "$ACL_ARN" \
  --region us-east-1

# Verify CloudFront association
aws wafv2 get-web-acl-for-resource \
  --resource-arn arn:aws:cloudfront::123456789012:distribution/E1234567890 \
  --region us-east-1 \
  --query 'WebACL.WebACLArn' --output text

# Verify the IP set
aws wafv2 get-ip-set \
  --scope CLOUDFRONT --region us-east-1 \
  --id $(echo "$IP_SET_ARN" | cut -d'/' -f2) \
  --query 'IPSet.{Name:Name,Addresses:Addresses}'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| CloudFront scope region | Any region | us-east-1 only | CloudFront scope requires us-east-1; association fails otherwise |
| Priority ordering | Random or unspecified | Specific allow (0) before broad block (40) | First match wins; allow must be first |
| WCU budget | Not calculated | 926/1500 cited with headroom | Exceeding 1500 fails create/update |
| Firehose naming | Arbitrary name | Must start with aws-waf-logs- | WAF rejects other prefixes |
| IP set scope/region | Any scope/region | Same scope and region as ACL | Cross-scope/region references fail |
| Rate-based forwarded IP | Source IP only | FORWARDED_IP behind proxy | Without it, all proxy clients share one bucket |
| Managed rule versions | Unpinned or unspecified | Default latest or pinned with quarterly review | Pinned versions stop threat-intel updates |

---

## Related artifacts

- **Skill definition:** `skills/waf-rule-deployer/SKILL.md`
- **Managed rules and WCU guide:** `skills/waf-rule-deployer/references/managed-rules-and-wcu.md`
- **Custom rules and labels guide:** `skills/waf-rule-deployer/references/custom-rules-and-labels.md`
- **Slash command:** `commands/aws/deploy-waf-rule.md`
- **Eval suite:** `skills/waf-rule-deployer/evals/evals.json`
- **Legacy test cases:** `skills/waf-rule-deployer/eval/test-cases.yaml`
