# Eval prompt: deploy-conformance-pack-ready

Plan the following AWS Config conformance pack deployment and emit the
standard VERDICT block (RULE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, EVALUATION, COMPLIANCE, REMEDIATION, NOTES).

Operation: create
Conformance pack name: cis-aws-foundations-benchmark
Type: conformance-pack
Rules:
  - iam-no-inline-policy (IAM_NO_INLINE_POLICY_CHECK, scope: AWS::IAM::User)
  - root-mfa-enabled (ROOT_ACCOUNT_MFA_ENABLED, periodic: One_Hour)
  - iam-password-policy (IAM_PASSWORD_POLICY, periodic: Six_Hours)
  - multi-region-cloudtrail-enabled (MULTI_REGION_CLOUD_TRAIL_ENABLED, periodic: One_Hour)
  - cloudtrail-enabled (CLOUD_TRAIL_ENABLED, periodic: One_Hour)
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
  "ConformancePackChecks": {
    "template-body-size": "2.1 KB",
    "all-managed-rules-valid": true,
    "describe-conformance-packs.count": 3,
    "count-after-deploy": 4
  },
  "ExistingPack": null
}
```
