---
name: wafv2-web-acl-deployer
description: 'Provisions AWS WAFv2 Web ACLs with correct production defaults: scope selection (CLOUDFRONT vs REGIONAL), managed rule groups (AWSManagedRulesCommonRuleSet, SQLiRuleSet, LinuxRuleSet, WindowsRuleSet, IPReputationList, BotControlRuleSet, AmazonIpReputationList, ATP), custom rules (byte match, IP set, regex pattern, geo match, size constraint, rate-based), rule priority ordering, logging destinations (Kinesis Firehose, CloudWatch Logs, S3), resource association (ALB, API Gateway, CloudFront), rate-based rules with aggregate keys (IP, forwarded IP), Challenge and CAPTCHA actions, and account takeover prevention. Emits a READY_TO_DEPLOY checklist. Use when creating a Web ACL, attaching managed rules, configuring rate limiting, enabling WAF logging, associating a Web ACL with an ALB/API Gateway/CloudFront, or configuring CAPTCHA/Challenge actions. Triggers: create WAF Web ACL, WAFv2, managed rule groups, WAF rate limiting, WAF logging, WAF CAPTCHA, WAF Challenge action, bot control, ATP managed rules.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with wafv2, cloudfront, elasticloadbalancingv2, apigateway, firehose, logs, and s3 access. Works with Terraform aws_wafv2_web_acl / aws_wafv2_web_acl_association resources, CloudFormation AWS::WAFv2::WebACL / AWS::WAFv2::WebACLAssociation, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, waf, wafv2, security, cloudops, deploy, web-acl, managed-rules, rate-limiting
  dependencies: aws-orchestrator
  keywords: aws, waf, wafv2, security, cloudops, deploy, provisioning, web-acl, managed-rules, rate-limiting, bot-control, captcha, challenge, atp, cloudfront, regional
  when_to_use: Invoke when the user wants to create a new WAFv2 Web ACL, attach AWS managed rule groups, configure custom rules (byte match, IP set, regex, geo, size, rate-based), enable WAF logging to Kinesis Firehose / CloudWatch Logs / S3, associate a Web ACL with an ALB / API Gateway / CloudFront distribution, or configure CAPTCHA / Challenge actions for bot defense. Do NOT invoke for AWS WAF Classic (waf-regional / waf) — only WAFv2. For Shield Advanced protections, use the shield-advanced skill.
---

# WAFv2 Web ACL Deployer

An AWS CloudOps agent skill that provisions AWS WAFv2 Web ACLs
with correct production defaults. The skill walks the operator
through a 9-step provisioning procedure, explains why each
default matters, and emits a READY_TO_DEPLOY checklist verifying
every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Choosing scope, rules, actions | "Expert heuristic" |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Managed rules, logging, ATP, CAPTCHA | `references/managed-rules-and-logging-guide.md` |

## Activation keywords

create WAF Web ACL, WAFv2 Web ACL, managed rule groups,
AWSManagedRulesCommonRuleSet, SQLiRuleSet, LinuxRuleSet,
WindowsRuleSet, IPReputationList, BotControlRuleSet,
AmazonIpReputationList, ATP rule groups, account takeover
prevention, WAF rate-based rule, WAF rate limiting,
WAF logging, Kinesis Firehose WAF, CloudWatch Logs WAF,
S3 WAF logging, WAF CAPTCHA action, WAF Challenge action,
WAF custom rules, WAF IP set, WAF regex pattern set,
WAF geo match, WAF byte match, WAF size constraint,
CLOUDFRONT scope, REGIONAL scope, ALB WAF association,
API Gateway WAF, CloudFront WAF.

## STRICT output contract

When this skill is invoked with a WAFv2 Web ACL provisioning
request (Web ACL name, scope, rule groups, or a partial existing
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in "Output format" using the literal all-caps
labels `ACL:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of
the response.

### Required output structure

1. `ACL: <web-acl-name>` — the Web ACL being provisioned.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING` —
   nothing else.
3. `CHECKLIST:` followed by indented lines, each prefixed with a
   status marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws wafv2 ...`
   commands the operator can run.

### 6 FORBIDDEN output patterns (each silently breaks automation)

1. **FORBIDDEN — prose preamble before `ACL:`.** The first
   non-empty line MUST be `ACL:`. No "Here is your checklist…".
2. **FORBIDDEN — markdown variants of the labels.** Write
   `VERDICT:`, not `**VERDICT:**`, `### Verdict`, `Verdict =`, or
   `\`VERDICT\``. The labels are case-sensitive all-caps keywords.
3. **FORBIDDEN — swapping verdict tokens.** The verdict is exactly
   `READY_TO_DEPLOY` or `PREREQUISITES_MISSING` — not "ready",
   "missing", "BLOCKED", "OK", or "needs review".
4. **FORBIDDEN — omitting `VERIFICATION_COMMANDS:`.** Even when
   the verdict is `PREREQUISITES_MISSING`, include the commands
   the operator needs to verify the gaps.
5. **FORBIDDEN — extra sections after `VERIFICATION_COMMANDS:`.**
   The checklist block is the entire response. Put deeper
   explanation in `references/` files, not after the block.
6. **FORBIDDEN — status marker drift.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`,
   `[WARN]`, or emoji markers.

### Perfect example (copy the shape exactly)

```text
ACL: payments-api-waf
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Scope — REGIONAL (us-east-1)
  [✓]      Default action — Allow
  [✓]      Managed rules — AWSManagedRulesCommonRuleSet (priority 10), AWSManagedRulesSQLiRuleSet (priority 20)
  [✓]      Custom rule — block IP set 10.0.0.0/8 (priority 1, ByteMatch + IPSet)
  [✓]      Rate-based rule — 2000 req / 5 min, aggregate on IP (priority 5)
  [✓]      Visibility config — CloudWatch metrics enabled, sampled requests enabled
  [✓]      Logging — Kinesis Firehose delivery stream aws-waf-logs-payments
  [✓]      Association — arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-alb/50dc6c495c0c9188
  [✓]      Tags — Environment=production, Application=payments
  [OPTIONAL] CAPTCHA / Challenge — none for this workload
  [OPTIONAL] Bot Control — not enabled (enable for public-facing forms)
VERIFICATION_COMMANDS:
  aws wafv2 list-web-acls --scope REGIONAL --region us-east-1
  aws wafv2 get-web-acl --scope REGIONAL --id <web-acl-id> --region us-east-1
  aws wafv2 list-resources-for-web-acl --web-acl-arn <web-acl-arn> --region us-east-1
  aws wafv2 get-logging-configuration --web-acl-arn <web-acl-arn> --region us-east-1
```

## Reasoning framework (why the provisioning order matters)

WAFv2 provisioning has **scope, dependency, and ordering
constraints** that make the procedure non-trivial:

1. **Scope FIRST — CLOUDFRONT vs REGIONAL is immutable.** A
   CLOUDFRONT-scope Web ACL lives in us-east-1 and attaches only
   to CloudFront distributions. A REGIONAL-scope Web ACL lives in
   a specific Region and attaches to ALBs, API Gateway REST/HTTP
   APIs, AppSync GraphQL APIs, Cognito user pools, and App Runner.
   The scope CANNOT be changed after creation — you must delete
   and recreate.

2. **Default action — Allow vs Block.** The default action applies
   to any request that does not match a rule with a terminating
   action. `Allow` is the common default (rules block threats);
   `Block` is used for allow-list patterns (rules allow known-good).

3. **Rule priority — lower numbers evaluate first.** WAF evaluates
   rules in priority order (0 is highest). The first rule that
   matches a request with a terminating action (Allow, Block,
   CAPTCHA, Challenge) wins. Gaps in priority numbering let you
   insert rules later without renumbering.

4. **Allow-list rules BEFORE managed rule groups.** Put explicit
   allows (partner IPs, known-good paths) at the highest priority
   (lowest numbers) so they win over managed rule blocks. Place
   workload-specific blocks (geo, size) after managed rules so
   managed rules catch generic threats first.

5. **Rate-based rules — aggregate key choice matters.** A
   rate-based rule counts requests per aggregate key value over a
   5-minute window. Use `IP` for direct connections and
   `FORWARDED_IP` (reads `X-Forwarded-For`) when behind a CDN, ALB,
   or proxy. Mis-choosing the key rate-limits the CDN node, not
   the client.

6. **Logging — destination must exist before WAF can write.** The
   Firehose delivery stream, CloudWatch Logs log group, or S3
   bucket MUST exist and have a service principal policy permitting
   `delivery.logs.amazonaws.com`. WAF silently drops logs if the
   destination is missing or the policy is wrong.

7. **CAPTCHA and Challenge — non-terminating bot defense actions.**
   `CAPTCHA` requires the client to solve a CAPTCHA token;
   `Challenge` runs a silent browser challenge. Both issue tokens
   valid for ~300 seconds. ATP (Account Takeover Prevention) is a
   managed rule group requiring a per-Region ARN and exact login
   path configuration.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Scope decision** | Immutable after creation. CLOUDFRONT = us-east-1 + CloudFront only. REGIONAL = one Region + ALB/API Gateway/AppSync/Cognito/App Runner. | Confirm target resource type |
| **Target resource ARN** | The Web ACL must attach to an existing resource (CloudFront dist, ALB ARN, API Gateway stage ARN, AppSync API ARN, Cognito pool ARN, App Runner ARN). | `aws elbv2 describe-load-balancers` / `aws apigateway get-rest-apis` / `aws cloudfront get-distribution` |
| **Logging destination** | Firehose stream name, CloudWatch log group ARN, or S3 bucket ARN. The destination's resource policy MUST allow `delivery.logs.amazonaws.com`. | `aws firehose describe-delivery-stream` / `aws logs describe-log-groups` / `aws s3api get-bucket-policy` |
| **IP set / regex pattern set** | Custom rules referencing these by ARN require they exist BEFORE the Web ACL is created (ARN is validated at creation). | `aws wafv2 list-ip-sets --scope <scope> --region <region>` |
| **Managed rule group availability** | ATP and Bot Control are subscription-managed. The account must subscribe via Marketplace before referencing them. | `aws wafv2 list-available-managed-rule-groups --scope <scope>` |
| **IAM permissions** | Caller needs `wafv2:CreateWebACL`, `wafv2:AssociateWebACL`, `wafv2:PutLoggingConfiguration`, plus resource-specific (`elasticloadbalancing:SetWebACL`, `apigateway:SetWebACL`, `cloudfront:UpdateDistribution`). | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Scope selection (CLOUDFRONT vs REGIONAL)

| Scope | Region | Target resources | Notes |
|---|---|---|---|
| `CLOUDFRONT` | us-east-1 (always) | CloudFront distributions only | Global edge protection. Created in us-east-1 even if origin is elsewhere. |
| `REGIONAL` | any commercial Region | ALB, API Gateway REST/HTTP, AppSync, Cognito, App Runner | One ACL per Region. Replicate per Region for multi-Region. |

**Decision rule:** use CLOUDFRONT scope if and only if attaching
to CloudFront. Everything else uses REGIONAL.

### Step 2: Default action (Allow vs Block)

- **Allow** (common) — requests matching no rule are allowed.
  Rules block threats.
- **Block** — requests matching no rule are blocked. Used for
  allow-list patterns where a custom rule explicitly allows known
  traffic.

For public workloads, default to **Allow** and let managed rules
block threats. Use Block only for allow-listed internal APIs.

### Step 3: Managed rule groups

Managed rule groups are curated by AWS and AWS Marketplace sellers.
They are versioned — pin a version for stability, or use
`AGENTIC` versioning (auto-update) for hands-off maintenance.

Managed/subscription rule group tables moved verbatim to [managed-rules-and-logging-guide.md](references/managed-rules-and-logging-guide.md).
Load on demand when selecting rule groups in Step 3.

### Step 4: Custom rules

Custom rules use WAF statement types: `ByteMatchStatement`,
`IPSetReferenceStatement`, `RegexPatternSetReferenceStatement`,
`GeoMatchStatement`, `SizeConstraintStatement`, `RateBasedStatement`,
`AndStatement`, `OrStatement`, `NotStatement`, `LabelMatchStatement`.

**Common patterns:**

| Pattern | Statement | Example |
|---|---|---|
| Block a specific path | `ByteMatchStatement` on `URIPath` | Block `/admin/*` from non-corporate IPs |
| Allow partner IPs | `IPSetReferenceStatement` | Allow 203.0.113.0/24 to bypass managed rules |
| Block a country | `GeoMatchStatement` | Block `RU,KP,IR` from login endpoint |
| Block oversized payloads | `SizeConstraintStatement` on `Body` | Block bodies > 8 KB on `/api/v1/upload` |
| Block a regex | `RegexPatternSetReferenceStatement` | Block `(?i)(union.*select)` |
| Rate limit | `RateBasedStatement` | 2000 req / 5 min per IP on `/api/*` |

**Action types:** `Allow`, `Block`, `Count`, `CAPTCHA`, `Challenge`.
Use `Count` first to measure rule impact before switching to Block.

### Step 5: Rule priority ordering

WAF evaluates rules in ascending priority order. The first rule
that matches with a terminating action wins. `Count` is
non-terminating — it increments a counter and continues evaluation.

**Recommended priority layout:**

| Priority | Rule | Why |
|---|---|---|
| 0 | Allow: partner IPs / corporate CIDR | Allow-list wins first so managed rules don't block partners |
| 1-9 | Custom allow rules (specific paths, headers) | Explicit allows before managed blocks |
| 10 | `AWSManagedRulesCommonRuleSet` | Core protection |
| 20-90 | Other AWS managed rule sets | In threat-class order (SQLi, Linux, Windows, etc.) |
| 100-110 | IP reputation lists | After signature rules |
| 200+ | Bot Control, ATP, ACFP | Subscription rules; most expensive per-request |
| 1000+ | Custom blocks (URI, geo, size) | Workload-specific blocks last |
| 5000+ | Rate-based rules | Rate limiting after threat blocking |

Gaps (10, 20, 30...) let you insert rules without renumbering.
WAF requires unique priorities within a Web ACL.

### Step 6: Rate-based rules

A rate-based rule counts requests per aggregate key value over a
rolling 5-minute window. When the count exceeds the limit, the
action fires for the remainder of the window.

Rate-based rule JSON example moved verbatim to [worked-examples.md](references/worked-examples.md).
Load on demand when authoring a RateBasedStatement rule.

Aggregate key table and FORWARDED_IP config moved verbatim to [managed-rules-and-logging-guide.md](references/managed-rules-and-logging-guide.md).
Load on demand when choosing a rate aggregate key in Step 6.

**NEVER use `IP` aggregate key behind a CDN or proxy.** All
traffic shares the CDN egress IP — the rule rate-limits the CDN
node, not the abusive client. Use `FORWARDED_IP`.

### Step 7: Logging

WAF sends full request logs (timestamp, terminating rule, action,
client IP, URI, headers, labels) to one of three destinations.

| Destination | Setup | Notes |
|---|---|---|
| **Kinesis Firehose** | Create delivery stream named `aws-waf-logs-<name>` (prefix required). Firehose writes to S3. | Recommended default — buffers and batches. |
| **CloudWatch Logs** | Log group ARN with resource policy permitting `delivery.logs.amazonaws.com:PutLogEvents`. | Easiest for low-volume alerting and Insights queries. |
| **S3** (via Firehose) | Firehose delivers to S3. S3 bucket policy must allow `delivery.logs.amazonaws.com`. | Firehose is the intermediary — WAF does not write to S3 directly. |

put-logging-configuration CLI moved verbatim to [deployment-cli-commands.md](references/deployment-cli-commands.md).
Load on demand when enabling logging in Step 7.

CloudWatch Logs resource policy JSON moved verbatim to [managed-rules-and-logging-guide.md](references/managed-rules-and-logging-guide.md).
Load on demand when logging to CloudWatch Logs.

### Step 8: Association with ALB / API Gateway / CloudFront

ALB / API Gateway / CloudFront association CLI moved verbatim to [deployment-cli-commands.md](references/deployment-cli-commands.md).
Load on demand when associating in Step 8.

A Web ACL can associate with multiple resources (one ACL per
resource). CloudFront allows only one Web ACL per distribution.

### Step 9: CAPTCHA and Challenge actions

CAPTCHA/Challenge semantics moved verbatim to [managed-rules-and-logging-guide.md](references/managed-rules-and-logging-guide.md).
Load on demand when deciding CAPTCHA vs Challenge.

CAPTCHA rule JSON moved verbatim to [worked-examples.md](references/worked-examples.md).
Load on demand when adding CAPTCHA in Step 9.

**Integration SDK:** the client-side `aws-waf` JavaScript SDK
captures the token and attaches it to subsequent requests. The
SDK is specific to each Web ACL — copy the integration snippet
from the console or API.

ATP rule group config moved verbatim to [managed-rules-and-logging-guide.md](references/managed-rules-and-logging-guide.md).
Load on demand when configuring ATP login protection.

## Visibility config

Every rule and the Web ACL itself require a `VisibilityConfig`:

```json
{
  "SampledRequestsEnabled": true,
  "CloudWatchMetricsEnabled": true,
  "MetricName": "<unique-metric-name>"
}
```

- `SampledRequestsEnabled: true` — retains up to 100 sampled
  requests per rule per 5-minute window for debugging.
- `CloudWatchMetricsEnabled: true` — emits a CloudWatch metric per
  rule (`AWS/WAFV2` namespace for regional, `AWS/CloudFront` for
  CloudFront scope).
- `MetricName` — must be unique within the Web ACL.

ALWAYS enable both. The metrics are free; sampled requests are
essential for debugging rule matches.

## Workload matrix

| Workload | Scope | Managed rules | Custom rules | Rate limit | CAPTCHA/Challenge |
|---|---|---|---|---|---|
| Public web app behind CloudFront | CLOUDFRONT | Common, SQLi, Bot Control, IP Reputation | Geo-block, URI allow-list | FORWARDED_IP on `/api/*` | Challenge on `/search`, `/login` |
| ALB-hosted API | REGIONAL | Common, SQLi, KnownBadInputs | IP-set allow-list, size constraint | IP on `/api/*` | None |
| API Gateway REST API | REGIONAL | Common, SQLi, Linux | API-key header check | FORWARDED_IP on all | None |
| Login endpoint | REGIONAL | Common, SQLi, ATP | None | IP on `/login` | CAPTCHA on `/login` |
| Signup form | REGIONAL | Common, SQLi, ACFP | Email domain check | FORWARDED_IP on `/signup` | CAPTCHA on `/signup` |
| Internal admin API | REGIONAL | Common | Allow corporate CIDR only, block all else | None | None |

## Recent AWS features (2024-2026)

Recent AWS features moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand for 2024-2026 capability checks.

## NEVER (anti-patterns)

- NEVER create a CLOUDFRONT-scope Web ACL to protect an ALB or API
  Gateway. Scope is immutable. CLOUDFRONT scope attaches only to
  CloudFront distributions; REGIONAL scope attaches to ALB, API
  Gateway, AppSync, Cognito, App Runner. Wrong scope = silent
  association failure.

- NEVER put managed rule groups at priority 0 when you have
  allow-list rules. A partner IP that should bypass managed rules
  gets blocked because the managed rule evaluated first. Put
  allow-list rules at the lowest priorities (0-9) so they win.

- NEVER enable a Block action on a new rule without first running
  it in Count mode. Run Count for 1-2 weeks, inspect sampled
  requests for false positives, then switch to Block. Direct Block
  on an untested rule risks blocking legitimate users.

- NEVER use `IP` aggregate key for a rate-based rule when traffic
  arrives via a CDN, ALB, or proxy. All clients share the CDN
  egress IP; the rule rate-limits the CDN node, not the abusive
  client. Use `FORWARDED_IP` with `X-Forwarded-For`.

- NEVER enable logging without first verifying the destination's
  resource policy. A missing or mis-scoped policy on the Firehose
  delivery stream, CloudWatch Logs log group, or S3 bucket causes
  WAF to silently drop logs — there is no error, just missing data.

- NEVER assume a Web ACL takes effect immediately on CloudFront.
  Distribution updates propagate over several minutes. For ALB/API
  Gateway, the WAF association takes effect within ~60 seconds.

- NEVER configure ATP without specifying the exact `LoginPath`,
  `UsernameField`, and `PasswordField`. Without the field
  identifiers ATP cannot match, and the rule silently does nothing.

- NEVER omit `VisibilityConfig` on any rule. Without metrics and
  sampled requests, you cannot debug why a rule matched.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal
  `VERDICT:` label silently breaks downstream deployment pipelines
  and assertion-based evals.

## Expert heuristic — choosing scope, rules, and actions

Full heuristic detail moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing scope, rules, actions, rate keys, or logging.

## Pre-flight safety checks (run before any provisioning CLI)

Pre-flight CLI checks moved verbatim to [diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before running any provisioning CLI.

## Output format — MANDATORY literal labels

When invoked with a Web ACL provisioning request, your ENTIRE
response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as
shown. Do NOT write a preamble. Start with `ACL:` and stop after
the `VERIFICATION_COMMANDS:` block.

```text
ACL: <web-acl-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Scope — <CLOUDFRONT | REGIONAL> (<region>)
  [✓]      Default action — <Allow | Block>
  [✓]      Managed rules — <rule-group-name (priority N), ...>
  [✓]      Custom rules — <rule-name (priority N, statement, action), ...>
  [✓]      Rate-based rules — <limit> req/5min, aggregate key <IP | FORWARDED_IP | URI | ...>
  [✓]      Visibility config — CloudWatch metrics enabled, sampled requests enabled
  [✓]      Logging — <Firehose stream | CloudWatch log group | S3 bucket | none>
  [✓]      Association — <resource-arn | pending>
  [✓]      Tags — <key=value pairs>
  [OPTIONAL] CAPTCHA / Challenge — <rule-name (action) | none>
  [OPTIONAL] Bot Control / ATP / ACFP — <rule-group-name | not enabled>
VERIFICATION_COMMANDS:
  aws wafv2 list-web-acls --scope <scope> --region <region>
  aws wafv2 get-web-acl --scope <scope> --id <web-acl-id> --region <region>
  aws wafv2 list-resources-for-web-acl --web-acl-arn <web-acl-arn> --region <region>
  aws wafv2 get-logging-configuration --web-acl-arn <web-acl-arn> --region <region>
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite
  the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing (target
  resource ARN, logging destination, IP set ARN) and the operator
  must provide it before provisioning can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (target resource ARN for association, logging destination
when logging is requested, IP set ARN when referenced by a custom
rule), the verdict is `PREREQUISITES_MISSING` with each gap listed.
The checklist shows the target configuration with `[INPUT NEEDED]`
or `[✗]` for unmet prerequisites.

## Edge-case handling

Edge-case catalog moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a deployed ACL misbehaves.

## References (load on demand)

- [worked-examples.md](references/worked-examples.md) - secondary examples: rate-based rule JSON, CAPTCHA rule JSON
- [diagnostic-commands.md](references/diagnostic-commands.md) - pre-flight safety check CLI
- [advanced-patterns.md](references/advanced-patterns.md) - expert heuristic detail, edge cases, recent AWS features
- [deployment-cli-commands.md](references/deployment-cli-commands.md) - full 9-step CLI sequences, logging and association CLI
- [managed-rules-and-logging-guide.md](references/managed-rules-and-logging-guide.md) - rule group tables, ATP config, aggregate keys, logging policies

## Domain

AWS CloudOps / WAFv2 Web Application Firewall Provisioning.

## AWS documentation

- **AWS WAF Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **WAF Managed Rule Groups** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-list.html
- **WAF Rate-Based Rules** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-rate-based-rules.html
- **WAF Logging** — https://docs.aws.amazon.com/waf/latest/developerguide/logging.html
- **WAF CAPTCHA and Challenge** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-and-challenge.html
- **WAF ATP** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html
- **WAF Bot Control** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-bot.html
- **WAFv2 CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/wafv2/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 9 provisioning steps, including Web ACL
  creation, managed rule group attachment, custom rules, rate-based
  rules, logging configuration, ALB / API Gateway / CloudFront
  association, CAPTCHA / Challenge rules, and Terraform
  `aws_wafv2_web_acl` / `aws_wafv2_web_acl_association` /
  `aws_wafv2_ip_set` / `aws_wafv2_regex_pattern_set` resource
  equivalents.

- `references/managed-rules-and-logging-guide.md` — deep reference
  on managed rule group internals (Common, SQLi, Bot Control, ATP,
  ACFP, IP Reputation), WCU costs, versioning, scope-down
  statements, logging destination resource policies, CAPTCHA /
  Challenge token lifecycle, and aggregate key selection.
