---
description: Audit a WAFv2 Web ACL configuration for default-action posture, managed-rule-group coverage gaps, rule effectiveness (BLOCK vs COUNT, shadow rules), rate-based rule correctness, logging, and visibility.
nl_triggers:
  - "audit my WAF"
  - "WAFv2 web acl"
  - "check my WAF rules"
  - "managed rule coverage"
  - "WAF count mode"
  - "rate-based rule"
  - "WAF logging"
  - "web acl security"
  - "OWASP WAF"
  - "shadow rule bypass"
  - "OverrideAction count"
  - "forwarded IP WAF"
  - "Bot Control rule"
  - "CAPTCHA rule WAF"
  - "text transformation bypass"
  - "WAF visibility config"
routes_to: wafv2-web-acl-auditor
---

# /aws:audit-wafv2-web-acl

Activate the `wafv2-web-acl-auditor` skill and audit one or more WAFv2 Web ACL
configurations against effective-protection principles.

## What it does

Reads a WAFv2 Web ACL configuration (JSON from `describe-web-acl`, pasted inline
or read from file) and applies the 11-step classification logic in declaration
order:

1. Validate input and check `Scope` (CLOUDFRONT must be `us-east-1`).
2. Zero-rule open door (`DefaultAction: Allow` + no managed rule groups).
3. Shadow / bypass rules (custom Allow at lower priority than managed groups).
4. COUNT-mode paralysis (`OverrideAction: {Count: {}}` on managed groups).
5. Baseline managed-rule coverage (CommonRuleSet required; coverage matrix).
6. Rate-based rule correctness (AggregateKeyType, FORWARDED_IP behind proxy).
7. Logging configuration (CloudWatch / Firehose / S3 destination present).
8. Visibility config (CloudWatchMetrics + SampledRequests on ACL + per-rule).
9. Rule action and statement correctness (transformations, positional constraints).
10. CAPTCHA / Challenge ImmunityTime and fallback rules.
11. Managed-rule-group exclusions (ExcludedRules over-exclusion).

Emits a deterministic VERDICT per Web ACL:

```text
WEBACL: <name>
VERDICT: MISCONFIGURED | WEAK | ADEQUATE | OK
REASON: <1-3 sentences citing the specific step, finding, and config>
RISK: CRITICAL | HIGH | MODERATE | LOW
GAPS: <comma-separated list of gap IDs, or "None" if OK>
REMEDIATION: <specific action(s), or "None required" if OK>
```

## When to invoke

Paste a Web ACL config and ask any of:

- "audit my WAF"
- "is my WAF actually protecting anything?"
- "check managed-rule coverage"
- "are my WAF rules in count mode?"
- "does my rate-based rule work behind CloudFront?"
- "hardening my WAF before production"

A bare WAF / Web ACL name + any audit verb ("audit this web acl", "check WAF
rules") also routes here via the orchestrator.

## Inputs

- A WAFv2 Web ACL configuration (JSON from `aws wafv2 describe-web-acl`),
  pasted inline or referenced by file path.
- Optional: the `LoggingConfiguration` block (from
  `aws wafv2 get-logging-configuration`) and the associated-resources list
  (from `aws wafv2 list-resources-for-web-acl`).

## Outputs

- One VERDICT block per Web ACL.
- Specific remediation: rule-group additions, OverrideAction fixes, shadow-rule
  reprioritization, rate-rule aggregate-key corrections, logging enablement.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the Phase 2
  Audit specialist for WAFv2).
- `references/managed-rule-group-reference.md` for the managed rule group
  catalog, per-group rule lists, and CLI commands.
