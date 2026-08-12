# Eval prompt: severity-routing-lambda

Design a severity-based anomaly routing pipeline using a Lambda router.
Emit the standard ANOMALY block (MONITOR, SUBSCRIPTION, ROUTING,
REMEDIATION, AUDIT, VERDICT, TEMPLATE).

Design reference: severity-routing-lambda
Account: 111111111111
Region: us-east-1

Requirement: route anomalies by severity.
- Critical (>=50% deviation): page on-call via PagerDuty (SNS -> Lambda -> PagerDuty).
- High (20-50%): notify Slack #finops-alerts (SNS -> Lambda -> Slack webhook).
- Low (<20%): log to CloudWatch dashboard (Lambda logs only).

Lambda router: arn:aws:lambda:us-east-1:111111111111:function:cost-anomaly-router
Slack webhook: configured via Lambda env var SLACK_WEBHOOK_URL.
Anomaly feedback: auto-submit true positive for impact >= $200.

Include the Lambda severity routing logic, SNS fan-out wiring, and the
three subscription tiers.
