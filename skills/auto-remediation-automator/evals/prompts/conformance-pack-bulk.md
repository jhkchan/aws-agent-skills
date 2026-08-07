# Eval prompt: conformance-pack-bulk

Design an automated remediation baseline using a conformance pack.
Emit the standard REMEDIATION block (RULE, RESOURCE_TYPE, WORKFLOW,
TRIGGER, SAFETY, AUDIT, VERDICT, TEMPLATE).

Design reference: conformance-pack-bulk
Account: 111111111111
Region: us-east-1

Requirements: deploy a security baseline covering
- s3-bucket-public-read-prohibited -> AWS-DisableS3BucketPublicAccess
- s3-bucket-server-side-encryption-enabled -> AWS-EnableS3BucketEncryption
- s3-bucket-versioning-enabled -> AWS-EnableS3BucketVersioning
All three are AWS-managed, reversible, and validated in pre-prod.

SSM service role ARN: arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole

Include the conformance-pack YAML template with RemediationConfiguration
resources for each rule.
