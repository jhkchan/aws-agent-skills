# Eval prompt: deploy-proactive-rule-ready

Plan the following proactive Config rule deployment and emit the
standard VERDICT block (RULE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, EVALUATION, COMPLIANCE, REMEDIATION, NOTES).

Operation: create
Rule name: proactive-s3-public-read-block
Type: proactive (CloudFormation hook)
ManagedRuleIdentifier: S3_BUCKET_PUBLIC_READ_PROHIBITED
ResourceTypes: ["AWS::S3::Bucket"]
TargetOperations: ["CREATE", "UPDATE"]
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
  "HookChecks": {
    "cloudformation.list-types.HOOK": {
      "typeName": "CfnHook::Config::ProactiveRule",
      "registered": true,
      "version": "1",
      "defaultVersion": "1"
    }
  },
  "SecurityHubChecks": {
    "securityhub.get-enabled-standards": {
      "enabled": true,
      "controlsEnabled": true
    }
  },
  "RuleChecks": {
    "describe-config-rules.count": 15
  },
  "ExistingRule": null
}
```
