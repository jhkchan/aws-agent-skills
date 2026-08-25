# Worked examples - Cost Anomaly Response Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — MANUAL_STEP_REQUIRED (missing approval gate)

```text
DETECTION_SOURCE: budgets
RESPONSE_SCOPE: budget-action
VERDICT: MANUAL_STEP_REQUIRED
WORKFLOW: (partial — blocked)
GUARDRAILS:
  - [PASS] Kill-switch: Parameter Store /cost/kill-switch
  - [FAIL] No approval gate — Budgets EC2 stop runs AUTOMATIC at 120%
  - [PASS] IAM role scoped to budgets:ExecuteBudgetAction
AUDIT:
  - [PASS] CloudTrail covers the account; Budgets action execution logged
FINDINGS:
  - [CRITICAL] No approval gate: a breach at 120% auto-stops instances with
    no human check. A billing-cycle lag (CUR delivery 8-24h) could trigger
    the stop after spend has already returned to normal.
  - [HIGH] Action lists i-0abc12345 only — horizontally scaled instances
    are NOT covered.
REMEDIATION:
  1. Move EC2 stop from 120% AUTOMATIC to 120% MANUAL:
     aws budgets put-budget-action --account-id 111122223333 \
       --budget-name monthly-ec2-budget --notification-type ACTUAL \
       --action-type RUN_SSM_DOCUMENTS --approval-model MANUAL
  2. Add a notify-only action at 100% so on-call is paged before stop.
  3. Tag EC2 with BudgetsActionMonitored=true; audit monthly.
```
