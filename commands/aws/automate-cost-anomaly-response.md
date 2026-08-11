---
description: Designs automated AWS cost-anomaly detection and response workflows across Cost Anomaly Detection (CAD) monitors, anomaly subscriptions (SNS), EventBridge to Lambda response patterns (notify Slack/Teams, tag resources), AWS Budgets native actions (IAM policy attach, EC2 stop), Cost Explorer anomaly views, and CUR Athena top-spenders analysis. Enforces guardrails — dry-run, approval gate for resource-stopping actions, scoped IAM, kill-switch, full CloudTrail audit. Emits AUTOMATED with response plan or MANUAL_STEP_REQUIRED with the specific gap.
nl_triggers:
  - "automate cost anomaly response"
  - "Cost Anomaly Detection to Slack"
  - "Budgets action on cost overrun"
  - "SNS alert on spend anomaly"
  - "EventBridge Lambda cost remediation"
  - "stop EC2 on budget breach"
  - "IAM deny policy budget action"
  - "CUR Athena top spenders"
  - "Amazon Q cost optimization"
  - "cost budget auto-action"
  - "tag resources on anomaly"
  - "anomaly subscription SNS"
  - "Cost Optimization Hub recommendations"
routes_to: cost-anomaly-response-automator
---

# /aws:automate-cost-anomaly-response

Activate the `cost-anomaly-response-automator` skill and produce a
cost-anomaly detection and response workflow design (or validation
report).

## What it does

Reads a detection source (CAD, AWS Budgets, Cost Explorer anomaly
view, CUR Athena analysis, Amazon Q / Cost Optimization Hub
recommendations), a response scope (notify, tag, budget-action,
cur-analysis, or full-playbook), and either:

1. **Designs** a complete workflow with: CAD monitor and subscription,
   Budgets native action, EventBridge rule + Lambda (notify, tag,
   CUR query), Step Functions state machine for full-playbook,
   scoped IAM roles, kill-switch, dry-run plan, and approval gate.
2. **Validates** an existing workflow against the mandatory guardrail
   baseline (kill-switch required, dry-run window, scoped IAM,
   approval gate before resource-stopping actions, idempotency,
   CloudTrail audit).

Emits a deterministic block per workflow:

```text
DETECTION_SOURCE: <cad | budgets | ce-anomaly | cur | q-recommendations>
RESPONSE_SCOPE: <notify | tag | budget-action | cur-analysis | full-playbook>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
WORKFLOW:
  Detection: <monitor or budget name + ARN>
  EventBridge rule: <name or "n/a (Budgets native)">
  Lambda / Step Functions: <arn or name>
  Budgets action: <action name or "none">
  SNS topic: <arn>
  Notification target: <Slack / Teams / email / PagerDuty>
GUARDRAILS:
  - [PASS|FAIL] Dry-run mode implemented
  - [PASS|FAIL] Approval gate before resource-stopping action
  - [PASS|FAIL] Scoped IAM (least privilege)
  - [PASS|FAIL] Idempotency check on Lambda
  - [PASS|FAIL] Kill-switch (Parameter Store or EventBridge disable)
AUDIT:
  - [PASS|FAIL] CloudTrail covers the account
  - [PASS|FAIL] Notification includes anomaly ID + impact USD
  - [PASS|FAIL] Budgets action execution logged
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide a detection source + response scope and ask any of:

- "automate cost anomaly response for EC2 spend over USD 500"
- "notify Slack on any CAD anomaly"
- "wire Budgets EC2 stop action at 120% with approval gate"
- "build a CUR Athena top-spenders daily Slack digest"
- "validate our existing cost-response workflow for guardrail gaps"
- "add Cost Optimization Hub recommendations to our FinOps Slack"

A bare detection source + response scope + "automate" routes here via
the orchestrator.

## Inputs

- **Required:** detection_source (cad | budgets | ce-anomaly | cur |
  q-recommendations), response_scope (notify | tag | budget-action |
  cur-analysis | full-playbook).
- **Recommended:** severity_threshold (default 100 USD / 80% budget),
  target_regions (Budgets actions are per-region), approval_required
  (required true for resource-stopping actions).
- **For validation mode:** existing_workflow (EventBridge rule JSON +
  Lambda/Step Functions definition + IAM role policy JSON).

## Outputs

- One VERDICT block per workflow (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete workflow design (CAD monitor, subscription, Budgets
  action, EventBridge rule, Lambda stubs, Step Functions ASL, IAM
  role policies) in WORKFLOW.
- Guardrail pass/fail per dimension in GUARDRAILS.
- Audit pass/fail per dimension in AUDIT.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for FinOps cost response).
- `/aws:audit-ce-cost-anomaly` for CAD subscription posture audits
  (this skill designs automation; the auditor reviews configuration).
- `/aws:audit-budgets` for budget threshold posture (a detection
  source for this skill's workflows).
- `/aws:audit-cur-cost-usage-report` for CUR configuration posture
  (required for the Athena top-spenders analysis).
