# Eval prompt: iam-unused-key-revoke

Design an automated remediation workflow for the following AWS Config
finding. Emit the standard REMEDIATION block (RULE, RESOURCE_TYPE,
WORKFLOW, TRIGGER, SAFETY, AUDIT, VERDICT, TEMPLATE).

Design reference: iam-unused-key-revoke
Account: 111111111111
Region: us-east-1

Config rule: iam-access-no-unused-access-keys (AWS-managed, periodic)
Scope: AWS::IAM::User
Sample NON_COMPLIANT resource: deployment-user (key AKIAXYZ aged 95 days unused)
Recorder scope: includeGlobalResourceTypes=true.
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Pre-prod validation: completed.

Note: the key has been unused for 95 days per the IAM credential
report. No application depends on it.
