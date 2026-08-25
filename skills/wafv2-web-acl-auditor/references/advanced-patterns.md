# Advanced Patterns - wafv2-web-acl-auditor

## Mindset deep dive: the four failure modes (moved from SKILL.md)

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

## Effective protection context (moved from SKILL.md)

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

## Operational edge cases (moved from SKILL.md)

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

## Recent AWS features 2024-2026 (moved from SKILL.md)

- **Bot Control API (2024):** AWS WAF Bot Control now exposes API-based bot classification and reputation scoring. Auditors should verify that Bot Control managed rule groups are deployed on public-facing Web ACLs and that the rule group uses `BLOCK` (not `COUNT`) for known bot categories.
- **CAPTCHA and Challenge action enhancements (2024-2025):** WAF CAPTCHA and Challenge actions now support more configuration options including interstitial page customization and mobile SDK support. Auditors should verify that CAPTCHA/Challenge actions are used on sensitive endpoints (login, registration) and that the challenge timeout is appropriate.
- **Rate-based rule improvements (2024):** Rate-based rules now support custom keys (header, query parameter, cookie) for more granular rate limiting. Auditors should verify that rate-based rules use the correct aggregation key — a rate rule keyed on `ip` may miss attackers behind a shared NAT, while a rule keyed on a session header may be bypassed by rotating headers.
- **ATP (Account Takeover Protection) updates (2024-2025):** Enhanced ATP with credential checking against known-breached password databases and suspicious login pattern detection. Auditors should verify that ATP managed rule groups are deployed on authentication endpoints.
- **WAF integration with CloudFront and API Gateway (2024):** Expanded WAF integration with support for more request inspection points. Auditors should verify that WAF Web ACLs are attached to both CloudFront distributions and API Gateway stages for defense-in-depth.

## Section taxonomy: CloudOps auditor pattern (moved from SKILL.md)

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

## Text-transformation matrix (moved from SKILL.md Step 8)

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

## Remediation guidance per verdict (moved from SKILL.md)

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

## Step 3 nuance: OverrideAction vs RuleActionOverrides (moved from SKILL.md)

**`RuleActionOverrides` vs `OverrideAction`:** These are different fields.
`OverrideAction` is the blanket rule-level override on the rule that wraps
the managed group statement. `RuleActionOverrides` lives INSIDE the
`ManagedRuleGroupStatement` and selectively overrides individual rules
within the group (e.g., change one rule from BLOCK to COUNT while leaving
the rest in BLOCK mode). A few targeted `RuleActionOverrides` for
false-positive tuning is acceptable; a blanket `OverrideAction: {Count: {}}`
is not.
