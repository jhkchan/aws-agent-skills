---
name: cicd-pipeline-automator
description: Designs and implements AWS-native CI/CD pipelines end-to-end using CodePipeline, CodeBuild, CodeDeploy, CloudFormation, CDK, and Terraform. Generates working pipeline-as-code templates (CloudFormation
  AWS::CodePipeline::Pipeline, CDK Pipeline module, Terraform aws_codepipeline) wired with source (CodeCommit / GitHub / CodeStar Connection), build (buildspec.yml, VPC-aware CodeBuild), test (unit, integration,
  CodeGuru Reviewer security scans), and deploy (CloudFormation change-set, CodeDeploy in-place / blue-green, ECS rolling, S3, Service Catalog) stages. Handles cross-account deployment (IAM roles, KMS artifact
  key, resource-based policy), blue/green (Lambda traffic shifting 10/90, ECS circuit breaker, Route53 weighted), pipeline monitoring (CloudWatch Events on state changes, SNS failure notifications, manual
  approval), and CodePipeline V2 event-driven triggers. Emits a verdict (AUTOMATED with pipeline template | MANUAL_STEP_REQUIRED with specific gap). Use when building a CI/CD pipeline, designing.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws codepipeline create-pipeline,
  update-pipeline, get-pipeline, get-pipeline-state, start-pipeline- execution, list-pipelines, aws codebuild create-project, batch-get- projects, aws codedeploy create-application, aws cloudformation create-change-set,
  execute-change-set, aws codestar-connections create-connection (AWS CLI v2, SSO or key-based credentials).
keywords:
- CodePipeline
- CodeBuild
- CodeDeploy
- CI/CD
- pipeline as code
- CloudFormation
- CDK
- Terraform
- blue/green
- canary
- cross-account deployment
- CodeStar Connection
- CodeCommit
- GitHub
- buildspec
- change-set
- manual approval
- pipeline monitoring
- CodePipeline V2
- CodeCatalyst
tags:
- codepipeline
- codebuild
- codedeploy
- ci-cd
- devtools
- automate
- cloudformation
- cdk
- terraform
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing or implementing a CI/CD pipeline using CodePipeline, CodeBuild, CodeDeploy, CloudFormation, CDK, or Terraform. Setting up source (CodeCommit, GitHub, CodeStar Connection), build
    (buildspec.yml, VPC-aware CodeBuild), test (unit, integration, CodeGuru), or deploy (CloudFormation change-set, CodeDeploy in-place or blue/green, ECS rolling, S3, Service Catalog) stages. Wiring cross-account
    deployment (IAM roles, KMS key, bucket policy). Implementing blue/green (Lambda traffic shifting, ECS circuit breaker, Route53 weighted). Adding pipeline monitoring (CloudWatch Events, SNS, manual approval).
    Migrating to CodePipeline V2 or troubleshooting pipeline failures.
  activation_triggers:
  - build CI/CD pipeline
  - create CodePipeline
  - design deployment pipeline
  - blue/green deployment
  - Lambda canary deploy
  - ECS rolling deploy
  - cross-account deployment
  - CodeStar Connection
  - buildspec.yml
  - pipeline as code
  - CloudFormation deploy pipeline
  - CDK pipelines
  - Terraform aws_codepipeline
  - CodePipeline V2 migration
  - pipeline not triggering
  - CodeBuild timeout
  - manual approval gate
  - SNS pipeline failure notification
  invocation_schema: 'Input: either (a) a deployment scenario describing app, source, build, test, deploy targets, and constraints (language, environment, cross-account, blue/green), OR (b) an existing
    pipeline definition + the operation (create, update, troubleshoot, migrate V2). Output: deterministic OPERATION/VERDICT/REQUIREMENTS/PIPELINE_TEMPLATE/ MANUAL_GAPS block per operation, where VERDICT
    is AUTOMATED (full template generated) or MANUAL_STEP_REQUIRED (specific gap blocks automation).'
---

# CI/CD Pipeline Automator

## What this skill does

Designs and emits a working CI/CD pipeline-as-code template for the
requested deployment scenario, including source, build, test, and
deploy stages wired correctly with IAM roles, KMS artifact encryption,
EventBridge triggers, SNS failure notifications, and (when requested)
manual approval gates. Runs deterministic requirement checks before
emitting the template — if all checks pass, the verdict is
`AUTOMATED` with the populated CloudFormation / CDK / Terraform
template. If a requirement is missing (no CodeStar Connection, no
cross-account KMS key, no deploy role), the verdict is
`MANUAL_STEP_REQUIRED` with the specific gap and the exact CLI / IaC
snippet that closes it.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + requirement checklist + stage matrix | Before any build |
| **§ Mindset** | Why pipeline-as-code, the source-credential trap, cross-account KMS | Understanding the design model |
| **§ Pre-flight** | Requirement gate — source, build env, deploy target, IAM, KMS | Before emitting any template |
| **§ Process** | Per-stage design: source, build, test, deploy, monitoring | When designing each stage |
| **§ Patterns** | Pipeline templates: CloudFormation, CDK, Terraform | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, PIPELINE_TEMPLATE, MANUAL_GAPS | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that break pipelines silently | Review before emitting |
| **§ Pre-flight safety** | Additional checks before any create/update CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `AUTOMATED` | All requirements satisfied (source cred, build env, deploy role, KMS key, artifact bucket, action IAM policies). Template generated. | Emit complete pipeline-as-code template, ready to apply |
| `MANUAL_STEP_REQUIRED` | One or more requirements missing (no CodeStar Connection, no cross-account role, no KMS key, environment mismatch). | Emit the specific gap and the exact CLI / IaC snippet to close it. Hold the partial template as a draft. |

**Requirement checklist (all must be satisfied for AUTOMATED):**

1. **Source provider credential** — CodeCommit (no extra cred), GitHub
   via CodeStar Connection (connection ARN in `Pending` or `Available`
   state), S3 (bucket exists with versioning).
2. **Build environment** — CodeBuild image supports the language
   runtime (check `aws codebuild list-curated-environment-images`).
3. **Build VPC (if private resources)** — VPC config with private
   subnets + security groups for CodeBuild if it needs to reach
   private VPC resources (RDS, internal ALB).
4. **Deploy role(s)** — IAM role with trust policy for the deploy
   provider (`cloudformation.amazonaws.com`, `codedeploy.amazonaws.com`,
   `ecs-tasks.amazonaws.com`) and the deploy-action permissions.
5. **KMS key** — customer-managed CMK for artifact encryption, with
   key policy granting the pipeline role + cross-account deploy roles
   `kms:Encrypt/Decrypt/GenerateDataKey`.
6. **Artifact bucket** — S3 bucket with versioning, bucket policy
   granting the pipeline role, KMS-compatible SSE config.
7. **Cross-account (if applicable)** — deploy role in target account
   with `Principal: codepipeline.amazonaws.com` + source-account
   condition; artifact bucket policy grants target account.
8. **Manual approval (if requested)** — SNS topic for approval
   notifications + NotificationArn in the approval action config.
9. **Monitoring** — EventBridge rule on `codepipeline` source
   matching `codepipeline-pipeline-pipeline-execution-failed`, target
   SNS topic for failure pages.

**Stage matrix (which AWS service handles each stage):**

| Stage | Provider(s) | Common pitfalls |
|---|---|---|
| Source | CodeCommit, GitHub (CodeStar Connection), S3, ECR | GitHub v1 OAuth is DEPRECATED — use CodeStar Connection |
| Build | CodeBuild (managed image, custom image, VPC) | Wrong runtime image, missing VPC config for private resources |
| Test | CodeBuild (unit/integration), CodeGuru Reviewer | Quality gate misconfigured, security scan not blocking |
| Deploy | CloudFormation, CodeDeploy, S3, ECS, Service Catalog, Elastic Beanstalk, Alex Skills Kit | Empty change-set, wrong deploy role, missing artifact encryption |
| Approval | Manual (SNS notification) | Missing NotificationArn = silent gate |
| Invoke | Lambda, Step Functions, SSM Automation | Lambda async invocation without error handling |

## Mindset

**One-line takeaway:** pipeline-as-code is the only sustainable way
to manage CI/CD at scale. Hand-built pipelines in the console have no
review trail, no rollback, no diff. Driven by three CodePipeline
realities:

- **Source credential is the silent pipeline-killer.** GitHub v1
  (`ThirdParty/GitHub`) uses a persistent OAuth token granting access
  to every repo under the authorizing user. CodeStar Connection is
  scoped and auto-rotated. A pipeline that uses v1 silently stops
  triggering when the token expires or is revoked. Always use CodeStar
  Connection for GitHub/GitLab/Bitbucket sources.
- **Cross-account deployment requires IAM in BOTH accounts AND a KMS
  key policy grant.** The pipeline role in the source account assumes
  a deploy role in the target account. The artifact bucket's KMS key
  policy must grant the target account `kms:Decrypt` — without this,
  the deploy action fails with `AccessDenied` when it tries to read
  the staged artifact.
- **CodePipeline V2 is event-driven; V1 defaults to polling.** V2
  pipelines use triggers (Git-based, scheduled, infrastructure-driven)
  and do not poll. V1 defaults to polling every 60 seconds unless
  `PollForSourceChanges: false` + an EventBridge rule is set. Polling
  generates excess API calls and has higher latency than event-based
  detection. New pipelines should use V2.

## Pre-flight: requirement gate

Run before emitting any template. Missing requirements produce
MANUAL_STEP_REQUIRED with the exact gap.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws codepipeline list-pipelines` — confirm whether a pipeline with
   the target name already exists (create vs update).
2. `aws codestar-connections list-connections` — for GitHub/GitLab
   sources, verify a connection exists in `Available` state. If
   `Pending`, the operator must complete the OAuth handshake in the
   console (cannot be automated).
3. `aws codebuild list-projects` — verify the CodeBuild project exists
   or will be created alongside the pipeline.
4. `aws codebuild list-curated-environment-images` — verify the build
   image supports the language runtime (e.g.,
   `aws/codebuild/standard:7.0` supports Node 18, Python 3.11, Java 17).
5. `aws iam get-role --role-name <deploy-role>` — verify the deploy
   role exists and its trust policy includes the deploy provider.
6. `aws kms describe-key --key-id <artifact-key>` — verify the artifact
   KMS key exists and its policy grants the pipeline role and any
   cross-account deploy roles.
7. `aws s3api get-bucket-location --bucket <artifact-bucket>` and
   `get-bucket-versioning` — verify the artifact bucket exists, has
   versioning enabled, and is in the pipeline region.
8. `aws sts get-caller-identity` on the target account (if cross-
   account) — verify the deploy role is assumable.

**Malformed input:** if the input scenario is missing required fields
(source provider, language/runtime, deploy target), emit
`VERDICT: MANUAL_STEP_REQUIRED` with `GAP: Scenario missing required
field <field>. Provide <field> to proceed.`

| Requirement | Effect on automation |
|---|---|
| CodeStar Connection in `Pending` state | MANUAL_STEP_REQUIRED — operator must complete OAuth handshake (cannot be automated); template emitted in draft with connection ARN placeholder. |
| No CodeStar Connection at all | MANUAL_STEP_REQUIRED — emit `aws codestar-connections create-connection` snippet, then complete the handshake. |
| Build image does not support runtime | MANUAL_STEP_REQUIRED — emit alternative image or custom-image buildspec. |
| Deploy role missing | MANUAL_STEP_REQUIRED — emit the IAM role CloudFormation snippet (trust + policy). |
| KMS key missing or no cross-account grant | MANUAL_STEP_REQUIRED — emit `aws kms create-key` + key policy grant snippet. |
| Artifact bucket missing | MANUAL_STEP_REQUIRED — emit S3 bucket CloudFormation snippet with versioning + KMS SSE. |
| Manual approval requested without SNS topic | MANUAL_STEP_REQUIRED — emit `aws sns create-topic` snippet. |
| EventBridge rule missing for failure notifications | AUTOMATED (the rule is part of the emitted template). |

## Process — pipeline design (apply in order)

### Step 0: Expert knowledge — non-obvious CodePipeline behaviors

These behaviors are easy to misjudge without operational pipeline
experience. Each changes a design if ignored:

- **The pipeline service role and action roles are DIFFERENT
  principals.** `pipeline.roleArn` is assumed by CodePipeline
  (`codepipeline.amazonaws.com`) to orchestrate stages, read from S3,
  invoke action providers. Each action's `configuration.RoleArn` is
  assumed by that action's service principal
  (`cloudformation.amazonaws.com`, `ecs-tasks.amazonaws.com`). Using
  the same role for both creates a trust-policy conflict and widens
  the blast radius.

- **`encryptionKey` absence means the pipeline does NOT manage
  encryption.** When `artifactStore.encryptionKey` is absent,
  CodePipeline writes artifacts using the bucket's own SSE settings.
  If the bucket has no SSE or SSE-S3 only, artifacts are
  UNENCRYPTED — and the bucket's policy may grant broad read access.

- **`get-pipeline` does NOT show disabled transitions.** Stage
  transition state is runtime metadata set by
  `DisableStageTransition`. Only `get-pipeline-state` returns
  `transitionStates[]` with `enabled: true/false`.

- **GitHub v1 (`ThirdParty/GitHub`) is DEPRECATED.** Persistent OAuth
  token grants access to every repo under the authorizing user.
  CodeStar Connections are scoped to specific repos and auto-rotate.
  Always emit CodeStar Connection in new pipelines.

- **`PollForSourceChanges: false` without EventBridge = no auto-
  trigger.** V1 pipelines need either polling=true OR a wired-up
  EventBridge rule. V2 pipelines use triggers (no polling field).

- **`artifactStores` (plural) is cross-region mode.** Each regional
  store has its own `encryptionKey`. A common gap: primary region has
  a CMK but a secondary region does not.

- **CloudFormation change-set deploy can produce an empty change-
  set.** When the template has no actual changes vs the existing
  stack, `create-change-set` returns no changes and the pipeline
  stage fails. Add `--disable-rollback false` and handle the
  `NoChange` case in the buildspec.

- **CodeDeploy blue/green for Lambda uses traffic shifting.** The
  canary config specifies `PreTrafficHook`, `PostTrafficHook`, and
  the routing config (Canary10Percent5Minutes, Linear10PercentEvery1Minute,
  AllAtOnce). The hooks are Lambda functions that run pre/post traffic
  shift and can fail the deployment programmatically.

- **CodeBuild `buildspec.yml` at the repo root is the default.**
  Override with `buildspec` in the project source config, or inline
  the buildspec in the project definition.

- **CodeBuild VPC config requires private subnets + NAT or VPC
  endpoints.** A CodeBuild project in a public subnet cannot reach
  the internet (no IGW for private subnets), and a project in a
  private subnet without NAT or VPC endpoints cannot pull the build
  image from ECR. Use VPC endpoints for S3, ECR, Logs, and any
  private services.

- **Cross-account deployment requires three IAM pieces.** (1) The
  pipeline role in the source account must allow `sts:AssumeRole` on
  the target deploy role. (2) The target deploy role's trust policy
  must allow `Principal: codepipeline.amazonaws.com` with a condition
  restricting to the source account. (3) The artifact bucket's KMS
  key policy must grant the target account `kms:Decrypt`.

- **`StartPipelineExecution` accepts `sourceRevisions` — an operator
  can deploy a DIFFERENT commit than what source detected.** This
  override is a supply-chain risk: a compromised operator can deploy
  an arbitrary commit that bypassed branch protection. Use
  CloudTrail to monitor `StartPipelineExecution` calls with
  `sourceRevisions` set.

- **SUPERSEDED execution mode cancels in-flight runs silently.** A
  new source change supersedes the currently running execution. If
  commits arrive faster than the pipeline completes, an execution
  may be cancelled moments before its Deploy stage. Use `QUEUE` mode
  (max 500 queued) to preserve all runs.

- **CodePipeline V2 (2024-2025) introduces triggers and pipeline
  variables.** V2 pipelines use Git-based triggers (push, pull
  request), scheduled triggers (cron), and infrastructure-driven
  triggers. No `PollForSourceChanges` field. V2 supports stage-level
  execution modes (QUEUED, SUPERSEDED) and pipeline-level variables
  for parameterized runs.

- **CodeCatalyst workflows (2024-2025) are an alternative to
  CodePipeline.** CodeCatalyst provides managed CI/CD workflows with
  a higher-level DSL. For greenfield DevOps on AWS, CodeCatalyst may
  be simpler; CodePipeline remains the right choice for fine-grained
  IAM control and existing AWS-native investments.

- **CodeGuru Reviewer can be a pipeline stage.** CodeGuru Reviewer
  integrates with CodePipeline as a build-stage action that runs
  automated code reviews on each pull request or commit. Pair with
  quality gates to block deploys on critical findings.

### Step 1: Source stage design

| Source | Provider | Credential | Trigger |
|---|---|---|---|
| CodeCommit | `CodeCommit` (AWS) | None (IAM-native) | EventBridge on `referenceUpdated` |
| GitHub | `CodeStarConnection` (AWS) | CodeStar Connection ARN | V2 trigger OR EventBridge rule |
| GitHub (legacy) | `GitHub` (ThirdParty) | OAuth token (DEPRECATED) | Polling or webhook (deprecated) |
| S3 | `S3` (AWS) | Pipeline role on bucket | EventBridge on `ObjectCreated` |
| ECR | `ECR` (AWS) | Pipeline role on ECR | EventBridge on `ImagePushed` |

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

### Step 2: Build stage design (CodeBuild)

**Key decisions:**
- **Managed image vs custom image.** Managed images
  (`aws/codebuild/standard:7.0`) cover common runtimes. Custom images
  (ECR-hosted) for proprietary runtimes or pre-installed dependencies.
- **VPC config.** If the build needs to reach private VPC resources
  (RDS, internal ALB, private ECR), set `VpcConfig` with private
  subnets + security groups. Add VPC endpoints or NAT for internet
  access.
- **Cache.** `LOCAL` cache (source, layers, custom) or `S3` cache.
  S3 cache is shared across build hosts and is faster for large
  dependency trees.
- **Artifacts.** `Type: CODEPIPELINE` for pipeline-managed artifacts.
  Secondary artifacts for separate build outputs.
- **Environment variables.** Plain text or Secrets Manager / Parameter
  Store references. Never hardcode secrets in buildspec.

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

### Step 3: Test stage design

| Test type | Implementation | Quality gate |
|---|---|---|
| Unit tests | CodeBuild `build` phase | Non-zero exit code fails the build |
| Integration tests | CodeBuild `post_build` phase | Non-zero exit code fails the build |
| Code coverage | CodeBuild + CodeGuru Profiler | Threshold gate in buildspec |
| CodeGuru Reviewer | CodePipeline action (separate stage) | Findings published to the PR; fail on critical |
| Security scans | Third-party action (Snyk, Checkov, Trivy) | Buildspec exit code on critical findings |
| Load tests | CodeBuild + Locust / k6 | Threshold gate on p99 latency |

### Step 4: Deploy stage design

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

### Step 5: Cross-account deployment design

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

### Step 6: Pipeline monitoring design

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

### Step 7: Emit template (AUTOMATED) or gap (MANUAL_STEP_REQUIRED)

If all pre-flight requirements pass, emit the complete pipeline-as-code
template (CloudFormation / CDK / Terraform, per the operator's
preference). The template includes:
- `AWS::CodePipeline::Pipeline` with all stages wired.
- `AWS::CodeBuild::Project` for build/test stages.
- `AWS::IAM::Role` for pipeline service role and each action deploy
  role.
- `AWS::KMS::Key` for artifact encryption (if not provided).
- `AWS::S3::Bucket` for artifact store (if not provided).
- `AWS::Events::Rule` for failure notifications.
- `AWS::SNS::Topic` for failure notifications and approval gates.

If any requirement is missing, emit `MANUAL_STEP_REQUIRED` with the
specific gap and the exact CLI / IaC snippet to close it.

## Patterns — pipeline-as-code templates

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

## Diagnostic flows

### Pipeline not triggering

1. `get-pipeline-state` — check the latest execution status. If
   nothing recent, the trigger is broken.
2. For V1: check `PollForSourceChanges` (true = polling, false =
   event-driven). If false, verify an EventBridge rule exists on the
   source change event.
3. For V2: check `Triggers` configuration. Verify the Git filter
   matches the branch and path.
4. For CodeStar Connection: verify the connection is `Available` (not
   `Pending`). A pending connection silently stops triggering.
5. Check CloudTrail for `StartPipelineExecution` events — if the
   EventBridge rule is firing but the pipeline isn't starting, the
   rule's role may lack `codepipeline:StartPipelineExecution`.

### CodeBuild timeout

1. Check the build project's `TimeoutInMinutes` (default 60, max 480).
2. Check CloudWatch Logs for the build — identify which phase is
   hanging (install, build, post_build).
3. Common causes: dependency download stall (use S3 cache or VPC
   endpoints), integration test waiting on a slow service, build
   image pull latency (use a custom ECR-hosted image).

### CloudFormation empty change-set

1. The deploy stage fails with `No updates are to be performed`.
2. Common cause: the build output template is identical to the
   deployed stack. Either no code changed, or the build did not
   regenerate the template.
3. Fix: add a buildspec step that always touches the template (e.g.,
  update a timestamp parameter), or handle `NoChange` in the deploy
  config.

### IAM role missing permissions

1. The deploy action fails with `AccessDenied` on a specific
   resource.
2. Check the deploy role (`configuration.RoleArn`) policy — does it
   grant the action on the resource?
3. For cross-account: check both the source-account pipeline role
   AND the target-account deploy role. The pipeline role must allow
   `sts:AssumeRole`; the deploy role's trust policy must allow
   `codepipeline.amazonaws.com`.

### Artifact bucket KMS policy (cross-account)

1. The deploy action fails with `AccessDenied` on `kms:Decrypt`.
2. The artifact KMS key policy must grant the target account
   `kms:Decrypt`, `kms:GenerateDataKey`. Without this, the deploy
   role can list the bucket but cannot decrypt the staged artifact.
3. Fix: add a key policy statement granting the target account root
   principal, with delegation to the deploy role.

## Output format (per operation)

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

### Worked example — AUTOMATED (greenfield pipeline)

```text
OPERATION: create
VERDICT: AUTOMATED
TARGET: prod-checkout-pipeline
REQUIREMENTS:
  - [PASS] CodeStar Connection arn:aws:codestar-connections:us-east-1:111111111111:connection/abc-123
    in Available state
  - [PASS] Build image aws/codebuild/standard:7.0 supports Node 18
  - [PASS] Deploy role arn:aws:iam::111111111111:role/prod-deploy exists
    with trust policy for cloudformation.amazonaws.com
  - [PASS] Artifact KMS key arn:aws:kms:us-east-1:111111111111:key/abc exists
    with policy granting the pipeline role
  - [PASS] Artifact bucket prod-checkout-artifacts exists with versioning
    and KMS SSE
  - [PASS] Approval SNS topic arn:aws:sns:us-east-1:111111111111:pipeline-approval
    exists with 2 subscriptions
PIPELINE_TEMPLATE:
  # CloudFormation AWS::CodePipeline::Pipeline (V2) — see inline template below
  Resources:
    Pipeline:
      Type: AWS::CodePipeline::Pipeline
      Properties:
        PipelineType: V2
        # ... full template populated with Source (CodeStar Connection),
        # Build (CodeBuild), Approval, Deploy (CloudFormation change-set)
        # stages wired with the verified IAM roles, KMS key, S3 bucket.
MANUAL_GAPS: (none)
NOTES:
  - Pipeline is V2 (event-driven). No PollForSourceChanges needed.
  - Trigger: Git push to main branch via CodeStar Connection.
  - Detection lag: ~30-60s from push to Source action firing.
  - Manual approval gate before Deploy stage; approvers notified via SNS.
  - Deploy uses CHANGE_SET_REPLACE + CHANGE_SET_EXECUTE (safe; change-set
    can be inspected before execution).
  - EventBridge rule emits SNS on FAILED/CANCELED state for on-call alerting.
```

### Worked example — MANUAL_STEP_REQUIRED (cross-account KMS gap)

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

## Anti-Patterns — NEVER do these things

- NEVER emit a pipeline using GitHub v1 (`ThirdParty/GitHub`). The v1
  integration uses a persistent OAuth token granting access to every
  repo under the authorizing user. It is DEPRECATED. Always use
  CodeStar Connection (`AWS/CodeStarConnection`).

- NEVER emit a pipeline without a customer-managed KMS key on the
  artifact store. The default (no `encryptionKey`) writes artifacts
  to S3 without KMS-managed access control — anyone with `s3:GetObject`
  can read every artifact (source archives, build outputs, templates).

- NEVER emit a pipeline role (`pipeline.roleArn`) with
  `AdministratorAccess`. The pipeline role orchestrates stages; it
  does not need broad service permissions. Grant least-privilege:
  `codepipeline:StartPipelineExecution`, `s3:GetObject` on artifact
  bucket, `codebuild:StartBuild`, etc.

- NEVER emit the same IAM role for the pipeline service principal and
  the action deploy principal. The pipeline role is assumed by
  `codepipeline.amazonaws.com`; the deploy role by
  `cloudformation.amazonaws.com` / `codedeploy.amazonaws.com` /
  `ecs-tasks.amazonaws.com`. Combining them widens the blast radius
  and creates a trust-policy conflict.

- NEVER emit a cross-account deploy role with
  `Principal: {"Service": "codepipeline.amazonaws.com"}` without a
  source-account `Condition`. Without the condition, ANY pipeline in
  ANY account can assume the role.

- NEVER emit a manual approval gate without `NotificationArn`. The
  gate exists on paper but approvers are never alerted — the pipeline
  sits in `InProgress` indefinitely until someone manually checks the
  console.

- NEVER emit a V1 pipeline with `PollForSourceChanges: false` without
  also emitting the EventBridge rule for source change detection. V1
  pipelines need EITHER polling OR an event rule — setting false
  without the rule means the pipeline never auto-triggers.

- NEVER emit a CodeBuild project in a public subnet when it needs to
  reach private VPC resources. CodeBuild in a public subnet cannot
  reach private subnets without VPC peering. Use private subnets +
  NAT or VPC endpoints.

- NEVER emit a deploy stage without a quality gate. A pipeline that
  deploys on every commit without tests is a continuous-deployment
  footgun — a faulty commit causes an outage. Add unit, integration,
  and (optionally) security scan stages before Deploy.

- NEVER emit `ActionMode: CREATE_UPDATE` for CloudFormation in a
  production pipeline. Use `CHANGE_SET_REPLACE` + `CHANGE_SET_EXECUTE`
  — the change-set can be inspected before execution, and an empty
  change-set can be handled gracefully.

- NEVER emit a CodeDeploy blue/green for Lambda without
  PreTrafficHook / PostTrafficHook. The hooks are the only programmatic
  way to fail the deployment if smoke tests fail during the canary
  window. Without hooks, a broken version ships to 100% after the
  canary interval elapses.

- NEVER emit a V1 pipeline when V2 is available. V2 pipelines use
  triggers (event-driven), support pipeline-level variables, and have
  stage-level execution modes (QUEUED, SUPERSEDED). V1 defaults to
  polling.

- NEVER auto-execute `create-pipeline` or `update-pipeline` without
  the CONFIRM gate. `UpdatePipeline` replaces the entire definition
  atomically with no diff and no rollback — always snapshot via
  `get-pipeline --output json` first.

- NEVER emit a pipeline without an EventBridge rule for failure
  notifications. A pipeline that fails silently leaves stale code in
  production. Add a rule matching `FAILED` and `CANCELED` states
  targeting an SNS topic.

- NEVER emit a cross-account pipeline without verifying the artifact
  bucket policy grants the target account `s3:GetObject`. The deploy
  role assumes the target role, which needs to read the artifact —
  without the bucket policy grant, the deploy fails with
  `AccessDenied` on the S3 GetObject call.

- NEVER emit a V2 pipeline trigger with a wildcard branch filter
  (`*`). This triggers on every branch push, including feature
  branches. Scope triggers to `main`, `release/*`, or specific
  branch patterns.

- NEVER recommend deleting a pipeline as remediation without verifying
  no workloads depend on it. `DeletePipeline` is irreversible.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-pipeline`, `update-pipeline`, `delete-pipeline`,
  `start-pipeline-execution`, `disable-stage-transition`,
  `enable-stage-transition`), emit: `CONFIRM: About to <operation> on
  pipeline <name> in account <account> region <region>. This affects
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Snapshot the pipeline before update.**
  `aws codepipeline get-pipeline --name <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`. `UpdatePipeline` replaces the
  entire definition atomically with no diff and no rollback.

- **Verify the pipeline exists before update.**
  `aws codepipeline get-pipeline --name <name>` — fail closed if it
  returns an error.

- **Before emitting a cross-account deploy role**, verify the target
  account ID and the trust policy condition. A misconfigured condition
  can allow any account to assume the role.

- **Before emitting a CodeStar Connection**, verify the connection
  state. A `Pending` connection requires the operator to complete the
  OAuth handshake in the console — this cannot be automated. Emit the
  connection ARN as a placeholder.

- **Before emitting a V2 migration**, verify the pipeline is eligible.
  V1 pipelines using deprecated features (e.g., GitHub v1 OAuth) must
  migrate the source first, then upgrade to V2.

- Prefer additive changes (add a stage, add an approval gate) over
  destructive changes (remove a stage, delete a pipeline) — additive
  changes are reversible and do not risk breaking existing deployment
  workflows.

## Recent AWS features (2024-2026)

- **CodePipeline V2 (2024-2025):** V2 pipelines introduce triggers
  (Git-based, scheduled, infrastructure-driven), pipeline-level
  variables, and stage-level execution modes (QUEUED, SUPERSEDED).
  V2 is the recommended default for new pipelines. V1 pipelines can
  be migrated via `update-pipeline` with `PipelineType: V2`.

- **CodePipeline.compute / EC2 runner (2025):** CodePipeline can
  provision EC2 runners for action execution (similar to GitHub
  Actions self-hosted runners). Useful for actions that need
  persistent state or specialized runtime.

- **CodeCatalyst workflows (2024-2025):** Higher-level CI/CD DSL
  alternative to CodePipeline. Suitable for greenfield DevOps on AWS
  that prioritizes developer experience over fine-grained IAM control.

- **CodeGuru Reviewer pipeline integration (2024-2025):** CodeGuru
  Reviewer can run as a pipeline stage, with findings published to
  the PR. Quality gates can block deploys on critical findings.

- **Cross-account actions with IAM role chaining (2024-2025):**
  Enhanced cross-account deployment support. Verify cross-account
  action roles have `ExternalId` conditions and are not wildcard-
  principal.

- **CodeDeploy blue/green for ECS with circuit breaker (2024):** ECS
  deployments now support circuit-breaker rollback (similar to
  Lambda blue/green). Use `DeploymentCircuitBreaker: {Enable: true,
  Rollback: true}` in the ECS service config.

- **EventBridge global endpoint for pipeline events (2024-2025):**
  Multi-region pipeline event routing for DR scenarios. Useful for
  pipelines that deploy to multiple regions.

- **AWS Backup integration with CodePipeline (2025):** Pipeline
  stages can trigger AWS Backup jobs for pre-deploy snapshots. Useful
  for database-dependent deploys.

## Error handling — procedure-level pipeline failures

These branches describe what to do when a step in the pipeline-build or
-deploy procedure fails — not when a CLI errors, but when the pipeline
*itself* cannot safely proceed.

- **If CodeBuild fails with `ResourceNotReachable` or
  `VpcConfigInvalidParameter`:** The CodeBuild project's `vpcConfig`
  references a security group, subnet, or VPC that does not exist or
  lacks `codebuild.amazonaws.com` in its security group inbound rules.
  Detection: `aws codebuild batch-get-projects --names <project>` and
  verify each `vpcConfig.securityGroupIds` / `subnets` / `vpcId` resolves
  via `aws ec2 describe-*`. Common causes: (a) the VPC was deleted but
  the project still references it; (b) the subnet has no available IP
  addresses; (c) the security group was recreated with a new ID after
  drift. Remediation: update the project with valid IDs, OR remove
  `vpcConfig` if the build does not need VPC access (e.g., no private
  artifact repo, no internal API calls). Do NOT retry the build until
  the project config is corrected — retries will fail identically.

- **If CloudFormation `create-change-set` returns an empty change set
  (`Status: FAILED`, `StatusReason: No updates are to be performed`):**
  The template is identical to the deployed stack. This is NOT a
  failure — it means the deploy is a no-op. Detection: the pipeline
  action `ChangeSetReplace` succeeds with `executionStatus: EXECUTABLE`
  but `Status: FAILED` on the change set itself. Remediation: in the
  pipeline's deploy stage, set
  `Configuration: ChangeSetName = <name>, ActionMode:
  REPLACE_ON_CREATE` and add a manual approval OR a Lambda check that
  skips `ExecuteChangeSet` when `Status == FAILED` and `StatusReason`
  contains `No updates`. Do NOT treat as a deployment failure — surface
  as `VERDICT: NOOP_DEPLOY (stack already in sync)`.

- **If cross-account deployment fails with `AccessDenied` on
  `sts:AssumeRole` in the deploy action:** The cross-account role's
  trust policy has expired or is missing the pipeline account. Common
  causes: (a) `ExternalId` condition mismatch (the pipeline account ID
  changed, or the role was created without the correct `ExternalId`);
  (b) the trust policy Principal is the wrong ARN format
  (`arn:aws:iam::111111111111:root` vs
  `arn:aws:iam::111111111111:role/CodePipelineServiceRole`); (c) the
  role was deleted during an AWS Organizations SCP change. Remediation:
  in the target account, `aws iam get-role --role-name
  <CrossAccountDeploymentRole>` and inspect `AssumeRolePolicyDocument`.
  Fix the trust policy, then re-run the failed action — do NOT need to
  recreate the pipeline. If the role was deleted, recreate with
  `aws cloudformation create-change-set` against the original stack
  template (recover from CloudFormation drift detection history).

- **If the source action fails with `RevisionNotFoundException` on
  CodeConnections (formerly CodeStar Connections):** The connection
  host or repository was renamed, the branch was deleted, or the
  OAuth token expired. Detection:
  `aws codestar-connections get-connection-status --connection-arn
  <arn>` returns `PENDING` or `ERROR`. Remediation: re-auth the
  connection via the AWS console (CLI cannot complete the OAuth hand-
  shake), then update the source action's `RepositoryName` and
  `BranchName` to match the current remote. The pipeline cannot self-
  heal this — operator action required.

- **If the manual approval stage times out (Approval expires before
  reviewer acts):** Default approval action has no timeout, but if the
  pipeline is wired with an EventBridge schedule that auto-rejects
  after N hours (a common compliance pattern), the deploy stage will
  block until manual intervention. Detection: pipeline status
  `InProgress` for > SLA, approval action `Status: InProgress`.
  Remediation: (a) emit an SNS notification to the approver channel
  with a deep link to the console approval UI; (b) for the immediate
  run, retry with `aws codepipeline put-approval-result --pipeline-name
  <name> --stage-name <stage> --action-name <action> --result
  status=Approved`; (c) for prevention, add a second approver or
  extend the auto-reject window. Surface as `VERDICT:
  APPROVAL_GATE_TIMEOUT` with the approver principal name.

## Edge cases

- **Pipeline with a manual approval stage timing out.** When the
  approval action is configured with a Lambda or EventBridge-based
  auto-reject after a compliance window (e.g., 4 hours for SOX), the
  pipeline will mark the run as Failed after timeout, blocking all
  subsequent runs of the same pipeline (CodePipeline does not auto-
  supersede by default in V1). Remediation: configure the approval
  action with `RevisionAlreadyPassed` semantics — newer revisions
  should supersede. In V2 pipelines, enable
  `ExecutionMode: SUPERSEDED` on the stage. Also wire an SNS topic to
  the approval action so the reviewer gets a push notification, not
  just a console badge.

- **Pipeline source in a different partition (AWS GovCloud or China).**
  CodeConnections does not support cross-partition source access. A
  pipeline in `aws-cn` cannot pull from a GitHub source via the same
  connection ARN as `aws`. Each partition needs its own connection.
  Surface as a finding if the source action references a foreign-
  partition connection ARN — the pipeline will fail at first run.

- **Pipeline that deploys to a stack with a DeletionPolicy: Retain on
  critical resources.** If the deploy template removes a resource that
  has `DeletionPolicy: Retain`, the resource is orphaned (still
  incurring cost) but no longer managed by the stack. Detection:
  compare `aws cloudformation list-stack-resources` against the new
  template before execute. Surface as a finding: `ORPHANED_RESOURCE`
  with the logical ID and physical ID — manual cleanup required post-
  deploy.

## Domain

AWS CloudOps / CodePipeline CI/CD Automation & Pipeline Engineering.

## AWS documentation

- **AWS CodePipeline User Guide** — https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html
- **CodePipeline V2 type** — https://docs.aws.amazon.com/codepipeline/latest/userguide/pipeline-types.html
- **CodePipeline API Reference** — https://docs.aws.amazon.com/codepipeline/latest/APIReference/
- **AWS CodeBuild User Guide** — https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html
- **CodeBuild buildspec reference** — https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html
- **AWS CodeDeploy User Guide** — https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html
- **CodeDeploy blue/green for Lambda** — https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps.html
- **CDK Pipelines module** — https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.pipelines-readme.html
- **CodeStar Connections** — https://docs.aws.amazon.com/dtconsole/latest/userguide/welcome.html
- **CodeCatalyst** — https://docs.aws.amazon.com/codecatalyst/latest/userguide/welcome.html
- **AWS CLI CodePipeline reference** — https://docs.aws.amazon.com/cli/latest/reference/codepipeline/
