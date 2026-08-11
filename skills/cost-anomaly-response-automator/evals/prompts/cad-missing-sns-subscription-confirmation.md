# Eval prompt: cad-missing-sns-subscription-confirmation

Design an automated cost-anomaly notification workflow for the
following scenario. Emit the standard design block (DETECTION_SOURCE,
RESPONSE_SCOPE, VERDICT, WORKFLOW, GUARDRAILS, AUDIT, FINDINGS,
REMEDIATION).

Scenario: cad-missing-sns-subscription-confirmation

Detection source: CAD
Response scope: notify (email + Slack)
Monitor: total-spend-monitor (DIMENSION, daily)
Subscription threshold: USD 500
SNS topic: arn:aws:sns:us-east-1:111122223333:cost-alerts (newly created)
SNS subscriptions:
  - email: finops@corp.example (Status: PendingConfirmation)
  - Lambda: cost-slack-forwarder (Status: confirmed)
Kill-switch: Parameter Store /cost/kill-switch (enabled)
Dry-run: not yet started.
