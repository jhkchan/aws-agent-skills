# Eval prompt: deploy-org-rule-prereqs-missing

Plan the following AWS Config organization rule deployment and emit the
standard VERDICT block (RULE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, EVALUATION, COMPLIANCE, REMEDIATION, NOTES).

Operation: create
Organization rule name: org-s3-public-read-prohibited
Type: organization-config-rule
ManagedRuleIdentifier: S3_BUCKET_PUBLIC_READ_PROHIBITED
ResourceTypesScope: ["AWS::S3::Bucket"]
Region: us-east-1
Account: 222222222222 (attempting from MEMBER account)

```json
{
  "RecorderChecks": {
    "describe-configuration-recorders": {
      "recorder": "default",
      "recording": true,
      "allSupported": true
    },
    "describe-delivery-channels": {
      "channel": "default",
      "s3BucketName": "config-bucket-222222222222",
      "bucketExists": true
    }
  },
  "OrgChecks": {
    "organizations.describe-organization": {
      "status": "AccessDeniedException",
      "reason": "This account (222222222222) is a MEMBER account, not the management account (111111111111). Organization config rules can only be deployed from the management account or a delegated administrator."
    },
    "configservice.describe-organization-config-rules": {
      "status": "AccessDeniedException",
      "reason": "Organization config rules require management account authorization"
    }
  },
  "ExistingRule": null
}
```
