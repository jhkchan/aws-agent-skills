# Eval: standard-expiry-monitoring

**Difficulty:** medium
**Branch:** OPERATION_COMPLETED — 5 issued certs, warning (<30d) and critical (<7d) alarms, SNS topics, renewal eligibility and DNS validation checked

## Prompt

Set up certificate expiry monitoring for my ACM certificates
in us-east-1, account 123456789012. I have 5 issued
certificates. Create DaysToExpiry alarms with warning at 30
days and critical at 7 days. Warning SNS topic
arn:aws:sns:us-east-1:123456789012:cert-warning-notifications,
critical SNS topic
arn:aws:sns:us-east-1:123456789012:cert-critical-escalation.
Check renewal eligibility and DNS validation status.
