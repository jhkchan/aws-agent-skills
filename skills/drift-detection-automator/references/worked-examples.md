# Worked Examples (load on demand) — Drift Detection Automator

Secondary worked example (REVIEW_REQUIRED) moved verbatim from SKILL.md. The primary worked example stays in SKILL.md.


---

## Worked example — REVIEW_REQUIRED, production stack (moved from SKILL.md)


```text
DRIFT_AUTOMATION: prod-drift-pipeline
STACK: prod-payment-service
DETECTION:
  - Method: EventBridge scheduled (cron 0 2 * * ? *)
  - Cadence: daily at 02:00 UTC
COMPARISON:
  - Lambda: drift-detector
  - Severity: CRITICAL (3 resources: SG modified, IAM policy changed, ALB listener)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts-critical
  - Routing: CRITICAL -> page on-call
REMEDIATION:
  - Method: MANUAL — SSM Change Manager approval required
  - Auto-remediate: BLOCKED (production stack)
SAFETY: production protection active, approval required
VERDICT: REVIEW_REQUIRED
GAP: Production drift detected but auto-remediation intentionally blocked. Operator must review 3 drifted resources. If intentional hotfixes from incident response, update the CFN template to match. If unintentional, create a change-set to revert. Do NOT auto-remediate without approval — re-applying the template may revert an active hotfix and cause a production outage.
TEMPLATE: (SSM Automation with aws:approve gate — see Step 6)
```