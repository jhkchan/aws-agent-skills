# End-to-end usage scenario: codepipeline-v2-deployer

A walkthrough showing the skill producing a deployment plan for a
production CodePipeline V2 with CodeCommit source, CodeBuild build
exporting namespace variables, CloudFormation cross-account deploy,
event-driven trigger with branch and path filter, manual approval
gate, and KMS-encrypted artifact bucket. Demonstrates the
READY_TO_DEPLOY verdict, architecture checklist, and ordered
deploy-command list.

## Input (user prompt)

> Provision a production V2 pipeline for our orders service. Source
> is CodeCommit repository `orders-service` on branch main. Build is
> CodeBuild `orders-build` exporting IMAGE_URI and IMAGE_TAG. There's
> a manual approval gate before prod deploy with an SNS notification
> to oncall@example.com. Deploy is CloudFormation CREATE_REPLACE on
> `prod-orders-service` in target account 222222222222 (cross-account).
> Trigger should fire only on pushes to main where src/** changed
> (exclude docs). Use the existing KMS key
> arn:aws:kms:us-east-1:111111111111:key/abc-123 and existing artifact
> bucket my-pipeline-artifacts.

## Expected behavior

1. **Pre-flight:** the skill validates the spec — pipeline type V2,
   source (CodeCommit), trigger (branch main + path filter), build
   (CodeBuild with exported variables), deploy (CloudFormation
   cross-account), approval gate, KMS key, artifact bucket.
2. **Trigger:** the skill plans a trigger scoped to `main` with
   FilePaths Includes=[src/**], Excludes=[docs/**, README.md]. It
   warns that an unscoped trigger would fire on every push to every
   branch.
3. **Namespace variables:** the skill plans `BuildVars` namespace
   with IMAGE_URI and IMAGE_TAG exported via buildspec
   exported-variables, consumed in the deploy's ParameterOverrides as
   `#{BuildVars.IMAGE_URI}`.
4. **Cross-account:** the skill plans the KMS key policy granting the
   target role kms:Decrypt / kms:GenerateDataKey, the cross-account
   IAM role trust policy, and the S3 bucket policy granting target
   role s3:GetObject.
5. **Manual approval:** the skill plans an Approval action with
   ExternalEntityLink, CustomData, and NotificationArn (SNS). It
   warns that approval timeouts are NOT enforced and suggests a
   scheduled Lambda for auto-rejecting stale approvals.
6. **Verdict:** READY_TO_DEPLOY — all 10 checklist dimensions pass.

## Expected output

```text
PIPELINE_SPEC: orders-service-pipeline
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Type: V2 (event-driven, no polling)
  Source: CodeCommit repository orders-service, branch main
  Trigger: branch=main, paths Includes=[src/**], Excludes=[docs/**, README.md]
  Build: CodeBuild orders-build, exports IMAGE_URI, IMAGE_TAG (Namespace=BuildVars)
  Approval: enabled between Build and Deploy (SNS prod-approval, ExternalEntityLink CHG12345)
  Deploy: CloudFormation CREATE_REPLACE on prod-orders-service in target account 222222222222
  Variables: IMAGE_URI flows from BuildVars to Deploy ParameterOverrides
  Cross-account: target=222222222222, KMS key arn:aws:kms:us-east-1:111111111111:key/abc-123, role arn:aws:iam::222222222222:role/CrossAccountCFNExecution
  Artifact bucket: my-pipeline-artifacts (block-public-access + KMS CMK + versioning)
  Pipeline role: arn:aws:iam::111111111111:role/my-pipeline-role (scoped to repo / project / stack / key / bucket)
CHECKLIST:
  [x] Pipeline type V2 confirmed (event-driven, no polling)
  [x] Source action configured (CodeCommit orders-service)
  [x] Trigger with branch + path filter (NOT unscoped — main only, src/** only)
  [x] Build (CodeBuild orders-build) with exported namespace variables IMAGE_URI, IMAGE_TAG
  [x] Deploy action with cross-account role arn:aws:iam::222222222222:role/CrossAccountCFNExecution
  [x] Manual approval gate configured (ExternalEntityLink + SNS notification)
  [x] Namespace variables validated (stage condition guards against empty IMAGE_URI)
  [x] Cross-account KMS key policy + IAM role + S3 bucket policy wired
  [x] Artifact bucket hardened (block public access + KMS CMK + versioning)
  [x] Pipeline IAM role scoped (no wildcards on S3 / KMS / CodeBuild / CodeCommit)
FINDINGS:
  - [INFO] Pricing: $0.002/execution (event-driven) + $1/active pipeline/month
  - [INFO] Cross-account deploy via KMS-encrypted artifacts — verify KMS policy grants target role
  - [WARN] Approval timeouts NOT enforced — pipeline waits indefinitely for approval
  - [WARN] Trigger filter MUST scope to production branches (unscoped = flood + risk)
DEPLOY_COMMANDS:
  1. aws kms put-key-policy --key-id arn:aws:kms:us-east-1:111111111111:key/abc-123 --policy-name default --policy file://kms-key-policy.json
  2. aws s3api put-bucket-policy --bucket my-pipeline-artifacts --policy file://bucket-policy.json
  3. aws codepipeline create-pipeline --cli-input-json file://pipeline.json
  4. aws codepipeline start-pipeline-execution --name orders-service-pipeline  # test execution
```

## Verification (run after deploy)

```bash
aws codepipeline get-pipeline --name orders-service-pipeline
aws codepipeline get-pipeline-state --name orders-service-pipeline

# Trigger / cross-account verification
aws kms get-key-policy --key-id arn:aws:kms:us-east-1:111111111111:key/abc-123 --policy-name default
aws s3api get-bucket-policy --bucket my-pipeline-artifacts
aws iam get-role --role-name CrossAccountCFNExecution  # in target account

# Trigger a test execution
aws codepipeline start-pipeline-execution --name orders-service-pipeline

# Verify the approval notification fires when build completes
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:prod-approval
```

The pipeline runs end-to-end on a push to main (src/** only): source
clone → build (exports IMAGE_URI) → approval gate (SNS fires,
oncall@example.com receives email) → on Approve, deploy to
prod-orders-service in 222222222222 via cross-account CloudFormation
using the KMS-encrypted artifact.
