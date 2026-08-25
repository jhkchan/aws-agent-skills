# Worked Examples - waf-rule-deployer

## Worked example: specific allow before broad block (moved from SKILL.md Step 3)

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
