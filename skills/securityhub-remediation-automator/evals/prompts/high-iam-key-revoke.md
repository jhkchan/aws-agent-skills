# Eval prompt: high-iam-key-revoke

Design an automated Security Hub remediation workflow for the following
finding. Emit the standard REMEDIATION block (FINDING_TYPE, STANDARD,
SEVERITY_ROUTE, RUNBOOK, TRIGGER, SAFETY, SUPPRESSION, VERDICT, TEMPLATE).

Design reference: high-iam-key-revoke
Account: 111111111111
Region: us-east-1

Standard: FSBP (ACTIVE)
Finding type: IAM.3 (IAM access key unused for 90+ days)
Severity: HIGH
Sample finding resource: arn:aws:iam::111111111111:user/ci-deploy-bot
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole

Note: the access key has been unused for 95 days per the IAM credential
report. No application depends on it. Pre-prod validation completed.
