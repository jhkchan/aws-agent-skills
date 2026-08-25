# Advanced Patterns - waf-rule-deployer

## Mindset deep dive: three provisioning misconceptions (moved from SKILL.md)

Three misconceptions dominate WAF rule design at provisioning time:

- **"Custom rules first, managed rules as backstop."** Backwards.
  Managed rule groups (CommonRuleSet, SQLiRuleSet,
  AmazonIpReputationList) are maintained by AWS and cover the OWASP
  Top 10 and emerging threats — they are the foundation (high
  coverage, low effort). Custom rules are for application-specific
  exceptions (allow a known scanner, block a specific geo, rate-limit
  a login endpoint). Managed rules first, custom rules for exceptions.

- **"Rule priority does not matter because WAF evaluates all rules."**
  Priority matters absolutely. WAF evaluates rules in priority order
  (lowest number first). The FIRST rule that matches determines the
  action — subsequent rules are NOT evaluated. If a broad block rule
  (block country X) has priority 0 and a specific allow (allow known
  partner IP in Country X) has priority 1, the partner IP is blocked.
  The specific allow MUST have the lower priority number.

- **"Any Web ACL can protect CloudFront."** Only a CLOUDFRONT-scoped
  Web ACL created in us-east-1 can be associated with a CloudFront
  distribution. A REGIONAL Web ACL (or a CloudFront ACL in any other
  region) CANNOT be associated. This is a hard constraint at
  association time.

## Expert heuristic: managed rules first, custom rules for exceptions (moved from SKILL.md)

A baseline model says "write a custom rule to block SQL injection."
The correct heuristic uses the managed rule group
(AWSManagedRulesSQLiRuleSet) that is continuously updated with new
signatures by AWS, then layers custom rules for exceptions.

```text
Rule priority chain (lowest number = evaluated first):

  Priority 0:  custom allow — known partner IP (specific exception)
  Priority 1:  custom allow — internal health-checker CIDR
  Priority 10: AWSManagedRulesCommonRuleSet (broad coverage)
  Priority 20: AWSManagedRulesSQLiRuleSet (SQLi signatures)
  Priority 30: AWSManagedRulesAmazonIpReputationList (known bad IPs)
  Priority 40: custom block — geo-match country X
  Priority 50: custom rate-based — 100 req / 5 min on /login
  Default action: ALLOW (or BLOCK, depending on posture)

Why this order:
  1. Specific allows (0, 1) evaluated FIRST so known-good traffic
     is never accidentally blocked by a downstream rule.
  2. Managed rule groups (10-30) provide broad threat coverage.
  3. Custom blocks (40) are application-specific.
  4. Rate-based (50) catches volume attacks.
  5. Default action applies if no rule matches.
```

**Key implication:** the specific-allow-before-broad-block pattern is
the #1 design principle. If a partner IP is in a blocked country, the
allow rule MUST be evaluated before the geo-block rule.

## Expert heuristic: WCU budget planning detail (moved from SKILL.md)

Every rule and rule group consumes WCU. Default limit is 1500 per
ACL. Exceeding causes create/update to fail with
`WAFInvalidParameterException`.

```text
Typical WCU costs (approximate, verify in AWS docs):
  AWSManagedRulesCommonRuleSet          ~700
  AWSManagedRulesSQLiRuleSet            ~200
  AWSManagedRulesAmazonIpReputationList ~20
  AWSManagedRulesLinuxRuleSet           ~200
  AWSManagedRulesWindowsRuleSet         ~200
  AWSManagedRulesBotControlRuleSet      ~50
  AWSManagedRulesATPRuleSet             ~50
  Custom byte-match (single condition)  1
  Custom geo-match                      3
  Custom IP set match                   1
  Custom regex pattern set match        25
  Custom rate-based                     1 + base rule cost

Example budget:
  CommonRuleSet(700) + SQLi(200) + IPReputation(20) + BotControl(50)
  + ATP(50) = 1020 WCU (managed)
  + 5 custom rules (~5 each) = 25 WCU (custom)
  = ~1045 WCU total (under 1500 limit, 455 headroom)
  Adding LinuxRuleSet(200) + WindowsRuleSet(200):
    1045 + 400 = 1445 WCU → only 55 WCU headroom.
    → Offload to a referenced rule group (1500 WCU separate budget).
```

**Key implication:** the 1500 WCU limit is hit faster than expected
when stacking managed rule groups. Use a referenced rule group to
offload capacity. Request a limit increase via Support for >1500.

## Expert heuristic: CloudFront ACL scope flows (moved from SKILL.md)

A CloudFront-scoped Web ACL MUST be created in us-east-1. A Regional
ACL cannot protect a CloudFront distribution, regardless of region.

```text
CloudFront protection flow:
  1. Create Web ACL --scope CLOUDFRONT --region us-east-1
  2. Add managed + custom rules (all resources in us-east-1)
  3. Create IP sets and regex sets in us-east-1
  4. Associate with distribution:
     aws wafv2 associate-web-acl \
       --web-acl-arn arn:aws:wafv2:us-east-1:...:global-webacl/... \
       --resource-arn arn:aws:cloudfront::...:distribution/...

Regional protection flow (ALB, API Gateway, AppSync):
  1. Create Web ACL --scope REGIONAL --region <any>
  2. Add rules; associate with the regional resource ARN
```
