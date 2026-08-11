---
name: deploy-budget
description: >-
  Slash command for the budget-deployer skill. Provisions AWS Budgets
  and Cost Anomaly Detection with production defaults: cost budgets
  (fixed/threshold, actual vs forecast alerts), usage budgets (RI/SP
  utilization, RI/SP coverage), cost anomaly detection (service
  monitors, subscriptions), budget actions (apply/remove IAM policy,
  stop EC2/RDS, SNS), threshold tiering (80/90/100%), cost filters
  (service, linked account, tag, region). Emits
  READY_TO_DEPLOY | PREREQUISITES_MISSING with the budget type, scope,
  action tier, and SNS wiring.
skill: budget-deployer
family: FinOps
task_type: deploy
verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:deploy-budget

Invoke the `budget-deployer` skill to provision AWS Budgets, Budget
Actions, or Cost Anomaly Detection.

Read the skill at `skills/budget-deployer/SKILL.md` and follow its
10-step provisioning procedure to emit a READY_TO_DEPLOY checklist.

## When to use

- You need to create a cost budget with thresholds (fixed or zero-spend).
- You want to set RI or Savings Plan utilization/coverage targets with
  alerting when they drop below the target.
- You want to wire Budget Actions (apply/remove IAM policy, stop EC2/RDS,
  SNS) at a specific threshold.
- You need Cost Anomaly Detection with a subscription to SNS or email.
- You need to scope a budget to a linked account, service, tag, or
  region via CostFilters.
- You want to validate that a budget design meets production baseline
  (SNS topic policy includes both budgets.amazonaws.com AND
  ce.amazonaws.com, action role trust verified, threshold tiering
  80/90/100 + FORECAST).

## Invocation

```
/aws:deploy-budget <budget name / scenario description>
```

The skill will:

1. Capture intent: budget type (COST / RI_UTILIZATION / RI_COVERAGE /
   SP_UTILIZATION / SP_COVERAGE / ANOMALY), scope, amount, time period,
   action tier, thresholds.
2. Verify prerequisites: account ID, SNS topic ARN + policy, action
   role with trust on budgets.amazonaws.com, KMS key policy if SSE-KMS.
3. Walk the 10-step provisioning procedure (budget definition ->
   notifications -> actions -> SNS -> anomaly -> filters -> verification).
4. Emit the standard VERDICT block with copy-pasteable CLI commands.

## Output shape

```text
BUDGET: <budget-name> in <account / scope>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [y|n] Budget type: COST | RI_UTILIZATION | RI_COVERAGE | SP_UTILIZATION | SP_COVERAGE | ANOMALY
  [y|n] Scope: <account | linked account | service | tag | region>
  [y|n] Amount / target: <$amount for COST | % for USAGE>
  [y|n] Time period: MONTHLY | DAILY | QUARTERLY | ANNUALLY
  [y|n] Alerts: <NotificationType + Threshold per notification>
  [y|n] Budget actions: <action type + threshold + target>
  [y|n] Action execution role: <ARN, trust verified>
  [y|n] SNS topic: <ARN, policy verified>
  [y|n] Cost anomaly monitor + subscription: <ARNs>
  [y|n] Cost filters: <list | none>
VERIFICATION_COMMANDS:
  aws budgets describe-budget ...
  aws budgets describe-notifications-for-budget ...
  aws budgets describe-budget-actions ...
  aws ce get-anomaly-subscriptions ...
  aws sns get-topic-attributes ...
```

## Pre-flight

The skill requires the AWS account ID and (for SNS/action paths) the
SNS topic ARN. If the user provides only a partial intent, the skill
emits `VERDICT: PREREQUISITES_MISSING` with the specific gaps cited
(ExecutionRoleArn missing, SNS topic policy lacks
budgets.amazonaws.com, etc.).

## References

- Skill: `skills/budget-deployer/SKILL.md`
- Reference: `skills/budget-deployer/references/provisioning-cli-commands.md`
- Reference: `skills/budget-deployer/references/budget-types-and-actions.md`
- AWS docs: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
