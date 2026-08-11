# Eval prompt: critical-s3-auto-remediation

Design an automated Security Hub remediation workflow for the following
finding. Emit the standard REMEDIATION block (FINDING_TYPE, STANDARD,
SEVERITY_ROUTE, RUNBOOK, TRIGGER, SAFETY, SUPPRESSION, VERDICT, TEMPLATE).

Design reference: critical-s3-auto-remediation
Account: 111111111111
Region: us-east-1

Standard: AWS Foundational Security Best Practices (ACTIVE)
Finding type: S3.1 (S3 bucket publicly accessible)
Severity: CRITICAL
Sample finding resource: arn:aws:s3:::app-data-bucket-prod
EventBridge detail-type: Security Hub Findings - Imported
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Pre-prod validation: completed (3 buckets tested, all remediated and
findings closed via batch-update-findings).
