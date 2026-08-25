# Worked Examples — GuardDuty Finding Automator

Secondary worked examples moved verbatim from SKILL.md.

## Worked example — REVIEW_REQUIRED, low-severity recon — moved from SKILL.md

```text
AUTOMATION_DEPLOYED: prod-guardduty-auto-response
FINDING_TYPE: Recon:EC2/PortProbeUnprotectedPort
SEVERITY: 2.0 (LOW)
ROUTING: none (Low — log only tier)
REMEDIATION: none (Low — no auto-response)
NOTIFICATION: N/A (Low severity)
INTEGRATION: Security Hub native forwarding only
SAFETY: N/A (no auto-action)
VERDICT: REVIEW_REQUIRED
GAP: Low-severity recon does not warrant auto-response. Recommend: (1) create suppression filter for authorized scanner IPs (Step 10); (2) CloudWatch metric for recon trend analysis (spike detection); (3) CloudTrail correlation — a recon finding followed by a High within 60 min indicates a real attack chain.
TEMPLATE: (suppression filter — see Step 10)
```
