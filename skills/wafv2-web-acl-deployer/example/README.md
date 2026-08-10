# End-to-End Example: WAFv2 Web ACL Provisioning

A walkthrough showing how to use the `wafv2-web-acl-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a WAFv2 Web ACL for the payments API ALB. The ACL
requires:

- REGIONAL scope in us-east-1
- Default action: Allow
- Managed rules: AWSManagedRulesCommonRuleSet, AWSManagedRulesSQLiRuleSet,
  AmazonIpReputationList
- Custom rule: allow partner IPs from an IP set at priority 0
- Rate-based rule: 2000 req / 5 min on /api/ paths, aggregate key IP
- Logging: Kinesis Firehose delivery stream `aws-waf-logs-payments`
- Association: ALB `payments-alb`
- Tags: Environment=production, Application=payments

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-wafv2-web-acl
```

Then paste the Web ACL requirements.

### Option B: Natural language

```
You: "Provision a WAFv2 Web ACL in us-east-1 for the payments API ALB.
      Name: payments-api-waf. REGIONAL scope. Managed rules: CommonRuleSet,
      SQLiRuleSet, AmazonIpReputationList. Custom rule: allow partner IPs.
      Rate-based: 2000 req/5min on /api/. Logging: Firehose
      aws-waf-logs-payments. Association: ALB payments-alb."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy waf web acl"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ACL: payments-api-waf
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Scope — REGIONAL (us-east-1)
  [✓]      Default action — Allow
  [✓]      Managed rules — AWSManagedRulesCommonRuleSet (priority 10), AWSManagedRulesSQLiRuleSet (priority 20), AmazonIpReputationList (priority 100)
  [✓]      Custom rule — allow partner IPs from IP set partner-ips (priority 0, Allow)
  [✓]      Rate-based rule — 2000 req/5min, aggregate key IP, scope /api/ (priority 5000)
  [✓]      Visibility config — CloudWatch metrics enabled, sampled requests enabled
  [✓]      Logging — Kinesis Firehose aws-waf-logs-payments
  [✓]      Association — arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-alb/50dc6c495c0c9188
  [✓]      Tags — Environment=production, Application=payments
VERIFICATION_COMMANDS:
  aws wafv2 list-web-acls --scope REGIONAL --region us-east-1
  aws wafv2 get-web-acl --scope REGIONAL --id <web-acl-id> --region us-east-1
  aws wafv2 list-resources-for-web-acl --web-acl-arn <web-acl-arn> --region us-east-1
  aws wafv2 get-logging-configuration --web-acl-arn <web-acl-arn> --region us-east-1
```

---

## Step 3 — Provisioning commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Create the Firehose delivery stream (prefix aws-waf-logs- required)
aws firehose create-delivery-stream \
  --delivery-stream-name aws-waf-logs-payments \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration \
    RoleARN=arn:aws:iam::123456789012:role/firehose-waf-role,\
    BucketARN=arn:aws:s3:::payments-waf-logs

# Step 2: Create the Web ACL with managed rules + rate-based rule
WEB_ACL_ARN=$(aws wafv2 create-web-acl \
  --name payments-api-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --description "WAF for payments API ALB" \
  --rules '[...]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=payments-api-waf \
  --region us-east-1 \
  --tags '[{"Key":"Environment","TagValue":"production"},{"Key":"Application","TagValue":"payments"}]' \
  --query 'Summary.ARN' --output text)

# Step 3: Configure logging
aws wafv2 put-logging-configuration \
  --logging-configuration \
    WebACLArn=${WEB_ACL_ARN},\
    LogDestinationConfigs=arn:aws:firehose:us-east-1:123456789012:deliverystream/aws-waf-logs-payments \
  --region us-east-1

# Step 4: Associate with the ALB
aws wafv2 associate-web-acl \
  --web-acl-arn ${WEB_ACL_ARN} \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-alb/50dc6c495c0c9188 \
  --region us-east-1
```

---

## Step 4 — Post-provisioning verification

```bash
# List Web ACLs
aws wafv2 list-web-acls --scope REGIONAL --region us-east-1

# Get full Web ACL config (rules, priorities, actions, visibility config)
aws wafv2 get-web-acl --scope REGIONAL --id <web-acl-id> --region us-east-1

# List resources associated with the Web ACL
aws wafv2 list-resources-for-web-acl --web-acl-arn ${WEB_ACL_ARN} --region us-east-1

# Verify logging configuration
aws wafv2 get-logging-configuration --web-acl-arn ${WEB_ACL_ARN} --region us-east-1

# Get sampled requests for a specific rule (for debugging)
aws wafv2 get-sampled-requests \
  --web-acl-arn ${WEB_ACL_ARN} \
  --rule-metric-name rate-limit-api \
  --scope REGIONAL \
  --time-window StartTime=2026-08-10T00:00:00Z,EndTime=2026-08-10T00:05:00Z \
  --max-items 100 \
  --region us-east-1
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Allow-list priority | Managed rules at priority 0 | Allow-list at 0, managed at 10+ | Partner IPs blocked by managed rules if managed rules evaluate first |
| Rate-based aggregate key | Always uses `IP` | `FORWARDED_IP` behind CDN/proxy | Behind a CDN, all clients share the edge IP — `IP` rate-limits the CDN node, not the abusive client |
| Firehose prefix | Any stream name | `aws-waf-logs-` prefix enforced | WAF rejects non-prefixed stream names at PutLoggingConfiguration time |
| Logging resource policy | Often forgotten | CloudWatch Logs / S3 policy with `delivery.logs.amazonaws.com` | Without the policy, WAF silently drops logs — no error, just missing data |
| Visibility config | Often omitted on rules | Required on every rule | Without sampled requests and CloudWatch metrics, you cannot debug rule matches or measure impact |
| OverrideAction | Wrong action type | `None` for managed rules, `Count` for new ATP rules | Managed rules use OverrideAction None (rules block directly); ATP starts in Count mode for false-positive baselining |
| Scope selection | REGIONAL for CloudFront | CLOUDFRONT for CloudFront, REGIONAL for ALB/API Gateway | Wrong scope = silent association failure; scope is immutable after creation |

---

## Related artifacts

- **Skill definition:** `skills/wafv2-web-acl-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/wafv2-web-acl-deployer/references/deployment-cli-commands.md`
- **Managed rules, logging, CAPTCHA, ATP guide:** `skills/wafv2-web-acl-deployer/references/managed-rules-and-logging-guide.md`
- **Slash command:** `commands/aws/deploy-wafv2-web-acl.md`
- **Eval suite:** `skills/wafv2-web-acl-deployer/evals/evals.json`
- **Legacy test cases:** `skills/wafv2-web-acl-deployer/eval/test-cases.yaml`
