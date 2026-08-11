# Eval prompt: codecommit-codebuild-cloudformation

Design a deployment plan for a production CodePipeline V2. Emit the
standard VERDICT block (PIPELINE_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Pipeline type: V2 (event-driven, no polling)
- Region: us-east-1
- Pipeline name: my-service-pipeline
- Source: CodeCommit repository `my-service`, branch `main`
- Build: CodeBuild project `my-service-build`, exports IMAGE_URI and
  IMAGE_TAG via `exported-variables` in buildspec
- Deploy: CloudFoundation CREATE_REPLACE on stack `prod-my-service`
  in same account (111111111111), template at
  `BuildOutput::template.yaml`, capabilities CAPABILITY_IAM
- Trigger: branch filter Includes=[main, "release/*"], FilePaths
  Excludes=[docs/**, README.md]
- Namespace variables: IMAGE_URI flows from Build (Namespace=BuildVars)
  to Deploy (ParameterOverrides uses #{BuildVars.IMAGE_URI})
- Artifact bucket: `my-pipeline-artifacts` with block-public-access,
  KMS CMK encryption (key arn:aws:kms:us-east-1:111111111111:key/abc),
  versioning enabled
- Pipeline role: scoped to the CodeCommit repo, CodeBuild project,
  CloudFormation stack, KMS key, and S3 artifact bucket (no wildcards)

Existing-account context: the CodeBuild project `my-service-build`
exists and is configured with the correct buildspec. The CloudFormation
stack `prod-my-service` exists in the account. The KMS key was created
earlier and is shared with another pipeline. The artifact bucket does
NOT exist yet — the skill should emit create-bucket + put-bucket-encryption
+ put-bucket-versioning commands.
