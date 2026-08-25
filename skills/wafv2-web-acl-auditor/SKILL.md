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

The classification focuses on four failure modes that WAF operators encounter
in production:

1. **Shadow rules** — a custom Allow/Challenge rule at a priority lower
   (evaluated earlier) than the managed rule groups, causing WAF to skip
   inspection for broad traffic classes. The most dangerous misconfiguration
   because the managed rules appear healthy in metrics while doing nothing.

2. **COUNT-mode paralysis** — `OverrideAction: {Count: {}}` on managed rule
   groups. The WAF logs every match but never blocks. Operators set this
   during testing and forget to flip it back; metrics look green because
   "no traffic was blocked" reads the same as "no attacks arrived."

3. **Coverage gaps** — missing the baseline OWASP rule set or input-validation
   groups (SQLi, Known-Bad-Inputs). A WAF with only a rate-limit rule and a
   geo-block is not an application firewall; it is a volumetric filter.

4. **Blind spots** — no logging destination configured, or
   `SampledRequestsEnabled: false`. Without logs, there is no incident
   response, no false-positive tuning, and no evidence the WAF is working.

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

**`RuleActionOverrides` vs `OverrideAction`:** These are different fields.
`OverrideAction` is the blanket rule-level override on the rule that wraps
the managed group statement. `RuleActionOverrides` lives INSIDE the
`ManagedRuleGroupStatement` and selectively overrides individual rules
within the group (e.g., change one rule from BLOCK to COUNT while leaving
the rest in BLOCK mode). A few targeted `RuleActionOverrides` for
false-positive tuning is acceptable; a blanket `OverrideAction: {Count: {}}`
is not.

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

**Managed rule group coverage matrix:**

| Category | Group Name | What it blocks | Required? |
|---|---|---|---|
| Baseline | `AWSManagedRulesCommonRuleSet` | OWASP Top 10 (SQLi, XSS, RFI, LFI, traversal, protocol anomalies, generic RCE) | **MUST HAVE** |
| Input validation | `AWSManagedRulesKnownBadInputsRuleSet` | Log4j, SSRF, bad-IP patterns, page-preview exploits | **STRONGLY RECOMMENDED** |
| Input validation | `AWSManagedRulesSQLiRuleSet` | Dedicated SQLi patterns (complements CommonRuleSet) | Recommended for form/API endpoints |
| OS hardening | `AWSManagedRulesLinuxRuleSet` | Linux-specific shell injection | If backend is Linux |
| OS hardening | `AWSManagedRulesUnixRuleSet` | POSIX shell patterns | If backend is Unix |
| OS hardening | `AWSManagedRulesWindowsRuleSet` | PowerShell, cmd.exe injection | If backend is Windows |
| Reputation | `AWSManagedRulesAmazonIpReputationList` | Known malicious IPs (botnets, scanners) | Recommended |
| Reputation | `AWSManagedRulesAnonymousIpList` | Tor, proxies, VPNs, hosting providers | Optional (false-positive prone) |
| App framework | `AWSManagedRulesWordPressRuleSet` | WordPress exploits | If running WordPress |
| App framework | `AWSManagedRulesPHPRuleSet` | PHP-specific exploits | If running PHP |
| Bot / fraud | `AWSBotControlRuleSet` | Bot classification (good/bad/unknown) | Paid add-on; optional |
| Bot / fraud | `AWSManagedRulesATPRuleSet` | Account takeover (credential stuffing, brute force) | Paid; recommended for login endpoints |
| Bot / fraud | `AWSManagedRulesACFRuleSet` | Account creation fraud | Paid; for signup flows |

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

**Text-transformation matrix (for ByteMatchStatement and RegexPatternSet):**

| Transformation | What it defeats | Must-have for |
|---|---|---|
| `URL_DECODE` | `%3Cscript%3E` | XSS/SQLi detection on URL/query |
| `URL_DECODE_UNI` | `%u003C` (unicode URL encoding) | Legacy IIS apps |
| `HTML_ENTITY_DECODE` | `&#x3C;script&#x3E;` | XSS in body/headers |
| `COMPRESS_WHITE_SPACE` | Tab/newline injection (`scr\tipt`) | SQLi/XSS in body |
| `LOWERCASE` | Case-variation (`ScRiPt`) | Case-insensitive matching |
| `CMD_LINE` | Windows argument injection | OS command injection |
| `BASE64_DECODE` | Base64-obfuscated payloads | API body inspection |
| `HEX_DECODE` | Hex-encoded payloads | API body inspection |

**Transformation order matters:** AWS applies transformations in the listed
order. `URL_DECODE` before `HTML_ENTITY_DECODE` handles double-encoding
(`%26%23x3C%3Bscript%26%23x3E%3B` → `&#x3C;script&#x3E;` → `<script>`).
Reversed order leaves the outer encoding intact. A `ByteMatchStatement`
with `TextTransformations: [{Type: NONE}]` inspects the raw request —
almost always a bypass for any pattern-based detection.

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

The classification above evaluates the Web ACL configuration in isolation.
In production, the WAF's effectiveness depends on the full request path:

1. **CloudFront / ALB → WAF → origin.** The WAF inspects the request
   after the CDN/load balancer terminates the TLS connection. The
   `X-Forwarded-For` header contains the client IP chain. Rate-based rules
   must use `FORWARDED_IP` with the correct header to rate-limit the
   actual client, not the proxy.

2. **Rule evaluation is short-circuit.** The first terminating action
   (Allow, Block, CAPTCHA) wins. A rule at priority 0 with `Action: Allow`
   that matches all traffic means no subsequent rule ever fires. The WAF
   processes rules in strict ascending priority order. Within a managed
   rule group, the group's internal rule order applies.

3. **Labels propagate forward.** A managed rule group can add labels
   (e.g., `awswaf:managed:awsbotcontrol:robot:verified_bot`). Later custom
   rules can match on these labels using `LabelMatchStatement`. This
   enables layered defense: let the Bot Control group classify, then write
   a custom rule that blocks based on the label. Not understanding labels
   leads to redundant custom rules that duplicate managed-rule logic.

4. **Association is required.** An unassociated Web ACL protects nothing.
   `aws wafv2 list-resources-for-web-acl --web-acl-arn <arn>` returns the
   associated ALBs, API Gateways, AppSync APIs, CloudFront distributions,
   or Cognito user pools. Always verify association in a live audit — a
   perfectly configured ACL with zero associations is theatre.

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

A Web ACL with CommonRuleSet in BLOCK (good) but a shadow Allow rule at
priority 0 matching `/api/*`, no rate-based rule, and no logging:

```text
WEBACL: api-gateway-acl
VERDICT: MISCONFIGURED
REASON: Step 2: custom rule "api-bypass" at priority 0 with Action Allow
matches URIPath STARTS_WITH /api/, shadowing all managed rule groups
(priority 10+) for the entire API surface. No rate-based rule (Step 5) and
no logging configuration (Step 6) compound the exposure — the WAF is both
bypassed and blind.
RISK: CRITICAL
GAPS: shadow-rule, no-rate-limit, no-logging
REMEDIATION: (1) Move the api-bypass rule to a priority HIGHER than the
managed rule groups, or scope it to an exact-match health-check path and
remove the STARTS_WITH wildcard. (2) Add a rate-based rule with
AggregateKeyType FORWARDED_IP and HeaderName X-Forwarded-For. (3) Enable
logging to CloudWatch Logs or Kinesis Data Firehose.
```

## Operational edge cases (expert knowledge)

These are production behaviors that surprise operators and are NOT in the
AWS documentation — they come from operating WAFv2 at scale:

1. **The COUNT-to-BLOCK metrics trap.** When you switch a managed rule
   group from COUNT to BLOCK, CloudWatch metrics for `CountedRequests`
   drop to zero (because those requests are now BLOCKED, not COUNTED).
   Operators often read this as "the WAF stopped detecting attacks" and
   revert to COUNT. The correct metric to watch after the switch is
   `BlockedRequests` — it should spike. Train operators before switching.

2. **Label propagation depends on group action.** Managed rule groups
   like Bot Control add labels (`awswaf:managed:awsbotcontrol:*`) ONLY
   when the group evaluates the rule. If you put the group in COUNT mode
   via `OverrideAction`, labels are STILL added (COUNT does not suppress
   label emission — only ExcludedRules does). BUT if you exclude a
   specific rule via `ExcludedRules`, its labels are NOT emitted. If you
   chain custom `LabelMatchStatement` rules on those labels, the chain
   silently breaks. Always verify the label source rule is not excluded.

3. **Rate-based rule sliding window.** `EvaluationWindowSec` is a SLIDING
   window, not a fixed window. A client making exactly `Limit` requests
   within 300 seconds may NOT be blocked — it depends on the distribution
   of requests across the window. Two bursts of `Limit/2` requests
   separated by 200 seconds may both pass because neither burst alone
   exceeds the limit within any 300-second slice. For deterministic
   brute-force protection on login endpoints, use a NARROWER window
   (60 seconds) with a lower limit.

4. **ForwardedIP spoofing via client header.** When using
   `AggregateKeyType: FORWARDED_IP`, the WAF trusts the value of
   `X-Forwarded-For` (or the configured header). CloudFront and ALB
   APPEND the real client IP to this header, but they do NOT strip
   client-supplied values. A client sending `X-Forwarded-For: 1.2.3.4`
   causes CloudFront to forward `X-Forwarded-For: 1.2.3.4, <real-ip>`.
   With `FallbackBehavior: MATCH`, the WAF uses the FIRST IP (1.2.3.4 —
   the spoofed one). An attacker rotates spoofed IPs to evade rate-based
   rules. Mitigation: place a CloudFront function or Lambda@Edge that
   strips client-supplied `X-Forwarded-For` before WAF inspection, or
   use `CUSTOM_KEYS` with a non-spoofable identifier (e.g., a session
   cookie) as the rate aggregate key.

5. **JSON body OversizeHandling default.** When the request body exceeds
   64 KB (the WAFv2 inspection limit for JSON bodies), the
   `OversizeHandling` field in `FieldToMatch.Json.Body` determines what
   happens. The default is `CONTINUE` — inspect as a raw string without
   JSON parsing. This means nested JSON payloads deeper than 64 KB bypass
   JSON-path-based rules. For APIs that accept large JSON bodies, set
   `OversizeHandling: MATCH` (block oversized bodies) or ensure the
   payload is validated upstream.

6. **CLOUDFRONT scope propagation delay.** Changes to a CLOUDFRONT scope
   Web ACL propagate to all CloudFront edge locations within 60 seconds
   but may take up to 5 minutes globally. Regional scope changes
   (ALB/API Gateway) propagate within 60 seconds. Do not test rule
   changes immediately — wait at least 60 seconds for REGIONAL and
   5 minutes for CLOUDFRONT scope.

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

- Confirm the Web ACL exists and capture its current state:
  `aws wafv2 describe-web-acl --id <id> --scope <CLOUDFRONT|REGIONAL> --output json > /tmp/<name>-backup-$(date +%s).json`.
  This backup is the rollback target.
- Check resource associations before modifying rules:
  `aws wafv2 list-resources-for-web-acl --web-acl-arn <arn> --output json`.
  An ACL attached to a production CloudFront distribution or ALB affects
  live traffic immediately upon update.
- Prefer additive changes (add a rule group) over destructive changes
  (delete a rule, switch Allow to Block). Adding a managed rule group in
  COUNT mode first, monitoring for a week, then switching to BLOCK is the
  safe progression. Deleting a rule or changing the default action is a
  live-traffic-impacting change.
- For shadow-rule remediation (Step 2), do NOT delete the shadow rule
  without understanding why it was added. It may be load-bearing for a
  legitimate traffic class (e.g., a partner integration that sends a
  specific header). Replace the broad match with a scoped match before
  removing the rule.
- Web ACL updates are eventually consistent — allow 60 seconds for
  changes to propagate to all edge locations before testing. Do not
  re-deploy or iterate within that window.

## Remediation guidance

### For MISCONFIGURED Web ACLs

1. **Zero-rule ACL (Step 1):** Add `AWSManagedRulesCommonRuleSet` and
   `AWSManagedRulesKnownBadInputsRuleSet` as managed rule group statements
   in BLOCK mode (`OverrideAction: {None: {}}`). Set their priority higher
   (larger number) than any custom Allow rules. Add a rate-based rule.
   Enable logging.

2. **Shadow rule (Step 2):** Either move the custom Allow rule to a
   priority number HIGHER than all managed rule groups (so managed rules
   inspect first), or scope its match pattern to an exact URI (health
   check) instead of a wildcard prefix. Never leave a broad-match Allow
   rule at a lower priority than managed rule groups.

3. **COUNT-mode paralysis (Step 3):** Review sampled requests from the
   COUNT period (1–2 weeks minimum). For false-positive rules, add
   `ExcludedRules` or `RuleActionOverrides`. Switch the remaining rules
   to BLOCK by setting `OverrideAction: {None: {}}`. Do this group by
   group, not all at once — switch CommonRuleSet first, monitor for 48h,
   then the next group.

4. **Missing CommonRuleSet (Step 4):** Add it immediately. There is no
   compensating control that provides equivalent OWASP Top 10 coverage
   with less effort.

### For WEAK Web ACLs

1. Add the missing managed rule groups per the coverage matrix (Step 4).
   Priority: CommonRuleSet (if absent — MISCONFIGURED), then
   KnownBadInputsRuleSet, then SQLiRuleSet.
2. Add a rate-based rule if absent. For resources behind CloudFront/ALB,
   use `AggregateKeyType: FORWARDED_IP` with `HeaderName: X-Forwarded-For`.
3. Enable logging if absent:
   `aws wafv2 put-logging-configuration --resource-arn <arn> --log-destination-configs <cw-log-group-arn>`.
4. Enable `CloudWatchMetricsEnabled` and `SampledRequestsEnabled` on the
   Web ACL and on each rule.

### For ADEQUATE Web ACLs

1. Address the single HIGH gap (add the missing rule group, fix the rate
   rule's aggregate key, or enable sampled requests).
2. Consider adding paid add-ons (Bot Control for bot mitigation, ATP for
   login endpoints) if the application's threat model warrants them.
3. Review `ExcludedRules` for over-exclusion and tighten if a Top-10
   OWASP rule is excluded.

### For OK Web ACLs

1. No remediation required for current posture.
2. Periodically review `ExcludedRules` and `RuleActionOverrides` — AWS
   updates managed rule groups, and an exclusion that was safe may become
   a gap when the group adds new rules that would have been useful.
3. Review sampled requests quarterly to detect new false-positive patterns
   and emerging attack signatures.

## Recent AWS features (2024-2026)

- **Bot Control API (2024):** AWS WAF Bot Control now exposes API-based bot classification and reputation scoring. Auditors should verify that Bot Control managed rule groups are deployed on public-facing Web ACLs and that the rule group uses `BLOCK` (not `COUNT`) for known bot categories.
- **CAPTCHA and Challenge action enhancements (2024-2025):** WAF CAPTCHA and Challenge actions now support more configuration options including interstitial page customization and mobile SDK support. Auditors should verify that CAPTCHA/Challenge actions are used on sensitive endpoints (login, registration) and that the challenge timeout is appropriate.
- **Rate-based rule improvements (2024):** Rate-based rules now support custom keys (header, query parameter, cookie) for more granular rate limiting. Auditors should verify that rate-based rules use the correct aggregation key — a rate rule keyed on `ip` may miss attackers behind a shared NAT, while a rule keyed on a session header may be bypassed by rotating headers.
- **ATP (Account Takeover Protection) updates (2024-2025):** Enhanced ATP with credential checking against known-breached password databases and suspicious login pattern detection. Auditors should verify that ATP managed rule groups are deployed on authentication endpoints.
- **WAF integration with CloudFront and API Gateway (2024):** Expanded WAF integration with support for more request inspection points. Auditors should verify that WAF Web ACLs are attached to both CloudFront distributions and API Gateway stages for defense-in-depth.

## References

See `references/managed-rule-group-reference.md` for the full managed rule
group catalog, per-group rule lists, `RuleActionOverrides` syntax, and the
`put-logging-configuration` / `associate-web-acl` CLI commands.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern, with sections in
this canonical order:

1. **Frontmatter** — name, description, version, metadata.
2. **Mindset** — the failure modes the skill hunts for.
3. **Quick reference** — fast triage shortcuts.
4. **Classification logic** — the ordered decision tree (Steps 0–11).
5. **Coverage / transformation matrices** — depth references.
6. **Output format** — the fixed per-ACL report shape.
7. **NEVER** — anti-patterns with explicit *why* each is wrong.
8. **Pre-flight safety checks** — non-destructive operation guards.
9. **Remediation guidance** — per-verdict action plan.
10. **References** — pointer to deeper references.

## Domain

AWS CloudOps / WAF Security & Compliance.

## AWS documentation

- **AWS WAF Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **WAF Security** — https://docs.aws.amazon.com/waf/latest/developerguide/security.html
- **WAF API Reference (v2)** — https://docs.aws.amazon.com/waf/latest/APIReference/
- **AWS CLI — wafv2** — https://docs.aws.amazon.com/cli/latest/reference/wafv2/
- **Bot Control** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-bot.html
- **ATP managed rule group** — https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html
