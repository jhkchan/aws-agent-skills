# Eval prompt: manual-gap-custom-resource

Design an automated remediation workflow for the following AWS Config
finding. Emit the standard REMEDIATION block (RULE, RESOURCE_TYPE,
WORKFLOW, TRIGGER, SAFETY, AUDIT, VERDICT, GAP, TEMPLATE).

Design reference: manual-gap-custom-resource
Account: 111111111111
Region: us-east-1

Config rule: custom-sg-no-open-ingress (custom Lambda rule)
Scope: AWS::EC2::SecurityGroup
Sample NON_COMPLIANT resource: sg-0abc123def (ingress 0.0.0.0/0 on port 22)
Recorder scope: includes AWS::EC2::SecurityGroup.
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Pre-prod validation: NOT completed (no custom runbook yet).
