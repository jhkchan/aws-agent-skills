# Eval prompt: s3-public-access-auto

Design an automated remediation workflow for the following AWS Config
finding. Emit the standard REMEDIATION block (RULE, RESOURCE_TYPE,
WORKFLOW, TRIGGER, SAFETY, AUDIT, VERDICT, TEMPLATE).

Design reference: s3-public-access-auto
Account: 111111111111
Region: us-east-1

Config rule: s3-bucket-public-read-prohibited (AWS-managed)
Scope: AWS::S3::Bucket
Sample NON_COMPLIANT resource: app-uploads-bucket-prod
Recorder scope: allSupported=true, includeGlobalResourceTypes=true.
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Pre-prod validation: completed (3 buckets tested, all flipped to COMPLIANT).
