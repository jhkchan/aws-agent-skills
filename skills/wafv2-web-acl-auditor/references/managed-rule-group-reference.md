# Managed Rule Group Reference

This reference catalogs all AWS-managed rule groups available in WAFv2, their
per-group rule compositions, the `RuleActionOverrides` and `ExcludedRules`
syntax, and the CLI commands for logging configuration and Web ACL
association.

## Managed rule group catalog

### Baseline

#### AWSManagedRulesCommonRuleSet
The OWASP Top 10 baseline. **MUST HAVE** — without this group, the WAF has
no baseline content inspection.

Key rules within the group:
- `CrossSiteScripting_BODY` / `_QUERYARGUMENTS` — XSS detection
- `SQLi_BODY` / `_QUERYARGUMENTS` — SQLi detection
- `GenericRFI_BODY` / `_QUERYARGUMENTS` — remote file inclusion
- `GenericLFI_BODY` / `_QUERYARGUMENTS` — local file inclusion
- `RemoteFileInclusion_URIPATH` — RFI via URI
- `DirectoryTransversal_URIPATH` / `_BODY` — path traversal
- `NoUserAgent_HEADER` — blocks requests with no User-Agent
- `UserAgent_BadBots_HEADER` — known bad-bot UA strings
- `SizeRestrictions_QUERYSTRING` / `_BODY` — oversized query/body blocks

Common exclusions:
- `NoUserAgent_HEADER` — health checkers send no User-Agent header
- `SizeRestrictions_BODY` — legitimate large file uploads (> 8 KB body)

### Input validation

#### AWSManagedRulesKnownBadInputsRuleSet
Protects against Log4j (CVE-2021-44228), SSRF, page-preview exploits, and
other known-bad input patterns. **STRONGLY RECOMMENDED** for all internet-
facing applications.

#### AWSManagedRulesSQLiRuleSet
Dedicated SQLi detection patterns complementing the CommonRuleSet. Recommended
for applications with database-backed form inputs or API endpoints.

### OS hardening

#### AWSManagedRulesLinuxRuleSet
Linux-specific shell injection patterns (`/bin/sh`, bash, curl, wget, etc.).

#### AWSManagedRulesUnixRuleSet
POSIX shell and Unix command patterns. Often paired with LinuxRuleSet.

#### AWSManagedRulesWindowsRuleSet
PowerShell (`powershell`, `pwsh`), `cmd.exe`, and Windows-specific injection.

### Reputation

#### AWSManagedRulesAmazonIpReputationList
Blocks IPs associated with botnets and known malicious actors, sourced from
AWS threat intelligence. Low false-positive rate.

#### AWSManagedRulesAnonymousIpList
Blocks Tor exit nodes, proxies, VPNs, and hosting providers. Higher false-
positive rate — legitimate users behind corporate proxies may be blocked.
Use with caution; consider COUNT mode first.

### Application framework

#### AWSManagedRulesWordPressRuleSet
WordPress-specific exploit detection (login brute force, XML-RPC, REST API
abuse). Only relevant if running WordPress.

#### AWSManagedRulesPHPRuleSet
PHP-specific exploit patterns (`eval()`, `base64_decode()`, `exec()`, etc.).
Only relevant if the backend runs PHP.

### Bot / fraud (paid add-ons)

#### AWSBotControlRuleSet
Classifies requests as bot/non-bot with labels: `awswaf:managed:awsbotcontrol:robot`,
`awswaf:managed:awsbotcontrol:category:scanner`, etc. Requires a paid
subscription. Use `LabelMatchStatement` in custom rules to build layered
defense on top of bot classifications.

#### AWSManagedRulesATPRuleSet (Account Takeover Prevention)
Detects credential stuffing, brute force, and anomalous login behavior.
Requires a paid subscription. Recommended for any application with login
endpoints. Configure `LoginPath`, `RequestInspection`, and
`ResponseInspection` to match your authentication flow.

#### AWSManagedRulesACFRuleSet (Account Creation Fraud)
Detects fraudulent account creation patterns. Requires a paid subscription.
For signup/registration flows.

## RuleActionOverrides syntax

To selectively override individual rules within a managed rule group (e.g.,
change one rule from BLOCK to COUNT while leaving the rest in BLOCK mode):

```json
{
  "ManagedRuleGroupStatement": {
    "VendorName": "AWS",
    "Name": "AWSManagedRulesCommonRuleSet",
    "RuleActionOverrides": [
      {
        "Name": "SizeRestrictions_BODY",
        "ActionToUse": { "Count": {} }
      }
    ]
  }
}
```

This is the **targeted** approach — only `SizeRestrictions_BODY` switches to
COUNT; all other rules in the group remain in BLOCK. This is preferred over
`OverrideAction: {Count: {}}` which disables the entire group.

## ExcludedRules syntax

To completely remove a rule from a managed rule group (it will not evaluate
at all):

```json
{
  "ManagedRuleGroupStatement": {
    "VendorName": "AWS",
    "Name": "AWSManagedRulesCommonRuleSet",
    "ExcludedRules": [
      { "Name": "NoUserAgent_HEADER" }
    ]
  }
}
```

## CLI commands

### Enable logging

```bash
# CloudWatch Logs destination
aws wafv2 put-logging-configuration \
  --resource-arn <web-acl-arn> \
  --log-destination-configs arn:aws:logs:<region>:<account>:log-group:<group-name> \
  --profile default

# Kinesis Data Firehose destination (must start with aws-waf-logs-)
aws wafv2 put-logging-configuration \
  --resource-arn <web-acl-arn> \
  --log-destination-configs arn:aws:firehose:<region>:<account>:deliverystream/aws-waf-logs-<name> \
  --profile default
```

### Associate Web ACL with a resource

```bash
# ALB
aws wafv2 associate-web-acl \
  --web-acl-arn <web-acl-arn> \
  --resource-arn <alb-arn> \
  --profile default

# CloudFront (must use CLOUDFRONT scope ACL in us-east-1)
aws wafv2 associate-web-acl \
  --web-acl-arn <web-acl-arn> \
  --resource-arn <cloudfront-distribution-arn> \
  --profile default \
  --region us-east-1
```

### List associated resources

```bash
aws wafv2 list-resources-for-web-acl \
  --web-acl-arn <web-acl-arn> \
  --profile default
```

### Describe Web ACL (for audit input)

```bash
# Regional scope
aws wafv2 describe-web-acl \
  --id <web-acl-id> \
  --scope REGIONAL \
  --output json \
  --profile default

# CloudFront scope (must be us-east-1)
aws wafv2 describe-web-acl \
  --id <web-acl-id> \
  --scope CLOUDFRONT \
  --output json \
  --profile default \
  --region us-east-1
```

### Get logging configuration

```bash
aws wafv2 get-logging-configuration \
  --resource-arn <web-acl-arn> \
  --profile default
```

## Scope rules

| Scope | Region constraint | Protects |
|---|---|---|
| `CLOUDFRONT` | Must be `us-east-1` | CloudFront distributions (global) |
| `REGIONAL` | Any region | ALB, API Gateway, AppSync, Cognito user pools (regional) |

A `CLOUDFRONT` scope ACL created in any region other than `us-east-1` is
invalid. A `REGIONAL` scope ACL cannot protect a CloudFront distribution —
CloudFront requires a `CLOUDFRONT` scope ACL.
