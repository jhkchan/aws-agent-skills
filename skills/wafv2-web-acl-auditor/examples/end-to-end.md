# End-to-end usage scenario: wafv2-web-acl-auditor

A walkthrough showing the skill auditing a Web ACL that looks healthy at first
glance — managed rule groups are present and visibility is enabled — but
contains a shadow bypass rule that silently disables protection for all API
traffic. This exercises shadow-rule detection (Step 2), coverage assessment
(Step 4), and the priority-ordering reasoning that a generic assistant misses.

## Input (user prompt)

> Audit this WAF before we go to production. It's attached to our main ALB.

```json
{
  "Name": "api-gateway-acl",
  "Scope": "REGIONAL",
  "DefaultAction": { "Allow": {} },
  "Rules": [
    {
      "Name": "internal-api-allow",
      "Priority": 0,
      "Action": { "Allow": {} },
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "/api/",
          "FieldToMatch": { "UriPath": {} },
          "TextTransformations": [{ "Priority": 0, "Type": "NONE" }],
          "PositionalConstraint": "STARTS_WITH"
        }
      },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "internal-api-allow",
        "SampledRequestsEnabled": true
      }
    },
    {
      "Name": "AWS-AWSManagedRulesCommonRuleSet",
      "Priority": 10,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet",
        "SampledRequestsEnabled": true
      }
    },
    {
      "Name": "AWS-AWSManagedRulesSQLiRuleSet",
      "Priority": 20,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesSQLiRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "SQLiRuleSet",
        "SampledRequestsEnabled": true
      }
    }
  ],
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": true,
    "MetricName": "api-gateway-acl",
    "SampledRequestsEnabled": true
  }
}
```

## Skill output

```text
WEBACL: api-gateway-acl
VERDICT: MISCONFIGURED
REASON: Step 2: custom rule "internal-api-allow" at priority 0 with Action
Allow matches URIPath STARTS_WITH /api/, shadowing all managed rule groups
(CommonRuleSet at priority 10, SQLiRuleSet at priority 20) for the entire API
surface. WAF evaluates rules in ascending priority order and terminates on the
first Allow/Block/CAPTCHA — the managed rule groups never inspect /api/
traffic. No rate-based rule (Step 5) and no logging configuration (Step 6)
compound the exposure.
RISK: CRITICAL
GAPS: shadow-rule, no-rate-limit, no-logging
REMEDIATION: (1) Move the internal-api-allow rule to a priority HIGHER than
the managed rule groups (e.g., priority 100), so managed rules inspect /api/
traffic first. Or scope it to an exact-match health-check path (e.g.,
/api/health) and remove the STARTS_WITH wildcard. (2) Add a rate-based rule
with AggregateKeyType FORWARDED_IP and HeaderName X-Forwarded-For (the ALB
forwards client IP in this header). (3) Enable logging to CloudWatch Logs or
Kinesis Data Firehose: aws wafv2 put-logging-configuration.
```

## What the skill caught that a generic assistant misses

1. **Priority-ordering shadow detection.** A generic assistant sees managed
   rule groups in BLOCK mode and pronounces the ACL "healthy." The skill's
   Step 2 recognizes that `Action: Allow` at priority 0 with a broad
   `STARTS_WITH /api/` match **terminates evaluation** before the managed
   groups at priorities 10 and 20 ever fire. The managed rules are dead code
   for all API traffic — the most critical attack surface.

2. **`TextTransformations: [{Type: NONE}]` on the shadow rule.** The
   ByteMatchStatement uses `NONE` transformation, meaning the match is
   case-sensitive raw inspection. An attacker sending `/API/` or `/%61pi/`
   (URL-encoded `a`) would NOT match the allow rule — but also would not be
   blocked by it, falling through to the managed rules. The inconsistency
   means the "allow" is fragile in both directions.

3. **No rate-based rule behind an ALB.** The ACL is attached to an ALB, so
   the source IP is the ALB's IP. Without a rate-based rule, there is zero
   brute-force or volumetric protection. The skill's Step 5 identifies this
   gap and recommends `FORWARDED_IP` with the correct header.

## Slash-command invocation

```
/aws:audit-wafv2-web-acl
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this WAF before we go to production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: wafv2-web-acl-auditor]` and hands off to this
skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit my WAF web acl"
# [Phase: Audit | Skills routed: wafv2-web-acl-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After fixing the shadow rule, verify the managed rule groups now fire on API
traffic:

```bash
# Check that CommonRuleSet metrics show non-zero blocked requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=Rule,Value=AWSManagedRulesCommonRuleSet Name=WebACL,Value=api-gateway-acl \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --profile default
```

Then monitor sampled requests in the WAF console for 48 hours to confirm no
false positives before declaring the ACL production-ready.
