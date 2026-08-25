# Diagnostic commands - CodePipeline V2 Deployer (load on demand)

## Verification commands (run after deployment)

```bash
aws codepipeline get-pipeline --name <name>
aws codepipeline get-pipeline-state --name <name>
aws codepipeline list-action-executions --pipeline-name <name> --region <region>

# Trigger / artifact / KMS / role verification
aws s3api get-public-access-block --bucket <bucket>
aws s3api get-bucket-encryption --bucket <bucket>
aws s3api get-bucket-versioning --bucket <bucket>
aws kms describe-key --key-id <key-id> && aws kms get-key-policy --key-id <key-id> --policy-name default
aws iam get-role --role-name <pipeline-role> && aws iam list-attached-role-policies --role-name <pipeline-role>

# Trigger a test execution
aws codepipeline start-pipeline-execution --name <name>
```

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before `create-pipeline`, the
  deployer MUST emit:
  `CONFIRM: About to create pipeline <name> in <region>. This
  provisions IAM roles, KMS keys, and an S3 artifact bucket. Proceed?
  (yes/no)`
- **Trigger filter.** Verify the trigger has at least one of
  `Branches.Includes`, `FilePaths.Includes`, `Tags.Includes`.
- **Cross-account KMS.** KMS key policy grants the target role
  `kms:Decrypt` and `kms:GenerateDataKey`; artifact bucket policy
  grants `s3:GetObject` to the target role.
- **Pipeline IAM role.** No wildcard resources on S3, KMS, CodeBuild,
  or CodeCommit. `iam:PassRole` scoped to the CloudFormation
  execution role.
- **CodeConnections state.** For GitHub / GitLab / Bitbucket, verify
  the connection is in `AVAILABLE` state (not `PENDING`).
- **Cost estimate.** V2 pipeline $0.002/execution + $1/active
  pipeline/month; CodeBuild $0.01/build-minute; S3 artifacts
  $0.023/GB-month + KMS $1/key/month.

