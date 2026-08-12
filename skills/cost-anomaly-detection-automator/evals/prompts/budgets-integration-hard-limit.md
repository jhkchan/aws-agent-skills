# Eval prompt: budgets-integration-hard-limit

Design a Budgets integration for hard spend limits alongside the existing
Cost Anomaly Detection setup. Emit the standard ANOMALY block (MONITOR,
SUBSCRIPTION, ROUTING, REMEDIATION, AUDIT, VERDICT, TEMPLATE).

Design reference: budgets-integration-hard-limit
Account: 111111111111
Region: us-east-1

Requirement: set up a monthly cost budget of $10,000 with threshold
alerts at 80% actual spend and 100% forecast. Also keep the existing
Cost Anomaly Detection monitor for pattern-based anomalies.

Existing anomaly monitor: ec2-spend-anomaly-monitor (ACTIVE, DIMENSION
SERVICE, threshold 50% IMMEDIATE).
SNS topic for budget alerts: arn:aws:sns:us-east-1:111111111111:budget-alerts

Include the Budget creation CLI and explain how Budgets and Cost Anomaly
Detection are complementary (not redundant).
