# cicd-pipeline-automator — worked examples (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Output format (per operation) — literal template block

```text
OPERATION: <create | update | troubleshoot | migrate-v2>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TARGET: <pipeline-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
PIPELINE_TEMPLATE: <inline CloudFormation / CDK / Terraform template>
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <CLI or IaC snippet to close the gap>
    REASON: <why this cannot be automated>
NOTES: <trigger model, detection lag, cross-account caveats>
```

## Worked example — MANUAL_STEP_REQUIRED (cross-account KMS gap)

```text
OPERATION: create
VERDICT: MANUAL_STEP_REQUIRED
TARGET: cross-account-deploy-pipeline
REQUIREMENTS:
  - [PASS] CodeStar Connection exists
  - [PASS] Build image supports runtime
  - [PASS] Source-account pipeline role allows sts:AssumeRole on
    arn:aws:iam::222222222222:role/target-deploy
  - [PASS] Target-account deploy role trust policy includes
    codepipeline.amazonaws.com with source-account condition
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
  - Once the KMS policy is updated, re-run the pipeline plan to emit the
    full template.
  - The target-account deploy role also needs s3:GetObject on the
    artifact bucket prefix — verify the bucket policy includes the
    target account.
```

## Perfect example output — AUTOMATED

```text
OPERATION: create
VERDICT: AUTOMATED
TARGET: prod-checkout-pipeline
REQUIREMENTS:
  - [PASS] CodeStar Connection arn:aws:codestar-connections:us-east-1:111111111111:connection/abc-123 (Available)
  - [PASS] Build image aws/codebuild/standard:7.0 supports Node 18
  - [PASS] Deploy role arn:aws:iam::111111111111:role/prod-deploy (trust: cloudformation.amazonaws.com)
  - [PASS] Artifact KMS key arn:aws:kms:us-east-1:111111111111:key/abc (policy grants pipeline role)
  - [PASS] Artifact bucket prod-checkout-artifacts (versioning enabled, KMS SSE)
  - [PASS] Approval SNS topic arn:aws:sns:us-east-1:111111111111:pipeline-approval (2 subscriptions)
PIPELINE_TEMPLATE:
  # CloudFormation AWS::CodePipeline::Pipeline (V2)
  Resources:
    Pipeline:
      Type: AWS::CodePipeline::Pipeline
      Properties:
        PipelineType: V2
        RoleArn: !GetAtt PipelineRole.Arn
        ArtifactStore:
          Type: S3
          Location: !Ref ArtifactBucket
          EncryptionKey: { Id: !Ref ArtifactKeyArn, Type: KMS }
        Stages:
          - Name: Source
            Actions:
              - Name: Source
                ActionTypeId: { Category: Source, Owner: AWS, Provider: CodeStarConnection, Version: 1 }
                Configuration:
                  ConnectionArn: !Ref GitHubConnectionArn
                  FullRepositoryId: !Sub "${GitHubOwner}/${GitHubRepo}"
                  BranchName: main
                OutputArtifacts: [{ Name: SourceOutput }]
          - Name: Build
            Actions:
              - Name: Build
                ActionTypeId: { Category: Build, Owner: AWS, Provider: CodeBuild, Version: 1 }
                Configuration: { ProjectName: !Ref BuildProject }
                InputArtifacts: [{ Name: SourceOutput }]
                OutputArtifacts: [{ Name: BuildOutput }]
          - Name: Approval
            Actions:
              - Name: Approve
                ActionTypeId: { Category: Approval, Owner: AWS, Provider: Manual, Version: 1 }
                Configuration:
                  NotificationArn: !Ref ApprovalTopic
                  CustomData: "Review and approve production deployment"
          - Name: Deploy
            Actions:
              - Name: CreateChangeSet
                ActionTypeId: { Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1 }
                Configuration:
                  ActionMode: CHANGE_SET_REPLACE
                  StackName: !Sub "${AppName}-prod"
                  ChangeSetName: !Sub "${AppName}-changeset"
                  TemplatePath: BuildOutput::template.yaml
                  RoleArn: !GetAtt DeployRole.Arn
                InputArtifacts: [{ Name: BuildOutput }]
                RunOrder: 1
              - Name: ExecuteChangeSet
                ActionTypeId: { Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1 }
                Configuration:
                  ActionMode: CHANGE_SET_EXECUTE
                  StackName: !Sub "${AppName}-prod"
                  ChangeSetName: !Sub "${AppName}-changeset"
                RunOrder: 2
    FailureRule:
      Type: AWS::Events::Rule
      Properties:
        EventPattern:
          source: [aws.codepipeline]
          detail-type: [CodePipeline Pipeline Execution State Change]
          detail: { state: [FAILED, CANCELED] }
        Targets:
          - Arn: !Ref PipelineFailureTopic
            Id: FailureNotify
MANUAL_GAPS: (none)
NOTES:
  - Pipeline is V2 (event-driven). No PollForSourceChanges needed.
  - Trigger: Git push to main via CodeStar Connection (~30-60s detection lag).
  - Deploy uses CHANGE_SET_REPLACE + CHANGE_SET_EXECUTE (inspectable, safe).
  - EventBridge rule emits SNS on FAILED/CANCELED for on-call alerting.
```

## Perfect example output — MANUAL_STEP_REQUIRED

```text
OPERATION: create
VERDICT: MANUAL_STEP_REQUIRED
TARGET: cross-account-deploy-pipeline
REQUIREMENTS:
  - [PASS] CodeStar Connection exists (Available)
  - [PASS] Build image supports runtime
  - [PASS] Source-account pipeline role allows sts:AssumeRole on target role
  - [PASS] Target-account deploy role trust includes codepipeline.amazonaws.com + aws:SourceAccount condition
  - [FAIL] Artifact KMS key policy does NOT grant target account 222222222222 kms:Decrypt/kms:GenerateDataKey
PIPELINE_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: Artifact KMS key arn:aws:kms:us-east-1:111111111111:key/abc policy
    missing cross-account grant for target account 222222222222.
    REMEDIATION:
      aws kms put-key-policy --key-id arn:aws:kms:us-east-1:111111111111:key/abc \
        --policy-name default \
        --policy '{"Version":"2012-10-17","Statement":[{"Sid":"Enable IAM","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::111111111111:root"},"Action":"kms:*","Resource":"*"},{"Sid":"Allow target account","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::222222222222:root"},"Action":["kms:Decrypt","kms:GenerateDataKey","kms:DescribeKey"],"Resource":"*"}]}'
    REASON: KMS key policy changes have blast radius beyond the pipeline.
      Operator must review the grant scope before applying.
NOTES:
  - Once the KMS policy is updated, re-run the pipeline plan to emit the full template.
  - Verify artifact bucket policy also grants target account s3:GetObject on the artifact prefix.
```

## Step 7: Emit template — included resources list

- `AWS::CodePipeline::Pipeline` with all stages wired.
- `AWS::CodeBuild::Project` for build/test stages.
- `AWS::IAM::Role` for pipeline service role and each action deploy
  role.
- `AWS::KMS::Key` for artifact encryption (if not provided).
- `AWS::S3::Bucket` for artifact store (if not provided).
- `AWS::Events::Rule` for failure notifications.
- `AWS::SNS::Topic` for failure notifications and approval gates.
