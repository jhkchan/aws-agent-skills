# Eval prompt: deploy-managed-s3-rule-ready

Plan the following AWS Config rule creation and emit the standard
VERDICT block (RULE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, EVALUATION, COMPLIANCE, REMEDIATION, NOTES).

Operation: create
Rule name: s3-bucket-public-read-prohibited
Type: managed
ManagedRuleIdentifier: S3_BUCKET_PUBLIC_READ_PROHIBITED
Scope: AWS::S3::Bucket
Region: us-east-1
Account: 111111111111

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
      "s3BucketName": "config-bucket-111111111111",
      "bucketExists": true
    }
  },
  "RuleChecks": {
    "describe-config-rules.s3-bucket-public-read-prohibited": {
      "status": "NoSuchConfigRule",
      "exists": false
    },
    "describe-config-rules.count": 12
  },
  "ManagedRuleValid": true,
  "ExistingRule": null
}
```
