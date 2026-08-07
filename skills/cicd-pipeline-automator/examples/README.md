# End-to-end usage scenario: cicd-pipeline-automator

A walkthrough showing the skill designing a greenfield CloudFormation
pipeline for a Node 18 service, then surfacing a MANUAL_STEP_REQUIRED
verdict for a cross-account pipeline where the KMS key policy is
missing the target-account grant. Each path includes requirement
checks, full pipeline template emission, and post-verification
guidance — contrasted with what a generic assistant misses.

## Input (user prompt)

> Build a CI/CD pipeline for prod-checkout-pipeline. Source is GitHub
> (acme-org/checkout-service, main branch), build is CodeBuild with
> Node 18, deploy is CloudFormation to the same account. Include a
> manual approval gate before deploy.

```json
{
  "Operation": "create",
  "Pipeline name": "prod-checkout-pipeline",
  "Source": "GitHub (CodeStar Connection)",
  "Repository": "acme-org/checkout-service",
  "Branch": "main",
  "Language": "Node 18",
  "Build image": "aws/codebuild/standard:7.0",
  "Deploy target": "CloudFormation stack prod-checkout in same account",
  "Approval gate": "yes",
  "Template format": "CloudFormation",
  "RequirementChecks": {
    "codestar-connections.get-connection.abc-123": {"ConnectionStatus": "Available"},
    "iam.get-role.prod-deploy": {"TrustPolicy": "cloudformation.amazonaws.com"},
    "kms.describe-key.abc": {"KeyPolicy": "grants pipeline role + deploy role"},
    "s3api.get-bucket-versioning.prod-checkout-artifacts": {"Status": "Enabled"},
    "sns.get-topic-attributes.pipeline-approval": {"subscriptions": 2}
  }
}
```

## Skill output — AUTOMATED

```text
OPERATION: create
VERDICT: AUTOMATED
TARGET: prod-checkout-pipeline
REQUIREMENTS:
  - [PASS] CodeStar Connection arn:aws:codestar-connections:us-east-1:111111111111:connection/abc-123
    in Available state
  - [PASS] Build image aws/codebuild/standard:7.0 supports Node 18
    (verified via list-curated-environment-images)
  - [PASS] Deploy role arn:aws:iam::111111111111:role/prod-deploy exists
    with trust policy for cloudformation.amazonaws.com
  - [PASS] Artifact KMS key arn:aws:kms:us-east-1:111111111111:key/abc exists
    with policy granting the pipeline role + deploy role kms:Encrypt/Decrypt/GenerateDataKey
  - [PASS] Artifact bucket prod-checkout-artifacts exists with versioning
    enabled and KMS SSE configured
  - [PASS] Approval SNS topic arn:aws:sns:us-east-1:111111111111:pipeline-approval
    exists with 2 subscriptions
PIPELINE_TEMPLATE:
  AWSTemplateFormatVersion: '2010-09-09'
  Parameters:
    AppName:
      Type: String
      Default: prod-checkout
    GitHubConnectionArn:
      Type: String
      Default: arn:aws:codestar-connections:us-east-1:111111111111:connection/abc-123
    ArtifactKeyArn:
      Type: String
      Default: arn:aws:kms:us-east-1:111111111111:key/abc
  Resources:
    PipelineRole:
      Type: AWS::IAM::Role
      Properties:
        AssumeRolePolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Principal: {Service: codepipeline.amazonaws.com}
              Action: sts:AssumeRole
        Policies:
          - PolicyName: ArtifactAccess
            PolicyDocument:
              Version: '2012-10-17'
              Statement:
                - Effect: Allow
                  Action: [s3:GetObject, s3:PutObject, s3:ListBucket]
                  Resource:
                    - arn:aws:s3:::prod-checkout-artifacts
                    - arn:aws:s3:::prod-checkout-artifacts/*
                - Effect: Allow
                  Action: [kms:Encrypt, kms:Decrypt, kms:GenerateDataKey, kms:DescribeKey]
                  Resource: !Ref ArtifactKeyArn
                - Effect: Allow
                  Action: [codebuild:StartBuild, codebuild:BatchGetBuilds]
                  Resource: '*'
    Pipeline:
      Type: AWS::CodePipeline::Pipeline
      Properties:
        RoleArn: !GetAtt PipelineRole.Arn
        PipelineType: V2
        ArtifactStore:
          Type: S3
          Location: prod-checkout-artifacts
          EncryptionKey:
            Id: !Ref ArtifactKeyArn
            Type: KMS
        Stages:
          - Name: Source
            Actions:
              - Name: Source
                ActionTypeId:
                  Category: Source
                  Owner: AWS
                  Provider: CodeStarConnection
                  Version: 1
                Configuration:
                  ConnectionArn: !Ref GitHubConnectionArn
                  FullRepositoryId: acme-org/checkout-service
                  BranchName: main
                  OutputArtifactFormat: CODE_ZIP
                OutputArtifacts:
                  - Name: SourceOutput
          - Name: Build
            Actions:
              - Name: Build
                ActionTypeId:
                  Category: Build
                  Owner: AWS
                  Provider: CodeBuild
                  Version: 1
                Configuration:
                  ProjectName: !Ref BuildProject
                InputArtifacts:
                  - Name: SourceOutput
                OutputArtifacts:
                  - Name: BuildOutput
          - Name: Approval
            Actions:
              - Name: Approve
                ActionTypeId:
                  Category: Approval
                  Owner: AWS
                  Provider: Manual
                  Version: 1
                Configuration:
                  NotificationArn: arn:aws:sns:us-east-1:111111111111:pipeline-approval
                  CustomData: "Review the CloudFormation change-set before deploy"
          - Name: Deploy
            Actions:
              - Name: CreateChangeSet
                ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1}
                Configuration:
                  ActionMode: CHANGE_SET_REPLACE
                  StackName: !Sub "${AppName}"
                  ChangeSetName: !Sub "${AppName}-changeset"
                  TemplatePath: BuildOutput::template.yaml
                  RoleArn: arn:aws:iam::111111111111:role/prod-deploy
                  Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM
                InputArtifacts: [{Name: BuildOutput}]
                RunOrder: 1
              - Name: ExecuteChangeSet
                ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1}
                Configuration:
                  ActionMode: CHANGE_SET_EXECUTE
                  StackName: !Sub "${AppName}"
                  ChangeSetName: !Sub "${AppName}-changeset"
                RunOrder: 2
    PipelineFailureRule:
      Type: AWS::Events::Rule
      Properties:
        EventPattern:
          source: [aws.codepipeline]
          detail-type: [CodePipeline Pipeline Execution State Change]
          detail:
            state: [FAILED, CANCELED]
        Targets:
          - Arn: arn:aws:sns:us-east-1:111111111111:pipeline-failures
            Id: PipelineFailureTopic
MANUAL_GAPS: (none)
NOTES:
  - Pipeline is V2 (event-driven). No PollForSourceChanges needed.
  - Trigger: Git push to main branch via CodeStar Connection.
  - Detection lag: ~30-60s from push to Source action firing.
  - Manual approval gate before Deploy stage; approvers notified via SNS.
  - Deploy uses CHANGE_SET_REPLACE + CHANGE_SET_EXECUTE (safe; the
    change-set can be inspected before execution).
  - EventBridge rule emits SNS on FAILED/CANCELED state for on-call alerting.
  - Apply via: aws cloudformation deploy --template-file pipeline.yaml \
      --stack-name prod-checkout-pipeline --capabilities CAPABILITY_IAM
```

## Contrast — MANUAL_STEP_REQUIRED (cross-account KMS gap)

```text
OPERATION: create
VERDICT: MANUAL_STEP_REQUIRED
TARGET: cross-account-deploy-pipeline
REQUIREMENTS:
  - [PASS] CodeStar Connection exists in Available state
  - [PASS] Build image supports runtime
  - [PASS] Source-account pipeline role allows sts:AssumeRole on
    arn:aws:iam::222222222222:role/target-deploy
  - [PASS] Target-account deploy role trust policy includes
    codepipeline.amazonaws.com with aws:SourceAccount=111111111111
    condition
  - [FAIL] Artifact KMS key arn:aws:kms:us-east-1:111111111111:key/abc
    policy does NOT grant target account 222222222222 kms:Decrypt /
    kms:GenerateDataKey. Without this, the deploy role in the target
    account cannot decrypt the staged artifact.
PIPELINE_TEMPLATE: (held in draft — apply after closing the gap)
MANUAL_GAPS:
  - GAP: Artifact KMS key policy missing cross-account grant.
    REMEDIATION:
      aws kms put-key-policy --key-id arn:aws:kms:us-east-1:111111111111:key/abc \
        --policy-name default \
        --policy '{
          "Version": "2012-10-17",
          "Statement": [
            {"Sid": "Enable IAM policies", "Effect": "Allow",
             "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
             "Action": "kms:*", "Resource": "*"},
            {"Sid": "Allow target account", "Effect": "Allow",
             "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
             "Action": ["kms:Decrypt", "kms:GenerateDataKey",
                        "kms:DescribeKey"], "Resource": "*"}
          ]
        }'
    REASON: KMS key policy changes have blast radius beyond the pipeline
      (any service in the target account could use the key). Operator
      must review the grant scope.
NOTES:
  - Once the KMS policy is updated, re-run the pipeline plan to emit
    the full template.
  - The target-account deploy role also needs s3:GetObject on the
    artifact bucket prefix — verify the bucket policy includes the
    target account.
  - Consider using ExternalId on the cross-account role for defense-
    in-depth (confused-deputy protection).
```

## What the skill caught that a generic assistant misses

1. **GitHub v1 OAuth vs CodeStar Connection.** A generic assistant
   defaults to `ThirdParty/GitHub` (DEPRECATED). The skill always emits
   `CodeStarConnection` and verifies the connection is `Available`
   before emitting the template.

2. **Customer-managed KMS key on artifact store.** A generic assistant
   omits the `encryptionKey` field — artifacts are stored with only
   the bucket's default SSE. The skill always emits a CMK and verifies
   its policy grants every relevant principal.

3. **Separate pipeline role vs deploy role.** A generic assistant uses
   one role for both. The skill emits two distinct roles with correct
   trust policies (`codepipeline.amazonaws.com` for pipeline,
   `cloudformation.amazonaws.com` for deploy).

4. **Manual approval NotificationArn.** A generic assistant omits the
   SNS topic for approval notifications — approvers never know they're
   needed. The skill always wires an SNS topic and verifies
   subscriptions exist.

5. **CHANGE_SET_REPLACE + CHANGE_SET_EXECUTE.** A generic assistant
   uses `CREATE_UPDATE` (no inspection before execution). The skill
   always uses the two-step change-set pattern for production
   pipelines.

6. **Cross-account KMS gap.** A generic assistant emits a partial
   template and lets it fail at deploy time. The skill runs the
   requirement check, surfaces the KMS policy gap, and emits the exact
   `put-key-policy` snippet to close it before applying.

7. **EventBridge failure rule.** A generic assistant omits failure
   notifications. The skill emits an EventBridge rule matching
   FAILED/CANCELED states targeting an SNS topic.

8. **V2 vs V1.** A generic assistant defaults to V1 (polling). The
   skill always emits V2 (event-driven triggers) unless migrating an
   existing V1 pipeline.

9. **CONFIRM gate.** A generic assistant auto-executes
   `create-pipeline`. The skill emits CONFIRM and waits —
   `UpdatePipeline` replaces the entire definition atomically with no
   diff and no rollback.

10. **Snapshot before modify.** A generic assistant updates in place.
    The skill snapshots via `get-pipeline --output json` first.

## Slash-command invocation

```
/aws:automate-cicd-pipeline
```

Or via the orchestrator:

```
/aws:pipeline
You: "build a CI/CD pipeline for prod-checkout-pipeline"
```

The orchestrator emits
`[Phase: Automate | Skills routed: cicd-pipeline-automator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "build CI/CD pipeline for prod-checkout"
# [Phase: Automate | Skills routed: cicd-pipeline-automator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the pipeline stack is applied:

```bash
# Verify the pipeline exists and is healthy
aws codepipeline get-pipeline --name prod-checkout-pipeline \
  --profile default \
  --query 'pipeline.{Name:name,Type:pipelineType,Stages:stages[].name}'

aws codepipeline get-pipeline-state --name prod-checkout-pipeline \
  --profile default \
  --query 'stageStates[].{Stage:stageName,Status:latestExecution.status}'

# Trigger a test run
aws codepipeline start-pipeline-execution --name prod-checkout-pipeline \
  --profile default

# Verify the EventBridge failure rule is wired
aws events describe-rule --name prod-checkout-pipeline-failure-rule \
  --profile default

# Verify the CodeStar Connection is healthy
aws codestar-connections get-connection \
  --connection-arn arn:aws:codestar-connections:us-east-1:111111111111:connection/abc-123 \
  --profile default \
  --query 'Connection.ConnectionStatus'
```
