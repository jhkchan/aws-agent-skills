# Eval prompt: org-payer-coverage-gap

Assess the following multi-account Cost Anomaly Detection setup and
emit the standard ANOMALY block (MONITOR, SUBSCRIPTION, ROUTING,
REMEDIATION, AUDIT, VERDICT, GAP, TEMPLATE).

Design reference: org-payer-coverage-gap
Payer account: 111111111111
Region: us-east-1

Existing monitor: org-payer-anomaly-monitor (ACTIVE, DIMENSION SERVICE,
covers all linked accounts).
Existing subscriptions: NONE.
Lambda router: NOT deployed.
SNS topic: NOT created.
Slack webhook: NOT configured.
Linked accounts: 222222222222 (dev), 333333333333 (prod).

The operator says "we have anomaly detection configured" because the
monitor shows as ACTIVE in the console.
