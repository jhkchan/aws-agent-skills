# Eval prompt: cross-account-kms-gap-manual

Design a cross-account CI/CD pipeline (source account 111111111111
deploys to target account 222222222222) and emit the standard
VERDICT block.

Operation: create
Pipeline name: cross-account-deploy-pipeline
Source: GitHub (CodeStar Connection)
Build image: aws/codebuild/standard:8.0
Deploy target: CloudFormation stack in target account 222222222222
  via deploy role arn:aws:iam::222222222222:role/target-deploy
Source account: 111111111111
Artifact KMS key: arn:aws:kms:us-east-1:111111111111:key/abc
Artifact bucket: prod-checkout-artifacts (in source account)

```json
{
  "RequirementChecks": {
    "codestar-connections.get-connection": {"ConnectionStatus": "Available"},
    "iam.get-role.target-deploy": {
      "TrustPolicy": "codepipeline.amazonaws.com with aws:SourceAccount=111111111111 condition (OK)"
    },
    "kms.describe-key.abc": {
      "KeyPolicy": "DOES NOT include account 222222222222 (FAIL)",
      "gap": "missing cross-account grant for kms:Decrypt, kms:GenerateDataKey"
    },
    "s3api.get-bucket-versioning.prod-checkout-artifacts": {"Status": "Enabled"},
    "s3api.get-bucket-policy.prod-checkout-artifacts": {
      "includes_account_222222222222": true,
      "actions": ["s3:GetObject"]
    },
    "codebuild.list-curated-environment-images.standard:8.0": {
      "supports": ["nodejs:20"]
    }
  }
}
```
