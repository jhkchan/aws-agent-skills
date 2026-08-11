# Eval prompt: delegate-allowlist-ready-with-warning

Plan the following delegate-strategy SCP deployment and emit the
standard VERDICT block. The user is replacing FullAWSAccess at the
root with a comprehensive allowlist. Plan MUST attach the allowlist
FIRST and detach FullAWSAccess SECOND, with an explicit lockout
warning in FINDINGS.

Operation: deploy-scp
Policy name: allowlist-approved-services
Strategy: delegate
Target: r-abc1 (root)
Approved services: ec2, s3, rds, lambda, iam, logs, kms, dynamodb,
  sns, sqs, sts, secretsmanager, ssm, efs
Order requirement: attach allowlist BEFORE detaching FullAWSAccess

```json
{
  "OrgState": {
    "describe-organization": {
      "Organization.FeatureSet": "ALL_FEATURES"
    },
    "list-roots.PolicyTypes": [
      {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
    ],
    "list-policies-for-target.r-abc1": [
      {"Name": "FullAWSAccess", "AwsManaged": true}
    ],
    "caller_iam": {
      "role": "AWSOrgAdminRole",
      "permissions": ["organizations:CreatePolicy", "organizations:AttachPolicy", "organizations:DetachPolicy"]
    }
  }
}
```
