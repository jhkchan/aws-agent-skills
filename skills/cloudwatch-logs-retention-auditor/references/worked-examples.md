# Worked Examples (load on demand) — CloudWatch Logs Retention Auditor

Secondary worked example moved verbatim from SKILL.md. The primary Never-expire worked example remains in SKILL.md.


---

## Worked example — malformed input (ERROR path) (moved from SKILL.md)

When `describe-log-groups` output is truncated or missing required
fields, the audit cannot proceed deterministically. Emit ERROR and stop —
do NOT fabricate a verdict from partial data.

```text
LOG_GROUP: /aws/lambda/checkout-api
VERDICT: ERROR
REASON: Log group metadata is malformed — required field 'retentionInDays'
missing AND 'storedBytes' missing. Cannot classify retention (Step 1) or
cost-risk (Step 3) without one of these.
REMEDIATION: Re-fetch with `aws logs describe-log-groups --log-group-name
/aws/lambda/checkout-api --output json` and re-audit. If the field
genuinely is absent in fresh output, that absence IS the signal — apply
Step 1 (NO_RETENTION) once the data is confirmed.
```
