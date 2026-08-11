# Eval prompt: cad-notify-slack-full-playbook

Design an automated cost-anomaly response for the following scenario.
Emit the standard design block (DETECTION_SOURCE, RESPONSE_SCOPE,
VERDICT, WORKFLOW, GUARDRAILS, AUDIT, FINDINGS, REMEDIATION).

Scenario: cad-notify-slack-full-playbook

Detection source: CAD (Cost Anomaly Detection)
Response scope: full-playbook (notify Slack, tag suspect resources,
  wait for approval, run budget action)
Monitor: ec2-spend-monitor (SERVICE type, daily cadence)
Anomaly subscription: prod-cost-anomaly-sub (USD 100 threshold)
SNS topic: arn:aws:sns:us-east-1:111122223333:cost-anomaly-alerts
Slack webhook: stored in Parameter Store /cost/slack-webhook
Kill-switch: Parameter Store /cost/kill-switch (enabled)
Dry-run: completed 2026-07-15 to 2026-07-29 (notify-only)
Approval gate: SQS task-token callback before EC2 stop
IAM: Lambda role scoped to ce:GetAnomalies, sns:Publish,
  resourcegroupstaggingapi:TagResources, budgets:ExecuteBudgetAction
Idempotency: DynamoDB cost-anomaly-dedupe keyed by AnomalyId
