# Eval: daily-compliance-report-sns-alerting

**Difficulty:** hard
**Branch:** AUTOMATION_DEPLOYED — three report templates, S3 delivery, CIS/NIST frameworks, SNS failure alerts

## Prompt

Set up a daily backup compliance audit for my account
123456789012. I need all three report templates
(BACKUP_JOB_REPORT, COMPLIANCE_REPORT, RECOVERY_POINT_REPORT)
delivered to s3://backup-reports-bucket/reports/. Frameworks:
CIS_AWS_1.4 and NIST_800_53. SNS alerts for backup failures to
arn:aws:sns:us-east-1:123456789012:backup-alerts. Region
us-east-1. Tags: Environment=production, Compliance=CIS.
