---
name: wafv2-web-acl-auditor
description: 'Audits AWS WAFv2 Web ACL configurations to determine whether the ACL provides effective protection: default-action posture (Allow vs Block), managed-rule-group coverage gaps, rule effectiveness (BLOCK vs COUNT, shadow/bypass rules, stale exclusions), rate-based rule correctness, logging and visibility configuration, and text-transformation bypass vectors. Emits a deterministic verdict per Web ACL. Use when reviewing a WAFv2 Web ACL for security posture, checking managed-rule coverage, validating rate-limit configuration, auditing WAF logging, or hardening a WAF before production deployment. Triggers: WAF, WAFv2, Web ACL, managed rule group, AWSManagedRules, rate-based rule, CAPTCHA, Challenge, OverrideAction, Count mode, forwarded IP, Bot Control, ATP, text transformation, WAF logging, WAF visibility, OWASP, SQLi, XSS, RFI.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex). No AWS CLI required for offline Web ACL classification — the skill reasons over provided config text. Live-account audits use aws wafv2 describe-web-acl / list-web-acls / get-logging-configuration (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: MISCONFIGURED | WEAK | ADEQUATE | OK
  when_to_use: Reviewing a WAFv2 Web ACL configuration (JSON from describe-web-acl), auditing managed-rule-group coverage, validating rate-based-rule correctness, checking WAF logging and visibility configuration, investigating rule-bypass or shadow-rule patterns, or hardening a WAF before production deployment.
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: WAF, WAFv2, Web ACL, managed rule group, AWSManagedRulesCommonRuleSet, rate-based rule, OverrideAction, Count mode, forwarded IP, Bot Control, ATP, text transformation, WAF logging, WAF visibility, OWASP, SQLi, XSS, CAPTCHA, Challenge
  tags: aws, wafv2, cloudops, security, web-acl, managed-rules, rate-limiting, owasp, audit, compliance
  dependencies: aws-orchestrator
---

# WAFv2 Web ACL Auditor

## Mindset

Classify a WAFv2 Web ACL configuration against effective-protection principles.
A Web ACL is not "secure" just because it exists — a WAF with `DefaultAction:
Allow` and all rules in COUNT mode is a logging appliance, not a security
control. The goal is to determine whether the ACL would actually **stop** the
attacks it claims to defend against: does every critical traffic class pass
through a BLOCK-mode managed rule group before reaching the backend, or does a
misplaced Allow rule or a blanket COUNT override silently disable protection?

Four-failure-mode detail moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand when explaining why a verdict was reached.

## Quick reference

If the Web ACL has `DefaultAction: Allow` and zero rules, it is
MISCONFIGURED. If any managed rule group has `OverrideAction: {Count: {}}`
and no compensating BLOCK rule covers that threat class, it is
MISCONFIGURED. If a custom Allow rule sits at a lower priority than all
managed rule groups with a broad match pattern, it is MISCONFIGURED. If
`AWSManagedRulesCommonRuleSet` is absent entirely, it is MISCONFIGURED.
If it has 3+ managed rule groups in BLOCK mode, a rate-based rule,
logging, and visibility, it is OK. See the steps below for edge cases
(scope, forwarded IP, exclusions, transformations, ImmunityTime).

**Output:** Always emit the block below (see Output format for detail):
`WEBACL: <name> | VERDICT: <MISCONFIGURED|WEAK|ADEQUATE|OK> | REASON | RISK | GAPS | REMEDIATION`.

## Process — Classification logic (apply in order)

### Step 0: Validate input

If the Web ACL config is not parseable (malformed JSON, missing `DefaultAction`
or `Rules` array), output:

```text
WEBACL: <name>
VERDICT: ERROR
REASON: Web ACL config is not valid JSON or is missing required fields (DefaultAction, Rules).
REMEDIATION: Re-export the ACL with aws wafv2 describe-web-acl --id <id> --scope <CLOUDFRONT|REGIONAL> --output json.
```

Do not attempt classification on malformed input. Additionally, verify the
`Scope` field if present: a `CLOUDFRONT` scope ACL must live in `us-east-1`;
a `REGIONAL` scope ACL in `us-east-1` cannot protect a CloudFront
distribution. Flag a scope mismatch but do not fail — the ACL may be valid
for a regional resource.

### Step 1: Check for zero-rule open door

If `DefaultAction` is `Allow` AND the `Rules` array is empty or contains
only custom rules with no `ManagedRuleGroupStatement`, classify as
**MISCONFIGURED** (CRITICAL). The WAF is a pass-through — every request
reaches the backend uninspected. Cite "Step 1: zero-protection ACL."

This also covers the case where `DefaultAction` is `Allow` and the only
rules present are rate-limit or geo-block rules without any content-inspection
managed rule group — a rate limiter is not a web application firewall.

### Step 2: Detect shadow / bypass rules

For every custom rule (a rule whose `Statement` is NOT a
`ManagedRuleGroupStatement`), check:

- **Action is `Allow` or `Challenge`** (not `Block`, not `Count`).
- **Priority is lower than at least one managed rule group's priority.**

If both are true, the custom rule is evaluated FIRST. If its `Statement`
matches a broad pattern, it shadows (bypasses) the managed rule groups for
that traffic class. The match pattern determines severity:

- **URIPath `STARTS_WITH` / `CONTAINS` with a common prefix** (e.g.,
  `/api/`, `/`, `/*`) — CRITICAL. Shadows all managed rules for a major
  traffic class. This is the most common shadow pattern.
- **HeaderMatch on a specific value** (e.g., `X-Internal: true`) — HIGH.
  Shadows managed rules for requests carrying that header; an attacker who
  discovers the header value bypasses all protection.
- **IPSet match** — MODERATE. Shadows for specific IPs; legitimate for
  known-good partner IPs but dangerous if the IPSet is stale or broad.
- **Exact-match URIPath** (e.g., `/health`) — LOW. Intentional exclusion
  for health checks; acceptable but should be noted.

A shadow rule with a broad match pattern and no managed rule group at a
lower priority to compensate makes the ACL **MISCONFIGURED**. Cite
"Step 2: shadow rule bypasses managed inspection."

**Priority semantics note:** WAF evaluates rules in ascending priority
order (priority 0 is first). The first rule whose `Action` is `Allow`,
`Block`, or `CAPTCHA` terminates evaluation for that request — subsequent
rules do not inspect it. `Count` and `Challenge` actions do NOT terminate
evaluation; the request continues through subsequent rules.

### Step 3: Detect COUNT-mode paralysis

For each rule with a `ManagedRuleGroupStatement`, check the `OverrideAction`:

- `OverrideAction: {None: {}}` or absent — the group uses its default
  actions (most rules BLOCK). This is correct.
- `OverrideAction: {Count: {}}` — the ENTIRE group is in count mode.
  Every rule in the group logs but does not block. This disables the
  group's protection.

If ALL managed rule groups in the ACL have `OverrideAction: {Count: {}}`,
and no custom BLOCK rule compensates, classify as **MISCONFIGURED**
(CRITICAL). Cite "Step 3: all managed rules in COUNT mode — protection
disabled."

If SOME but not all managed rule groups are in COUNT mode, downgrade the
ACL by one tier (e.g., OK → ADEQUATE, ADEQUATE → WEAK). The COUNT-mode
groups are not providing protection; treat them as absent for coverage
scoring. Cite "Step 3: partial COUNT-mode — <group name> not blocking."

OverrideAction vs RuleActionOverrides nuance moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand when tuning false positives in Step 3.

### Step 4: Verify baseline managed-rule coverage

Check which managed rule groups are present (in BLOCK mode — COUNT-mode
groups from Step 3 do not count). Apply the coverage matrix below. The
**minimum viable coverage** is `AWSManagedRulesCommonRuleSet` plus at least
one input-validation group.

If `AWSManagedRulesCommonRuleSet` is absent entirely (not in COUNT, just
missing), classify as **MISCONFIGURED** (CRITICAL) regardless of other
rules. This group provides the OWASP Top 10 baseline: SQLi, XSS, RFI, LFI,
traversal, session fixation, and protocol anomalies. Without it, the ACL
has no baseline content inspection. Cite "Step 4: missing CommonRuleSet —
no OWASP baseline."

Coverage matrix moved verbatim to [managed-rule-group-reference.md](references/managed-rule-group-reference.md).
Load on demand when scoring baseline coverage in Step 4.

### Step 5: Check rate-based rule correctness

If the ACL has no rule with a `RateBasedStatement`, record a gap
(`GAP: no rate-based rule — vulnerable to volumetric/brute-force attacks`).
This alone does not determine the verdict but factors into the WEAK tier.

If a rate-based rule exists, validate:

- **AggregateKeyType.** If `IP` (legacy) and the protected resource is
  behind CloudFront or an ALB, flag as a gap — the rule rate-limits the
  proxy's IP, not the client. The correct key behind a proxy is
  `FORWARDED_IP` with `ForwardedIPConfig.HeaderName` matching the proxy's
  forwarded-IP header (`X-Forwarded-For` for ALB, `X-Amz-Cf-Id` is NOT an
  IP — CloudFront forwards client IP in `X-Forwarded-For` as well, but
  the first value is the client; set `FallbackBehavior: MATCH`).
- **Limit threshold.** `<100` is aggressive (legitimate traffic at risk);
  `>5000` is permissive (attackers can operate below it). Reasonable range
  depends on traffic profile: 100–500 for login/API endpoints, 500–2000
  for general web traffic. Flag extreme values.
- **EvaluationWindowSec.** Default is 300 (5 minutes). A shorter window
  (60–120s) catches burst attacks faster but is more sensitive; a longer
  window (600s) smooths out legitimate spikes. Not a defect — note for
  context.

A rate-based rule with `AggregateKeyType: IP` behind a proxy is a
**functional defect** — the rule appears to work but rate-limits the
wrong entity. Flag as HIGH severity.

### Step 6: Check logging configuration

**Detection rule:** If the Web ACL JSON does NOT contain a top-level
`LoggingConfiguration` key (with `LogDestinationConfigs` pointing to a
CloudWatch Logs ARN, Kinesis Data Firehose ARN, or S3 bucket ARN), logging
is NOT configured. Record a gap (`GAP: no WAF logging — blind to attacks`).

Do NOT confuse `VisibilityConfig` with `LoggingConfiguration` — they are
independent settings. `VisibilityConfig` controls CloudWatch metrics and
sampled-request storage (Step 7). `LoggingConfiguration` controls full
request/response log delivery to a destination. A Web ACL can have
`VisibilityConfig` enabled but `LoggingConfiguration` absent — that ACL
has metrics but no logs.

Without logging:
- You cannot tune false positives (no blocked-request samples in the log).
- You cannot detect bypasses (no count-mode samples in the log).
- Incident response has no evidence of attack timing or source.
- PCI-DSS Requirement 10 and SOC 2 CC7.2 require security event logging.

No logging with `DefaultAction: Allow` and minimal rules compounds the
risk — the WAF is both weak and blind. This combination is always a
HIGH gap.

**Redacted fields:** `LoggingConfiguration` may have `RedactedFields`
configured to strip sensitive data from logs (e.g., passwords, credit
card numbers). This is correct — check that `RedactedFields` is not
overly broad (stripping entire request bodies defeats the purpose of WAF
logging for false-positive tuning).

### Step 7: Check visibility configuration

Every rule AND the Web ACL itself should have `VisibilityConfig` with:

- `CloudWatchMetricsEnabled: true` — emits per-rule metrics to CloudWatch.
  Without this, the WAF dashboard is blank and you cannot detect when a
  rule stops firing.
- `SampledRequestsEnabled: true` — stores a sample of matched requests
  for inspection in the console. Without this, false-positive tuning
  requires reproducibility you do not have.

Missing `CloudWatchMetricsEnabled` on the Web ACL-level `VisibilityConfig`
is a HIGH gap — the entire WAF is invisible to monitoring. Missing it on
individual rules is MODERATE — per-rule metrics are unavailable but the
ACL-level metric still fires.

### Step 7b: Check Web ACL associations

An unassociated Web ACL protects nothing. If the input includes association
data (or a note that the ACL is associated with specific resources),
verify that at least one resource is listed. If the input does NOT include
association data, add a NOTE to the REMEDIATION field:

```text
NOTE: Verify resource associations with aws wafv2 list-resources-for-web-acl
--web-acl-arn <arn>. An unassociated ACL protects nothing regardless of
rule quality.
```

This does not change the verdict tier (the audit evaluates rule
configuration quality, not deployment state), but it MUST appear in the
REMEDIATION field so the operator does not mistake a well-configured but
unassociated ACL for active protection.

### Step 8: Evaluate rule actions and statement correctness

For custom rules (non-managed-group), verify the `Action` and `Statement`:

- **`Action: Count` on a custom rule** — the rule logs but does not block.
  Acceptable for new rules in a testing phase; flag if the rule is intended
  to block (note in REMEDIATION).
- **`ByteMatchStatement` with `TextTransformations` containing only
  `NONE`** — raw inspection without decoding. This is a bypass vector:
  URL-encoded (`%3Cscript%3E`) or HTML-entity-encoded (`&#x3C;script&#x3E;`)
  payloads evade detection. See the text-transformation matrix below.
- **`SizeConstraintStatement` with `ComparisonOperator: GT` and a large
  `Size`** (e.g., > 1 MB) — the rule inspects only oversized bodies, which
  is rarely the intent. Likely a misconfiguration.
- **`GeoMatchStatement` with `CountryCodes` containing only one country
  AND `Action: Block`** — a deny-all-except-one-country rule. Functional
  but fragile; legitimate users traveling abroad are blocked. Flag as
  MODERATE unless the application is explicitly geo-restricted.
- **`NotStatement` wrapping an `IPSet`** with `Action: Block` — blocks
  everything not in the IPSet. This is a Default-Block-via-custom-rule
  pattern. Verify the IPSet is comprehensive.

Text-transformation matrix moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing ByteMatchStatement bypass vectors in Step 8.

### Step 9: Check CAPTCHA / Challenge rule configuration

If the ACL contains CAPTCHA or Challenge actions:

- **`ImmunityTime` not set (null or 0)** — every request is challenged,
  breaking single-page applications and API flows. The token is single-use.
  Set `ImmunityTime` to 60–300 seconds for interactive flows.
- **`ChallengeAction` without a fallback `Block` rule** — if a bot solves
  the challenge, it proceeds with no further restriction. Layer a Block
  rule behind the challenge for repeat offenders.
- **CAPTCHA on an API endpoint** — programmatic clients cannot solve visual
  CAPTCHAs. Use `Challenge` (silent JS proof-of-work) for APIs; reserve
  CAPTCHA for browser flows.

Missing `ImmunityTime` is a MODERATE application-compatibility issue, not a
security gap — but it causes operators to disable CAPTCHA entirely when it
breaks their app, which IS a security gap.

### Step 10: Check managed-rule-group exclusions

`ManagedRuleGroupStatement.ExcludedRules` removes specific rules from the
group. Common legitimate exclusions:

- `NoUserAgent_HEADER` from CommonRuleSet — health checkers send no UA.
- `SizeRestrictions_BODY` from CommonRuleSet — large file uploads blocked.

If `ExcludedRules` contains more than 3 rules from a single group, or if
it excludes a rule protecting against a Top-10 OWASP category (SQLi, XSS,
RCE, LFI/RFI), flag as MODERATE — the exclusion weakens protection for
that attack class. Cite the specific excluded rule name and what it blocks.

### Step 11: Aggregate to verdict

The verdict is determined by counting CRITICAL findings and HIGH gaps. The
precedence is strict — a single CRITICAL finding overrides everything.

**Gap severity reference (use this to count HIGH gaps):**

| Gap | Severity | Step |
|---|---|---|
| Default Allow + zero managed rule groups | CRITICAL | 1 |
| Shadow Allow rule before managed groups (broad match) | CRITICAL | 2 |
| All managed groups in COUNT mode | CRITICAL | 3 |
| Missing CommonRuleSet entirely | CRITICAL | 4 |
| Only 1 managed group in BLOCK (insufficient coverage) | HIGH | 4 |
| No rate-based rule | HIGH | 5 |
| No logging destination configured | HIGH | 6 |
| Rate rule with `AggregateKeyType: IP` behind proxy | HIGH | 5 |
| No CloudWatch metrics on Web ACL VisibilityConfig | HIGH | 7 |
| Missing input-validation group (KnownBadInputs absent) | MODERATE | 4 |
| Missing Bot Control / ATP (paid add-ons) | LOW | 4 |
| Missing sampled requests on VisibilityConfig | LOW | 7 |
| ImmunityTime not set on CAPTCHA rule | LOW | 9 |

| Verdict | Trigger condition | Example |
|---|---|---|
| **MISCONFIGURED** | Any CRITICAL finding from Steps 1–4 | Zero-rule ACL; all-COUNT mode; shadow bypass rule; missing CommonRuleSet |
| **WEAK** | No CRITICAL, but 2+ HIGH gaps | CommonRuleSet-only + no rate rule + no logging (3 HIGH gaps); CommonRuleSet + KnownBadInputs but no rate rule + no logging (2 HIGH gaps) |
| **ADEQUATE** | No CRITICAL, exactly 1 HIGH gap (or 0 HIGH + MODERATE gaps) | CommonRuleSet + KnownBadInputs in BLOCK + rate rule + logging, but rate rule uses IP behind proxy (1 HIGH) |
| **OK** | No CRITICAL, 0 HIGH gaps (LOW gaps allowed) | 3+ BLOCK-mode managed groups (baseline + input validation + reputation) + FORWARDED_IP rate rule + logging + full visibility + no shadow rules |

**Critical counting examples:**

- **CommonRuleSet-only, no rate rule, no logging:** 3 HIGH gaps → **WEAK**.
- **CommonRuleSet + KnownBadInputs, no rate rule, no logging:** 2 HIGH gaps → **WEAK**.
- **CommonRuleSet + KnownBadInputs + rate rule + logging, rate rule uses IP behind proxy:** 1 HIGH gap → **ADEQUATE**.
- **3+ groups + FORWARDED_IP rate rule + logging + full visibility:** 0 HIGH gaps → **OK**.

**Aggregation rule:** A single CRITICAL finding makes the whole ACL
MISCONFIGURED, regardless of how many other rules are correct. Two or more
HIGH gaps make it WEAK. Exactly one HIGH gap caps the verdict at ADEQUATE.
Zero HIGH gaps is OK (MODERATE and LOW gaps appear in GAPS and REMEDIATION
but do not downgrade the tier).

## Effective protection context (expert note)

Full request-path context moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand when assessing real-world effectiveness.

## Output format (per Web ACL)

```text
WEBACL: <name>
VERDICT: MISCONFIGURED | WEAK | ADEQUATE | OK
REASON: <1-3 sentences citing the specific step, finding, and config>
RISK: CRITICAL | HIGH | MODERATE | LOW
GAPS: <comma-separated list of gap IDs, or "None" if OK>
REMEDIATION: <specific action(s), or "None required" if OK>
```

### Multi-rule aggregation example

Full multi-rule aggregation example moved verbatim to [worked-examples.md](references/worked-examples.md).
Load on demand when emitting a multi-gap MISCONFIGURED report.

## Operational edge cases (expert knowledge)

Operational edge-case catalog moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand for production-behavior surprises (COUNT metrics, labels, sliding window, spoofing).

## NEVER (anti-patterns)

- NEVER classify a Web ACL with `DefaultAction: Allow` and zero managed
  rule groups as OK or ADEQUATE. It is MISCONFIGURED — the WAF is a
  pass-through that inspects nothing. A rate-limit rule without content
  inspection does not change this verdict.

- NEVER treat `OverrideAction: {Count: {}}` on a managed rule group as
  equivalent to BLOCK. COUNT mode explicitly disables blocking — the
  group logs matches but lets traffic through. If ALL groups are in COUNT,
  the ACL is MISCONFIGURED regardless of how many groups are configured.

- NEVER ignore a custom Allow rule at a lower priority number than managed
  rule groups. WAF evaluates in ascending priority order and terminates on
  the first Allow/Block/CAPTCHA. A broad-match Allow rule at priority 0
  means every subsequent managed rule group is dead code for the matched
  traffic class. This is the single most common WAF bypass in production.

- NEVER classify a Web ACL missing `AWSManagedRulesCommonRuleSet` as OK.
  This group is the OWASP Top 10 baseline — without it, SQLi, XSS, RFI,
  LFI, traversal, and protocol-anomaly attacks pass uninspected unless
  every one is covered by a custom rule (which is impractical and fragile).

- NEVER assume `DefaultAction: Block` is inherently safer than `Allow`.
  Default Block requires every legitimate request path to be explicitly
  allow-listed by a rule; if the rules are incomplete, legitimate traffic
  is blocked (application outage). Default Allow with comprehensive BLOCK
  rules is the standard production posture. Default Block is exceptional
  and demands careful allow-listing.

- NEVER recommend switching `DefaultAction` from Allow to Block without a
  COUNT-mode testing period first. Default Block without a complete
  allow-list will block legitimate traffic immediately. Run all managed
  rule groups in COUNT for 1–2 weeks, review sampled requests for false
  positives, add exclusions, THEN switch to Block.

- NEVER recommend enabling all managed rule groups blindly without
  considering application compatibility. `AWSManagedRulesCommonRuleSet`
  includes `SizeRestrictions_BODY` (blocks bodies > 8 KB) and
  `GenericRFI_BODY` which can false-positive on legitimate API payloads.
  Enable incrementally in COUNT mode, tune exclusions, then switch to BLOCK.

- NEVER treat a rate-based rule with `AggregateKeyType: IP` behind
  CloudFront or an ALB as correctly configured. The rule rate-limits the
  proxy IP, not the client. Behind a proxy, the correct key is
  `FORWARDED_IP` with `HeaderName: X-Forwarded-For` and
  `FallbackBehavior: MATCH` (use the first IP in the chain).

- NEVER classify an unassociated Web ACL as providing protection. A Web
  ACL with no resource associations protects nothing — verify with
  `aws wafv2 list-resources-for-web-acl`. An unassociated ACL with a
  perfect configuration is still theatre.

- NEVER treat `TextTransformations: [{Type: NONE}]` on a
  `ByteMatchStatement` as sufficient for XSS/SQLi detection. Raw
  inspection without `URL_DECODE` or `HTML_ENTITY_DECODE` allows encoded
  payloads to bypass pattern matching. At minimum, include `URL_DECODE`
  and `HTML_ENTITY_DECODE` in the transformation list.

- NEVER recommend `Action: Block` as the first remediation for a managed
  rule group in COUNT mode without first reviewing the sampled requests
  from the COUNT period. Switching directly to BLOCK without false-positive
  tuning causes production incidents — legitimate API calls are blocked,
  and the operations team reverts to COUNT (sometimes permanently).

- NEVER trust the Web ACL name as an indicator of scope. A Web ACL named
  "production-cloudfront-acl" may be REGIONAL scope and protect an ALB.
  Always read the `Scope` field and verify the associated resources match
  the intended perimeter.

- NEVER assume a Web ACL with a perfect rule configuration is providing
  protection without verifying resource associations. An unassociated ACL
  is dead weight — `aws wafv2 list-resources-for-web-acl` must return at
  least one ALB, API Gateway, AppSync, CloudFront distribution, or Cognito
  user pool. Always include an association-check NOTE in the REMEDIATION
  field, even for OK verdicts.

- NEVER confuse `VisibilityConfig` with `LoggingConfiguration`. They are
  independent settings. `VisibilityConfig` controls CloudWatch metrics and
  sampled-request storage. `LoggingConfiguration` controls full log delivery
  to CloudWatch Logs, Firehose, or S3. A Web ACL can have metrics enabled
  but no logging — it is observable but not auditable.

- NEVER trust a custom rule referencing an `IPSet` without verifying the
  IPSet contents are current. Stale IPSets — containing decommissioned
  partner IPs, expired allow-list entries, or broad CIDR blocks from a
  debugging session — are a silent bypass or silent block. An IPSet
  allow-rule with a `/8` CIDR effectively allows 16 million IPs through
  managed rule inspection. Always audit IPSet scope alongside the Web ACL.

- NEVER chain custom `LabelMatchStatement` rules on labels from a managed
  rule group without verifying the source rule is not in `ExcludedRules`.
  Excluding a rule suppresses its label emission — downstream label-match
  rules silently stop firing. This is invisible in metrics because the
  label-match rule simply matches nothing (0 requests), which looks the
  same as "no traffic matched the label."

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks moved verbatim to [diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before recommending or running any remediation CLI.

## Remediation guidance

Per-verdict remediation playbooks moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand after a verdict to build the REMEDIATION field.

## Recent AWS features (2024-2026)

Recent AWS features moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand for 2024-2026 capability checks.

## References

See `references/managed-rule-group-reference.md` for the full managed rule
group catalog, per-group rule lists, `RuleActionOverrides` syntax, and the
`put-logging-configuration` / `associate-web-acl` CLI commands.

Section taxonomy moved verbatim to [advanced-patterns.md](references/advanced-patterns.md).
Load on demand to see the canonical CloudOps auditor section order.

## References (load on demand)

- [worked-examples.md](references/worked-examples.md) - secondary worked example: multi-rule aggregation report
- [diagnostic-commands.md](references/diagnostic-commands.md) - pre-flight safety checks and backup/association CLI
- [advanced-patterns.md](references/advanced-patterns.md) - failure modes, edge cases, matrices, remediation playbooks, recent features
- [managed-rule-group-reference.md](references/managed-rule-group-reference.md) - managed rule group catalog and coverage matrix

## Domain

AWS CloudOps / WAF Security & Compliance.

## AWS documentation

- **AWS WAF Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **WAF Security** — https://docs.aws.amazon.com/waf/latest/developerguide/security.html
- **WAF API Reference (v2)** — https://docs.aws.amazon.com/waf/latest/APIReference/
- **AWS CLI — wafv2** — https://docs.aws.amazon.com/cli/latest/reference/wafv2/
- **Bot Control** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-bot.html
- **ATP managed rule group** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html
