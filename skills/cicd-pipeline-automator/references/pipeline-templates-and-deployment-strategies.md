# Pipeline Templates and Deployment Strategies Reference

Load this reference when planning or emitting any pipeline-as-code
template. The procedures below are the canonical sequences for each
deployment archetype, with requirement checks, IaC templates, and
post-deploy verification.

## Decision tree — which deployment strategy

| Scenario | Use | Why |
|---|---|---|
| Stateless service, simple stack | **CloudFormation change-set** | Inspect before execute; safe |
| Lambda function, low-risk change | **CodeDeploy canary 10%/90%** | Traffic shifting with hooks |
| Lambda function, immediate rollback needed | **CodeDeploy all-at-once + alarms** | Fast rollback via CloudWatch alarm |
| ECS service, rolling update | **ECS deployment circuit breaker** | Auto-rollback on failed stabilize |
| EC2 fleet, in-place | **CodeDeploy in-place** | Rolling replace across ASG instances |
| EC2 fleet, zero-downtime | **CodeDeploy blue/green via Auto Scaling group** | New ASG, traffic shift, terminate old |
| API Gateway, weighted routing | **Route53 weighted + canary deployment** | Gradual traffic shift via DNS |
| Multi-region active-active | **CloudFormation StackSet + Route53 latency** | Per-region deploy with global DNS |
| Compliance / audit deploy | **Manual approval + CloudFormation change-set** | Human review + drift detection |
| Cross-account hub-and-spoke | **Source account pipeline + target deploy role** | Central CI/CD, isolated deploy targets |

## CloudFormation change-set deploy procedure

**When to use:** stateless services where the template is the source
of truth.

**Pre-checks:**
1. Deploy role exists with trust policy for
   `cloudformation.amazonaws.com`.
2. Deploy role policy grants the actions needed by the stack
   (`ec2:*`, `s3:*`, etc.).
3. Artifact KMS key policy grants the deploy role `kms:Decrypt`.
4. Stack exists (for `CHANGE_SET_REPLACE`) or does not exist (for
   `CHANGE_SET_CREATE` then `CHANGE_SET_EXECUTE`).
5. Template path in the artifact matches the build output structure.

**Pipeline action sequence:**
```yaml
- Name: CreateChangeSet
  ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1}
  Configuration:
    ActionMode: CHANGE_SET_REPLACE
    StackName: !Sub "${AppName}-prod"
    ChangeSetName: !Sub "${AppName}-changeset"
    TemplatePath: BuildOutput::template.yaml
    TemplateConfiguration: BuildOutput::config.json
    RoleArn: !GetAtt DeployRole.Arn
    Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND
    ParameterOverrides: !Sub |
      {
        "AppVersion": "#{BuildVariables.CommitSha}",
        "Environment": "prod"
      }
  InputArtifacts: [{Name: BuildOutput}]
  RunOrder: 1
- Name: ExecuteChangeSet
  ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1}
  Configuration:
    ActionMode: CHANGE_SET_EXECUTE
    StackName: !Sub "${AppName}-prod"
    ChangeSetName: !Sub "${AppName}-changeset"
    OutputFileName: StackOutputs.json
  OutputArtifacts: [{Name: DeployOutput}]
  RunOrder: 2
```

**Common failure modes:**
- `InvalidChangeSetStatusException` — the change-set was already
  executed or deleted. Recreate.
- `InsufficientCapabilitiesException` — capabilities not declared.
  Add CAPABILITY_IAM, CAPABILITY_NAMED_IAM, CAPABILITY_AUTO_EXPAND
  as needed.
- Empty change-set — the template has no actual changes. Handle via
  `OnRollback: DISABLED` or add a timestamp parameter.

## CodeDeploy blue/green for Lambda procedure

**When to use:** Lambda function deploys with traffic shifting and
pre/post traffic hooks.

**Pre-checks:**
1. CodeDeploy application exists with
   `computePlatform: Lambda`.
2. Deployment group exists targeting the Lambda function / alias.
3. Deployment style: `BLUE_GREEN` with `WITH_TRAFFIC_CONTROL`.
4. PreTrafficHook / PostTrafficHook Lambda functions exist and are
   tested.
5. IAM role for CodeDeploy includes `AWSCodeDeployRoleForLambda`
   managed policy.

**Deployment configuration options:**
- `CodeDeployDefault.LambdaCanary10Percent5Minutes` — 10% for 5 min,
  then 90%.
- `CodeDeployDefault.LambdaCanary10Percent30Minutes` — 10% for 30
  min, then 90%.
- `CodeDeployDefault.LambdaLinear10PercentEvery1Minute` — 10% per
  minute over 10 minutes.
- `CodeDeployDefault.LambdaLinear10PercentEvery2Minutes` — 10% every
  2 min over 20 min.
- `CodeDeployDefault.LambdaAllAtOnce` — immediate 100% (fastest,
  no canary).
- Custom config via `create-deployment-config` for non-standard
  percentages.

**Hook function contract:**
```python
def handler(event, context):
    # PreTraffic: runs BEFORE any traffic shifts to the new version
    # PostTraffic: runs AFTER all traffic is on the new version
    # Both must return 200 on success, non-200 to fail the deployment
    deployment_id = event['DeploymentId']
    lifecycle_event_hook_execution_id = event['LifecycleEventHookExecutionId']
    # Run validation (smoke tests, schema checks, etc.)
    success = run_validation()
    codedeploy = boto3.client('codedeploy')
    codedeploy.put_lifecycle_event_hook_execution_status(
        deploymentId=deployment_id,
        lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
        status='Succeeded' if success else 'Failed'
    )
    return {'statusCode': 200 if success else 500}
```

If a hook fails, CodeDeploy automatically rolls back to the previous
version. No operator intervention needed.

## ECS rolling with circuit breaker procedure

**When to use:** ECS services where the task definition is updated
on each deploy.

**Pre-checks:**
1. ECS cluster + service exists.
2. Task execution role + task role exist and have needed permissions.
3. Container image is in ECR (or accessible registry).
4. Service's `DeploymentConfiguration.DeploymentCircuitBreaker` is
  enabled.

**ECS service config:**
```yaml
DeploymentConfiguration:
  DeploymentCircuitBreaker:
    Enable: true
    Rollback: true
  MaximumPercent: 200
  MinimumHealthyPercent: 100
```

When the circuit breaker is enabled with rollback, ECS automatically
rolls back to the previous task definition if a deployment fails to
reach steady state within ~30 minutes (configurable).

**Pipeline action:**
```yaml
- Name: DeployECS
  ActionTypeId: {Category: Deploy, Owner: AWS, Provider: ECS, Version: 1}
  Configuration:
    ClusterName: !Ref ECSCluster
    ServiceName: !Ref ECSService
    TaskDefinitionTemplatePath: BuildOutput::taskdef.json
    Image1: !Sub "${ECRRepo}.dkr.ecr.${AWS::Region}.amazonaws.com/${AppName}:#{BuildVariables.CommitSha}"
  InputArtifacts: [{Name: BuildOutput}]
```

The `Image1` placeholder is substituted into the task definition
template, allowing dynamic image tags per commit.

## Cross-account deployment procedure

**When to use:** central CI/CD account deploys to multiple target
accounts.

**Architecture:**
```
[Source account (CI/CD)]              [Target account (prod)]
  CodePipeline                          Deploy role
    |                                     ^
    |   assume role                       |
    +-------------------------------------+
    artifact bucket -> KMS key grants ->
```

**Three IAM pieces:**

1. **Source-account pipeline role** — must allow `sts:AssumeRole` on
   the target deploy role:
   ```json
   {
     "Effect": "Allow",
     "Action": "sts:AssumeRole",
     "Resource": "arn:aws:iam::222222222222:role/target-deploy"
   }
   ```

2. **Target-account deploy role** — trust policy restricting to the
   source account:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"Service": "codepipeline.amazonaws.com"},
       "Action": "sts:AssumeRole",
       "Condition": {"StringEquals": {
         "aws:SourceAccount": "111111111111"
       }},
       "StringLike": {
         "aws:SourceArn": "arn:aws:codepipeline:us-east-1:111111111111:*"
       }
     }]
   }
   ```

3. **Artifact KMS key policy** — must grant the target account:
   ```json
   {
     "Sid": "Allow target account",
     "Effect": "Allow",
     "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
     "Action": ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
     "Resource": "*"
   }
   ```

The target account root principal is granted, which then delegates to
the deploy role via IAM policy.

**Artifact bucket policy** must grant the target account:
```json
{
  "Sid": "Allow target account",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::source-artifact-bucket",
    "arn:aws:s3:::source-artifact-bucket/*"
  ]
}
```

## Pipeline monitoring procedure

**EventBridge rule for pipeline failures:**
```yaml
PipelineFailureRule:
  Type: AWS::Events::Rule
  Properties:
    EventPattern:
      source: [aws.codepipeline]
      detail-type:
        - CodePipeline Pipeline Execution State Change
      detail:
        state: [FAILED, CANCELED, STOPPED]
    Targets:
      - Arn: !Ref PipelineFailureTopic
        Id: PipelineFailureTopic
        RoleArn: !GetAtt EventBridgeRole.Arn
```

**Manual approval gate:**
```yaml
- Name: ApproveDeployment
  ActionTypeId: {Category: Approval, Owner: AWS, Provider: Manual, Version: 1}
  Configuration:
    NotificationArn: !Ref ApprovalTopic
    CustomData: "Review the CloudFormation change-set before deployment"
    ExternalEntityLink: !Sub "https://console.aws.amazon.com/cloudformation/home?region=${AWS::Region}#/stacks/changesets/changeset-id"
```

The `ExternalEntityLink` lets approvers click directly to the
change-set preview in the console.

## V2 migration procedure

**V1 → V2 migration steps:**
1. Verify no deprecated features are in use (GitHub v1 OAuth — migrate
   to CodeStar Connection first).
2. Snapshot the V1 pipeline: `get-pipeline --name <name> --output
   json`.
3. Update the pipeline with `PipelineType: V2`.
4. Add `Triggers` config (replaces `PollForSourceChanges`).
5. Apply: `update-pipeline --cli-input-json file://v2-pipeline.json`.
6. Verify the trigger fires on the next push.

V2 pipelines support in-place upgrade from V1 — no need to delete and
recreate. The migration is reversible (downgrade back to V1 is
supported within 30 days).

## Build environment reference (2026)

**Common CodeBuild managed images:**
- `aws/codebuild/standard:7.0` — Node 18, Python 3.11, Java 17, Go 1.20, .NET 7
- `aws/codebuild/standard:8.0` — Node 20, Python 3.12, Java 21, Go 1.22, .NET 8
- `aws/codebuild/amazonlinux2-x86_64-standard:5.0` — Amazon Linux 2
- `aws/codebuild/amazonlinux2-aarch64-standard:2.0` — ARM64

For runtime-specific images:
- `aws/codebuild/nodejs:18` — Node 18 only
- `aws/codebuild/python:3.11` — Python 3.11 only
- `aws/codebuild/java:17` — Java 17 only

For custom images, host in ECR and reference by URI in
`Environment.Image`.

## Trigger patterns (V2)

**Git push trigger:**
```yaml
Triggers:
  - GitConfiguration:
      Push:
        - Branches:
            - main
            - 'release/*'
          FilePathIncludes:
            - 'src/**'
            - 'buildspec.yml'
          FilePathExcludes:
            - 'docs/**'
            - '*.md'
    ProviderType: CodeStarSourceConnection
```

**Pull request trigger:**
```yaml
Triggers:
  - GitConfiguration:
      PullRequest:
        - Events:
            - OPEN
            - UPDATED
          Branches:
            - main
    ProviderType: CodeStarSourceConnection
```

**Scheduled trigger (cron):**
```yaml
Triggers:
  - GitConfiguration: {}
    ProviderType: Schedule
    Schedule:
      ScheduleExpression: "cron(0 2 * * ? *)"
```

## Cost reference (2026)

- CodePipeline V1 active pipeline: $1.00/month.
- CodePipeline V2 active pipeline: $0.50/month (cheaper for V2 with
  triggers).
- CodePipeline action execution: $0.003 per action (V1), $0.002 per
  action (V2).
- CodeBuild: $0.005/minute (small), $0.01/minute (medium), $0.02/minute
  (large), $0.08/minute (xlarge).
- CodeDeploy: free for EC2/Lambda/ECS deployments.
- KMS CMK: $1.00/month per key + $0.03 per 10,000 requests.
- S3 artifact storage: $0.023/GB-month (standard).

For a fleet of 20 pipelines averaging 50 actions/month each, monthly
CodePipeline cost is ~$130 — usually negligible vs. engineering time
saved.

## V2 trigger example (Step 1: source stage design)

**V2 trigger example:**
```yaml
Triggers:
  - GitConfiguration:
      Push:
        - Branches:
            - main
          FilePathIncludes:
            - "src/**"
    ProviderType: CodeStarSourceConnection
```

## buildspec.yml minimum (Step 2: build stage design)

**buildspec.yml minimum:**
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      nodejs: 18
    commands:
      - npm ci
  build:
    commands:
      - npm run build
      - npm run test:unit
  post_build:
    commands:
      - npm run test:integration
artifacts:
  files:
    - '**/*'
  base-directory: dist
cache:
  paths:
    - node_modules/**/*
```

## Step 4: Deploy stage design — strategy blocks

#### CloudFormation deploy (create-change-set + execute)

```yaml
- Name: Deploy
  Actions:
    - Name: CreateChangeSet
      ActionTypeId:
        Category: Deploy
        Owner: AWS
        Provider: CloudFormation
        Version: 1
      Configuration:
        ActionMode: CHANGE_SET_REPLACE
        StackName: !Sub "${AppName}-prod"
        ChangeSetName: !Sub "${AppName}-prod-changeset"
        TemplatePath: BuildOutput::template.yaml
        RoleArn: !GetAtt DeployRole.Arn
        Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM
      InputArtifacts:
        - Name: BuildOutput
      RunOrder: 1
    - Name: ExecuteChangeSet
      ActionTypeId:
        Category: Deploy
        Owner: AWS
        Provider: CloudFormation
        Version: 1
      Configuration:
        ActionMode: CHANGE_SET_EXECUTE
        StackName: !Sub "${AppName}-prod"
        ChangeSetName: !Sub "${AppName}-prod-changeset"
      RunOrder: 2
```

#### CodeDeploy in-place (EC2)

```yaml
- Name: Deploy
  Actions:
    - Name: DeployEC2
      ActionTypeId:
        Category: Deploy
        Owner: AWS
        Provider: CodeDeploy
        Version: 1
      Configuration:
        ApplicationName: !Ref CodeDeployAppName
        DeploymentGroupName: !Ref CodeDeployDGName
      InputArtifacts:
        - Name: BuildOutput
```

#### CodeDeploy blue/green (Lambda)

```yaml
DeploymentStyle:
  DeploymentType: BLUE_GREEN
  DeploymentOption: WITH_TRAFFIC_CONTROL
  DeploymentOverview:
    Canary10Percent5Minutes: {}
```

The canary config specifies 10% traffic shift for 5 minutes, then the
remaining 90%. PreTrafficHook / PostTrafficHook Lambda functions run
before/after the shift and can fail the deployment programmatically.

#### ECS rolling with circuit breaker

```yaml
DeploymentConfiguration:
  DeploymentCircuitBreaker:
    Enable: true
    Rollback: true
  MaximumPercent: 200
  MinimumHealthyPercent: 100
```

The circuit breaker rolls back automatically if a deployment fails to
stabilize within the healthy-percent thresholds.

#### Route53 weighted routing (manual blue/green)

```yaml
- Name: ShiftTraffic10
  ActionTypeId:
    Category: Invoke
    Owner: AWS
    Provider: Lambda
    Version: 1
  Configuration:
    FunctionName: traffic-shifter
    UserParameters: '{"blue_weight": 90, "green_weight": 10}'
```

The Lambda function updates the Route53 weighted record set. Pair with
CloudWatch alarms that auto-rollback if error rate spikes.

## Step 5: Cross-account deployment design — IAM pieces and policies

**Three IAM pieces (all required):**

1. **Source-account pipeline role** — must allow `sts:AssumeRole` on
   the target deploy role.
2. **Target-account deploy role** — trust policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"Service": "codepipeline.amazonaws.com"},
       "Action": "sts:AssumeRole",
       "Condition": {"StringEquals": {
         "aws:SourceAccount": "<source-account-id>"
       }}
     }]
   }
   ```
3. **Artifact KMS key policy** — must grant the target account
   `kms:Decrypt`, `kms:GenerateDataKey`.

**Artifact bucket policy** must grant the target account
`s3:GetObject` on the artifact prefix.

## Step 6: Pipeline monitoring design — EventBridge rule and approval gate

**EventBridge rule for pipeline failures:**
```yaml
EventPattern:
  source:
    - aws.codepipeline
  detail-type:
    - CodePipeline Pipeline Execution State Change
  detail:
    state:
      - FAILED
      - CANCELED
Target:
  Arn: !Ref PipelineFailureTopic
```

**Manual approval gate:**
```yaml
- Name: ApprovalGate
  Actions:
    - Name: Approve
      ActionTypeId:
        Category: Approval
        Owner: AWS
        Provider: Manual
        Version: 1
      Configuration:
        NotificationArn: !Ref ApprovalTopic
        CustomData: "Review and approve production deployment"
```

Missing `NotificationArn` = silent gate. Approvers never know they're
needed.

## Patterns — pipeline-as-code templates (CloudFormation, CDK, Terraform)

### CloudFormation (AWS::CodePipeline::Pipeline)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Parameters:
  AppName:
    Type: String
  GitHubConnectionArn:
    Type: String
  ArtifactKeyArn:
    Type: String
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
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AWSCodePipelineFullAccess
      Policies:
        - PolicyName: ArtifactAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: [s3:GetObject, s3:PutObject, s3:ListBucket]
                Resource:
                  - !GetAtt ArtifactBucket.Arn
                  - !Sub "${ArtifactBucket.Arn}/*"
              - Effect: Allow
                Action: [kms:Encrypt, kms:Decrypt, kms:GenerateDataKey, kms:DescribeKey]
                Resource: !Ref ArtifactKeyArn
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      RoleArn: !GetAtt PipelineRole.Arn
      PipelineType: V2
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactBucket
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
                FullRepositoryId: !Sub "${GitHubOwner}/${GitHubRepo}"
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
                NotificationArn: !Ref ApprovalTopic
                CustomData: "Review and approve production deployment"
        - Name: Deploy
          Actions:
            - Name: CreateChangeSet
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CloudFormation
                Version: 1
              Configuration:
                ActionMode: CHANGE_SET_REPLACE
                StackName: !Sub "${AppName}-prod"
                ChangeSetName: !Sub "${AppName}-changeset"
                TemplatePath: BuildOutput::template.yaml
                RoleArn: !GetAtt DeployRole.Arn
              InputArtifacts:
                - Name: BuildOutput
              RunOrder: 1
            - Name: ExecuteChangeSet
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CloudFormation
                Version: 1
              Configuration:
                ActionMode: CHANGE_SET_EXECUTE
                StackName: !Sub "${AppName}-prod"
                ChangeSetName: !Sub "${AppName}-changeset"
              RunOrder: 2
```

### CDK (Pipelines module)

```typescript
import * as cdk from 'aws-cdk-lib';
import * as pipelines from 'aws-cdk-lib/pipelines';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';

const app = new cdk.App();
const pipeline = new pipelines.CodePipeline(this, 'Pipeline', {
  pipelineName: `${appName}-pipeline`,
  synth: new pipelines.CodeBuildStep('Synth', {
    input: pipelines.CodePipelineSource.connection(`${githubOwner}/${githubRepo}`, 'main', {
      connectionArn: githubConnectionArn,
    }),
    buildEnvironment: {
      buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
      privileged: true,
    },
    commands: ['npm ci', 'npm run build', 'npx cdk synth'],
  }),
  crossAccountKeys: true,
});

const prodStage = pipeline.addStage(new ProdAppStage(app, 'Prod', {
  env: prodEnv,
}));
prodStage.addPost(new pipelines.ShellStep('SmokeTest', {
  commands: ['curl -f https://prod.example.com/health'],
}));
```

### Terraform (aws_codepipeline)

```hcl
resource "aws_codepipeline" "this" {
  name     = "${var.app_name}-pipeline"
  role_arn = aws_iam_role.pipeline.arn
  pipeline_type = "V2"

  artifact_store {
    type     = "S3"
    location = aws_s3_bucket.artifacts.id
    encryption_key {
      id   = aws_kms_key.artifacts.arn
      type = "KMS"
    }
  }

  stage {
    name = "Source"
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarConnection"
      version          = "1"
      output_artifacts = ["source_output"]
      configuration = {
        ConnectionArn        = var.github_connection_arn
        FullRepositoryId     = "${var.github_owner}/${var.github_repo}"
        BranchName           = "main"
        OutputArtifactFormat = "CODE_ZIP"
      }
    }
  }

  stage {
    name = "Build"
    action {
      name      = "Build"
      category  = "Build"
      owner     = "AWS"
      provider  = "CodeBuild"
      version   = "1"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      configuration = {
        ProjectName = aws_codebuild_project.this.name
      }
    }
  }

  stage {
    name = "Deploy"
    action {
      name     = "Deploy"
      category = "Deploy"
      owner    = "AWS"
      provider = "CloudFormation"
      version  = "1"
      input_artifacts = ["build_output"]
      configuration = {
        ActionMode     = "REPLACE_ON_FAILURE"
        StackName      = "${var.app_name}-prod"
        TemplatePath   = "build_output::template.yaml"
        RoleArn        = aws_iam_role.deploy.arn
        Capabilities   = "CAPABILITY_IAM,CAPABILITY_NAMED_IAM"
      }
    }
  }
}
```
