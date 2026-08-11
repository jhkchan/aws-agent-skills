# Eval prompt: cross-account-deployment

Design a deployment plan for a cross-account V2 pipeline. Emit the
standard VERDICT block.

Requirements:

- Pipeline type: V2
- Region: us-east-1
- Source account: 111111111111 (where the pipeline lives)
- Target account: 222222222222 (where CloudFormation deploys)
- Pipeline name: my-service-cross-account-pipeline
- Source: CodeCommit repository `my-service`, branch `main`
- Build: CodeBuild `my-service-build` in source account, exports
  IMAGE_URI and IMAGE_TAG
- Deploy: CloudFormation CREATE_REPLACE on `prod-my-service` in
  TARGET account 222222222222, with capabilities CAPABILITY_IAM
- Cross-account role (target account, existing):
  `arn:aws:iam::222222222222:role/CrossAccountCFNExecution`
  - Trust policy principal:
    arn:aws:iam::111111111111:role/my-pipeline-role
- KMS key (existing):
  arn:aws:kms:us-east-1:111111111111:key/abc-123
  - Key policy grants: pipeline role (kms:Decrypt,
    kms:GenerateDataKey, kms:DescribeKey); target role (kms:Decrypt,
    kms:GenerateDataKey)
- Artifact bucket: `my-pipeline-artifacts` (existing, bucket policy
  grants target role s3:GetObject on artifacts/*)
- Pipeline role: `my-pipeline-role` in source account (existing,
  scoped to S3 / KMS / CodeCommit / CodeBuild / sts:AssumeRole on
  target role)
- Trigger: branch main, FilePaths Includes=[src/**]

Existing-account context: all IAM roles, the KMS key, and the artifact
bucket exist and are correctly configured. The CloudFormation stack
`prod-my-service` does NOT exist in the target account yet — the first
deploy will create it. The pipeline does NOT exist yet.
