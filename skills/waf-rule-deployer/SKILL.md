---
name: waf-rule-deployer
description: >-
  Provisions AWS WAFv2 rule sets with production defaults: Web ACL
  creation (CloudFront scope in us-east-1 vs Regional scope), rule
  groups (managed vs custom) with capacity planning in WCU (Web ACL
  Capacity Units, 1500 default per ACL), managed rule groups
  (AWSManagedRulesCommonRuleSet, AWSManagedRulesSQLiRuleSet,
  AWSManagedRulesAmazonIpReputationList, AWSManagedRulesLinuxRuleSet,
  AWSManagedRulesWindowsRuleSet, AWSManagedRulesUnixRuleSet),
  custom rules (byte-match, regex pattern set, geo-match,
  rate-based), IP set and regex pattern set resources, rule priority
  ordering (lowest number evaluated first), action types (allow,
  block, count, CAPTCHA, Challenge), bot control managed rule group,
  account takeover prevention (ATP), label matching for rule
  chaining, logging configuration via Kinesis Firehose to S3, and
  CloudFront distribution association. Emits a READY_TO_DEPLOY
  checklist with verification commands. Use when creating a WAF rule
  set, attaching managed rule groups to a Web ACL, writing custom
  byte-match or geo-match rules, configuring rate-based rules,
  planning WCU budget, configuring WAF logging to S3 via Firehose,
  associating a Web ACL with a CloudFront distribution, or chaining
  rules with labels. Triggers: create WAF rule, WAF managed rule
  group, WAF custom rule, WAF byte match, WAF geo match, WAF rate
  based rule, WAF IP set, WAF regex pattern set, WAF WCU budget,
  WAF CloudFront ACL, WAF logging Kinesis Firehose, WAF bot control,
  WAF ATP, WAF label matching, WAF Challenge action, WAF CAPTCHA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with wafv2,
  cloudfront, firehose, s3, iam, and logs access. CloudFront-scoped
  Web ACLs must be created in us-east-1. Works with Terraform
  aws_wafv2_web_acl / aws_wafv2_rule_group / aws_wafv2_ip_set /
  aws_wafv2_regex_pattern_set resources and CloudFormation
  AWS::WAFv2::WebACL / AWS::WAFv2::RuleGroup templates.
keywords:
  - aws
  - waf
  - wafv2
  - web acl
  - rule group
  - managed rules
  - custom rules
  - cloudops
  - deploy
  - provisioning
  - security
  - byte match
  - geo match
  - rate based
  - ip set
  - regex pattern set
  - wcu
  - bot control
  - atp
  - captcha
  - challenge
  - cloudfront
  - label matching
  - kinesis firehose
tags:
  - aws
  - waf
  - wafv2
  - security
  - cloudops
  - deploy
  - rule-group
  - managed-rules
  - custom-rules
  - cloudfront
  - rate-based
  - bot-control
  - atp
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - waf
    - wafv2
    - security
    - cloudops
    - deploy
    - rule-group
    - managed-rules
    - custom-rules
    - cloudfront
    - rate-based
    - bot-control
    - atp
  dependencies:
    - aws-orchestrator
  keywords:
    - create waf rule
    - waf managed rule group
    - waf custom rule
    - waf byte match
    - waf geo match
    - waf rate based rule
    - waf ip set
    - waf regex pattern set
    - waf wcu budget
    - waf cloudfront acl
    - waf logging kinesis firehose
    - waf bot control
    - waf atp
    - waf label matching
    - waf challenge action
    - waf captcha
  when_to_use: >-
    Invoke when the user wants to create a WAFv2 Web ACL with managed
    and custom rules, attach managed rule groups (CommonRuleSet,
    SQLiRuleSet, AmazonIpReputationList), write custom byte-match or
    geo-match or rate-based rules, plan WCU capacity budget, configure
    WAF logging to S3 via Kinesis Firehose, associate a Web ACL with a
    CloudFront distribution (must be in us-east-1), or chain rules
    using labels. Do NOT invoke for AWS Shield Advanced (use shield
    skills), AWS Firewall Manager (use firewall-manager skills), or
    for auditing an existing Web ACL (use wafv2-web-acl-auditor).
---

# WAF Rule Deployer

An AWS CloudOps agent skill that provisions AWS WAFv2 rule sets with
correct defaults. The skill walks the operator through scope
selection (CloudFront vs Regional), managed rule group selection,
custom rule authoring, WCU budget planning, rule priority ordering,
action selection, label-based rule chaining, logging configuration,
and resource association, captures requirements, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create WAF rule, WAF managed rule group, WAF custom rule, WAF byte
match, WAF geo match, WAF rate based rule, WAF IP set, WAF regex
pattern set, WAF WCU budget, WAF CloudFront ACL, WAF logging Kinesis
Firehose, WAF bot control, WAF ATP, WAF label matching, WAF Challenge
action, WAF CAPTCHA.

## STRICT output contract

When this skill is invoked with a WAF-rule-provisioning request
(create a Web ACL, attach managed rules, write custom rules, plan WCU
budget, configure logging, associate with CloudFront, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `WAF_RULE_SET:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Scope selection (CloudFront vs Regional) | ACL scope decision |
| Step 2 — Managed rule groups (high coverage first) | Managed rules |
| Step 3 — Custom rules (exceptions and specifics) | Custom rules |
| Step 4 — WCU budget planning (1500 default) | Capacity planning |
| Step 5 — Rule priority ordering | Evaluation order |
| Step 6 — Action types (allow, block, count, CAPTCHA, Challenge) | Action semantics |
| Step 7 — IP set and regex pattern set | Reusable match sets |
| Step 8 — Rate-based rules | Traffic volume controls |
| Step 9 — Bot control and ATP | Managed add-ons |
| Step 10 — Label matching and rule chaining | Rule chaining |
| Step 11 — Logging configuration (Firehose to S3) | Observability |
| Step 12 — CloudFront association | CDN attachment |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/managed-rules-and-wcu.md | Managed rules + WCU detail |
| references/custom-rules-and-labels.md | Custom rule + label detail |

## Mindset

**One-line takeaway:** Start with managed rule groups for broad
coverage (maintained by AWS threat intelligence), then add custom
rules for exceptions — the specific allow rule MUST have a lower
priority number than the broad block rule so the exception is
evaluated first. CloudFront-scoped Web ACLs MUST be created in
us-east-1. The WCU budget per Web ACL defaults to 1500; exceeding
it causes create/update to fail.

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

## Configuration dependency graph (novel heuristic)

WAF rule configurations are NOT independent. The ACL scope determines
the region (us-east-1 for CloudFront). Managed rule groups consume
WCUs against the ACL budget. IP sets and regex sets must exist before
custom rules reference them. Labels emitted by one rule must exist
before a downstream rule matches on them. Logging requires a Firehose
stream before it can be attached.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Web ACL (scope + region) | CloudFront scope MUST be us-east-1 | scope CANNOT be changed after creation — must delete and recreate | container for all rules |
| Managed rule group | Web ACL exists; vendor/name correct | pinned version stops threat-intel updates; default is latest | broad threat coverage |
| Custom rule (byte/geo/IP) | Web ACL exists; referenced IP/regex set already created | priority MUST be unique within the ACL | application-specific allow/block |
| Rate-based rule | Web ACL exists; aggregate key chosen | evaluated per 5-min window; too-low limit blocks legitimate bursts | volume-based protection |
| IP set / regex set | Same scope and region as referencing ACL | cross-scope/region references fail at rule evaluation | reusable match criteria |
| Label (chaining) | Upstream rule with RuleLabels must exist and match first | label visible only to rules with higher priority number | multi-stage rule logic |
| Logging (Firehose→S3) | Firehose stream exists in same region as ACL; name starts with `aws-waf-logs-` | cannot enable logging if already enabled; must disable first | request logging |
| CloudFront association | Web ACL scope=CLOUDFRONT; region=us-east-1; distribution exists | association deploys globally in ~1 min | edge protection |

**The priority-ordering row is the one a baseline model misses.**
WAF evaluates rules in priority order and stops at the first match.
A specific allow rule MUST have a lower priority number than a broad
block rule. The procedure below forces an explicit priority
assignment for every rule.

## Expert heuristic: managed rules first, custom rules for exceptions

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

## Expert heuristic: WCU budget planning (1500 default)

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

## Expert heuristic: CloudFront ACL must be in us-east-1

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

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| ACL scope decided (CLOUDFRONT vs REGIONAL) | CloudFront scope MUST be us-east-1; scope immutable after creation | Confirm the resource to protect |
| Region correct for scope | CloudFront scope → us-east-1; Regional → resource region | `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` |
| WCU budget planned | Exceeding 1500 WCU causes failure | Sum managed group WCUs + custom rule WCUs |
| Managed rule group names verified | Wrong vendor/name causes create failure | `aws wafv2 list-managed-rule-groups --region us-east-1` |
| IP set / regex set exist (if referenced) | Custom rules referencing non-existent sets fail | `aws wafv2 list-ip-sets --scope <scope> --region <region>` |
| Firehose stream exists (if logging) | Logging requires existing Firehose stream named `aws-waf-logs-*` | `aws firehose describe-delivery-stream --delivery-stream-name <name>` |
| CloudFront distribution ARN (if CloudFront) | Association requires the distribution ARN | `aws cloudfront list-distributions` |
| Default action decided | Action when no rule matches (ALLOW=fail-open; BLOCK=fail-closed) | Assess security posture |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Scope selection (CloudFront vs Regional)

| Feature | CLOUDFRONT scope | REGIONAL scope |
|---|---|---|
| Region | MUST be us-east-1 | Any region |
| Protects | CloudFront distributions | ALB, API Gateway, AppSync, Cognito, App Runner |
| IP set / regex set region | us-east-1 | Same region as the ACL |
| Web ACL ARN format | `...:global-webacl/...` | `...:regional/webacl/...` |

## Step 2 — Managed rule groups (high coverage first)

Managed rule groups are maintained by AWS and provide broad threat
coverage. They are the foundation of the rule set.

| Managed rule group | Coverage | Approx WCU |
|---|---|---|
| AWSManagedRulesCommonRuleSet | OWASP Top 10 (SQLi, XSS, LFI, RFI, admin paths) | ~700 |
| AWSManagedRulesSQLiRuleSet | SQL injection signatures | ~200 |
| AWSManagedRulesAmazonIpReputationList | Known malicious IPs (botnets, spammers) | ~20 |
| AWSManagedRulesLinuxRuleSet | Linux-specific exploits (LFI, shell injection) | ~200 |
| AWSManagedRulesWindowsRuleSet | Windows-specific exploits (PowerShell, RCE) | ~200 |
| AWSManagedRulesUnixRuleSet | Unix/Linux LFI, shell escape | ~200 |
| AWSManagedRulesBotControlRuleSet | Bot detection (paid add-on) | ~50 |
| AWSManagedRulesATPRuleSet | Account takeover prevention (paid add-on) | ~50 |
| AWSManagedRulesACFPRuleSet | Account creation fraud prevention (paid add-on) | ~50 |

**Version strategy:** default (latest) auto-updates threat signatures
— best for new deployments. Pinned (e.g., `Version_2.1`) is stable
— best for production predictability; review and upgrade quarterly.

## Step 3 — Custom rules (exceptions and specifics)

Custom rules handle application-specific logic using statement types:

| Statement type | Use case | Example |
|---|---|---|
| ByteMatchStatement | Match string in headers/URI/query/body | Block `User-Agent: BadBot` |
| GeoMatchStatement | Allow/block by country (ISO 3166-1 alpha-2) | Block traffic from `RU, KP` |
| IPSetReferenceStatement | Match against reusable IP set | Allow corporate CIDR range |
| RegexPatternSetReferenceStatement | Match against reusable regex set | Block SQLi regex patterns |
| SizeConstraintStatement | Match by request component size | Block bodies > 8192 bytes |
| RateBasedStatement | Match when key exceeds N req/5 min | Block 100 req/5min on `/login` |
| NotStatement | Negate another statement | Allow everything NOT from country X |
| OrStatement / AndStatement | Combine statements | Block if geo=X AND header=`BadBot` |

**Specific allow before broad block:**

```text
Custom rule: allow-known-partner
  Priority: 0, Action: ALLOW
  Statement: IPSetMatch(ip-set-partner-cidrs)
  → Evaluates first; known partner IPs bypass all other rules.

Custom rule: block-high-risk-geo
  Priority: 40, Action: BLOCK
  Statement: GeoMatch(RU, KP)
  → A partner IP in a blocked geo is ALLOWED (priority 0 wins).
```

## Step 4 — WCU budget planning (1500 default)

```bash
# Check current WCU usage
aws wafv2 describe-web-acl \
  --scope CLOUDFRONT --region us-east-1 \
  --id <acl-id> \
  --query 'WebACL.Capacity' --output text
```

**Offload WCU to a rule group** (up to 1500 WCU separately):

```bash
aws wafv2 create-rule-group \
  --scope CLOUDFRONT --region us-east-1 \
  --name "custom-exceptions" --capacity 1500 \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName='custom-exceptions'
# Reference it in the Web ACL via RuleGroupReferenceStatement (1 WCU)
```

## Step 5 — Rule priority ordering

WAF evaluates rules in priority order (lowest number first). The
first matching rule determines the action. Subsequent rules are NOT
evaluated.

```text
Priority assignment best practice:
  0     — Specific allows (partner IPs, health checkers)
  1-9   — Reserved for future specific allows
  10-99 — Managed rule groups (broad coverage)
  100+  — Custom blocks (geo, header, body)
  1000+ — Rate-based rules
  Default action — ALLOW or BLOCK (applies if no rule matches)
```

Priority MUST be unique within the ACL. Duplicates cause
`update-web-acl` to fail.

## Step 6 — Action types (allow, block, count, CAPTCHA, Challenge)

| Action | Behavior | Use case |
|---|---|---|
| ALLOW | Passes to the protected resource | Known-good traffic |
| BLOCK | Dropped with HTTP 403 | Known-bad traffic |
| COUNT | Passes but counted in metrics | Testing a rule before BLOCK (dry run) |
| CAPTCHA | Requires solving a CAPTCHA | Bot mitigation on forms/login |
| Challenge | Silent browser-side token (no puzzle) | Bot mitigation on general traffic |

**COUNT for safe rollout:** set new rules to COUNT first. Monitor
metrics. If count is low, switch to BLOCK. If high, investigate
false positives.

## Step 7 — IP set and regex pattern set

Reusable resources referenced by custom rules. Must be in the SAME
scope and region as the Web ACL.

```bash
# Create an IP set
IP_SET_ARN=$(aws wafv2 create-ip-set \
  --scope CLOUDFRONT --region us-east-1 \
  --name "partner-cidrs" \
  --addresses "203.0.113.0/24" "198.51.100.10/32" \
  --ip-address-version IPV4 \
  --query 'Summary.IPSetARN' --output text)

# Create a regex pattern set
REGEX_SET_ARN=$(aws wafv2 create-regex-pattern-set \
  --scope CLOUDFRONT --region us-east-1 \
  --name "sqli-patterns" \
  --regular-expression-list "(?i)(union.*select)" "(?i)(drop.*table)" \
  --query 'Summary.RegexPatternSetARN' --output text)
```

**Constraint:** an IP set in us-east-1 CANNOT be referenced by a
Regional ACL in us-west-2. Scope and region must match.

## Step 8 — Rate-based rules

Rate-based rules limit requests from a single key in a 5-minute window.

```text
RateBasedStatement:
  Limit: 100              # max requests per 5-min window
  AggregateKeyType: IP    # IP | FORWARDED_IP | CUSTOM | CONSTANT
  EvaluationWindowSec: 300 # fixed at 300 (5 min); not configurable
  ForwardedIPConfig:      # required if FORWARDED_IP
    HeaderName: X-Forwarded-For
    FallbackBehavior: MATCH | NO_MATCH
```

**Use cases:** login endpoint (100/5min per IP), API abuse (1000/5min
per IP), scraping prevention (500/5min per IP).

**Forwarded IP caveat:** behind a proxy/CDN, use `FORWARDED_IP` with
`X-Forwarded-For` to rate-limit the original client IP, not the proxy.

## Step 9 — Bot control and ATP

**Bot Control** (`AWSManagedRulesBotControlRuleSet`, paid) classifies
requests as bot or browser. Useful for detecting scrapers, crawlers,
and automated tools.

**ATP** (`AWSManagedRulesATPRuleSet`, paid) checks login attempts
against known compromised credentials and applies CAPTCHA/Challenge to
suspicious logins. Requires:
- `LoginPath`: the login endpoint (e.g., `/login`)
- `PayloadType`: JSON or FORM_ENCODED
- `UsernameField` / `PasswordField`: field names
- `ResponseInspection` (optional): inspect response to detect failed
  logins

## Step 10 — Label matching and rule chaining

Labels allow rules to communicate. A rule with `RuleLabels` adds a
label to request metadata. A downstream rule matches via
`LabelMatchStatement`.

```text
Rule: detect-suspicious-header (priority 10)
  Action: COUNT   # tag the request, do not block yet
  RuleLabels:
    - Name: suspicious-header-detected

Rule: block-if-suspicious-and-geo (priority 20)
  Action: BLOCK
  Statement: And(
    LabelMatch("suspicious-header-detected"),
    GeoMatch(RU, KP)
  )
  → Blocks only if BOTH conditions are true.
```

**Constraint:** labels are case-insensitive and auto-prefixed with
`awswaf:`. A label emitted at priority 10 is visible only to rules
with priority > 10.

## Step 11 — Logging configuration (Firehose to S3)

WAF logs contain request details (timestamp, client IP, matched rules,
action, labels). Requires a Kinesis Firehose stream as destination;
Firehose writes to S3.

**Prerequisites:** Firehose stream in the SAME region as the Web ACL;
stream name MUST start with `aws-waf-logs-`; S3 bucket exists.

```bash
# Create the Firehose stream (if needed)
aws firehose create-delivery-stream \
  --delivery-stream-name aws-waf-logs-production \
  --s3-destination-configuration \
    RoleARN=arn:aws:iam::<acct>:role/firehose-waf-role,\
    BucketARN=arn:aws:s3:::waf-logs-bucket \
  --region us-east-1

# Enable logging
aws wafv2 put-logging-configuration \
  --web-acl-arn <web-acl-arn> \
  --logging-configuration \
    LogDestinationConfigs=arn:aws:firehose:us-east-1:<acct>:deliverystream/aws-waf-logs-production \
  --region us-east-1
```

**RedactedFields:** omit sensitive fields (e.g., `Authorization`
header, `password` parameter) via the `RedactedFields` config.

## Step 12 — CloudFront distribution association

```bash
aws wafv2 associate-web-acl \
  --web-acl-arn <web-acl-arn> \
  --resource-arn arn:aws:cloudfront::<acct>:distribution/E1234567890 \
  --region us-east-1

# Verify
aws wafv2 get-web-acl-for-resource \
  --resource-arn arn:aws:cloudfront::<acct>:distribution/E1234567890 \
  --region us-east-1 \
  --query 'WebACL.WebACLArn' --output text
```

Association takes ~1 minute to propagate to all edge locations.

## NEVER do these things

1. **NEVER create a CloudFront-scoped Web ACL outside us-east-1.**
   CloudFront scope requires us-east-1. Any other region causes
   association to fail.

2. **NEVER put a broad block rule before a specific allow rule.**
   WAF evaluates in priority order and stops at the first match. The
   specific allow MUST have a lower priority number.

3. **NEVER exceed the 1500 WCU budget without planning.** Exceeding
   causes create/update to fail. Sum managed + custom WCUs; offload
   to a referenced rule group if needed.

4. **NEVER reference an IP set or regex set from a different scope
   or region.** They must be in the SAME scope and region as the ACL.

5. **NEVER use the BLOCK action for a new rule without testing with
   COUNT first.** Always test with COUNT, monitor metrics, verify no
   false positives, then switch to BLOCK.

6. **NEVER forget the Firehose stream naming prefix.** The Firehose
   stream for WAF logging MUST start with `aws-waf-logs-`.

7. **NEVER assume pinned managed rule group versions auto-update.**
   Pinning stops threat-intel updates. Review pinned versions
   quarterly and upgrade.

8. **NEVER change the Web ACL scope after creation.** Scope is
   immutable. To switch scopes, delete and recreate (re-adding all
   rules).

9. **NEVER use duplicate rule priorities.** Priorities must be unique
   within the ACL. Duplicates cause `update-web-acl` to fail.

10. **NEVER rate-limit on source IP behind a proxy/CDN without
    FORWARDED_IP.** All clients share one rate bucket. Use
    `FORWARDED_IP` with `X-Forwarded-For`.

## Output format

```text
WAF_RULE_SET: <acl-name> (<scope>, <region>) — <wcu-used>/<wcu-limit> WCU
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Scope: CLOUDFRONT (us-east-1) | REGIONAL (<region>)
  [✓|✗] Default action: ALLOW | BLOCK
  [✓|✗] Managed rule group: <vendor/name> (version <v>) — priority <n> — <wcu> WCU
  [✓|✗] Custom rule: <rule-name> — priority <n> — action <ALLOW|BLOCK|COUNT|CAPTCHA|Challenge> — <statement> — <wcu> WCU
  [✓|✗] Rate-based rule: <rule-name> — limit <n>/5min per <key>
  [✓|✗] IP set: <name> (<scope>, <region>) — <n> addresses
  [✓|✗] Regex pattern set: <name> (<scope>, <region>) — <n> patterns
  [✓|✗] WCU budget: <used> / <limit> (<headroom> WCU remaining)
  [✓|✗] Priority order: specific-allow (<n>) before broad-block (<n>) — VERIFIED
  [✓|✗] Bot control: enabled | disabled
  [✓|✗] ATP: enabled (login-path <path>) | disabled
  [✓|✗] Labels: <label-name> (priority <n>) → <downstream-rule> (priority <n>)
  [✓|✗] Logging: Firehose <stream-name> → S3 <bucket> (redacted fields: <list>)
  [✓|✗] CloudFront association: <distribution-arn> | N/A (regional)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws wafv2 get-web-acl --scope <scope> --id <acl-id> --region <region>
  aws wafv2 list-rule-groups --scope <scope> --region <region>
  aws wafv2 get-logging-configuration --web-acl-arn <arn> --region <region>
```

### Worked example — CloudFront Web ACL with managed rules and custom allow

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
  [✓] Logging: Firehose aws-waf-logs-production → S3 waf-logs-bucket (redacted: Authorization header)
  [✓] CloudFront association: arn:aws:cloudfront::123456789012:distribution/E1234567890
  [✓] Tags: Environment=production, Protected=cloudfront
VERIFICATION_COMMANDS:
  aws wafv2 get-web-acl --scope CLOUDFRONT --id <acl-id> --region us-east-1
  aws wafv2 get-logging-configuration --web-acl-arn <arn> --region us-east-1
  aws cloudfront get-distribution-config --id E1234567890
```

## Error handling

### WAFInvalidParameterException: WCU limit exceeded
- Total WCU exceeds 1500. Offload to a referenced rule group, remove
  low-value managed groups, or request a limit increase via Support.

### Association fails for CloudFront distribution
- ACL scope is not CLOUDFRONT, or ACL is not in us-east-1. Scope and
  region are immutable; recreate with `--scope CLOUDFRONT --region
  us-east-1`.

### put-logging-configuration fails
- Firehose stream name does not start with `aws-waf-logs-`. Rename
  or recreate with the required prefix. Verify the stream is in the
  same region as the ACL.

### Custom rule referencing IP set fails
- IP set is in a different scope or region. Recreate in the same
  scope and region.

### Rate-based rule not triggering
- Rate window is fixed at 5 minutes. Verify the limit is not too
  high for the traffic volume. Behind a proxy, switch to
  `FORWARDED_IP` with `X-Forwarded-For`.

### Managed rule group pinned, no new signatures
- Pinned versions do not receive updates. Use
  `describe-managed-rule-group` to see available versions and
  upgrade quarterly.

## Domain

AWS CloudOps / AWS WAFv2 Web ACL Rule Set Provisioning & Application
Layer Security.

## AWS documentation

- **WAF Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **Managed rule groups list** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-list.html
- **Web ACL creation** — https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-create.html
- **Custom rules** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-custom-rules.html
- **Rate-based rules** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-rate-based-rules.html
- **WCU and capacity** — https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html
- **Logging** — https://docs.aws.amazon.com/waf/latest/developerguide/logging.html
- **CloudFront features** — https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-features.html
- **Bot Control** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-bot.html
- **ATP** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html
- **Labels and chaining** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-conditions.html
- **CAPTCHA and Challenge** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-and-challenge.html
