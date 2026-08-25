# Worked Examples (load on demand) — Cost Anomaly Detection Automator

Secondary worked examples and full CLI payloads moved verbatim from SKILL.md. Loaded on demand.

---

## Worked example — REVIEW_REQUIRED, monitor without subscription (moved from SKILL.md)

```text
ANOMALY: org-payer-coverage-gap
MONITOR:
  - Name: org-payer-anomaly-monitor
  - Type: DIMENSION (SERVICE, all services)
  - Status: ACTIVE
  - Scope: All linked accounts under payer 111111111111
SUBSCRIPTION:
  - Severity routing: NONE — no subscription created
  - Endpoints: NONE
  - Frequency: N/A
ROUTING:
  - Critical: NOT WIRED
  - High: NOT WIRED
  - Low: NOT WIRED
REMEDIATION:
  - Actions: NONE
  - Lambda: NOT WIRED
AUDIT:
  - Budgets: NONE at org level
  - Feedback: NONE
VERDICT: REVIEW_REQUIRED
GAP: Monitor is ACTIVE but has zero subscriptions. Anomalies are detected silently. Create subscriptions (Step 3), wire SNS fan-out (Step 4), deploy Lambda router (Step 5). For multi-account, add per-linked-account routing (Step 7).
TEMPLATE: (see Steps 3-5)
```
