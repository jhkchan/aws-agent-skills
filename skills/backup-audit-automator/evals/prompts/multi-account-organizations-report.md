# Eval: multi-account-organizations-report

**Difficulty:** hard
**Branch:** AUTOMATION_DEPLOYED — all accounts in Org, all regions, CIS framework, SNS alerts

## Prompt

Create an organization-wide backup compliance report. I need
COMPLIANCE_REPORT delivered daily to
s3://org-backup-reports/compliance/ covering ALL accounts in my
Organization (5 accounts) and ALL regions. Framework: CIS_AWS_1.4.
SNS alerts to arn:aws:sns:us-east-1:123456789012:org-backup-alerts.
Management account: 123456789012. Region us-east-1.
