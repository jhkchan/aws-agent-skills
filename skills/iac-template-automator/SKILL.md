---
name: iac-template-automator
description: >-
  Generates and validates Infrastructure-as-Code templates for common AWS
  patterns across CloudFormation (template structure, nested stacks,
  cross-stack refs, drift detection, change sets), CDK v2 (L1/L2/L3
  constructs, Apps, Stacks, aspects), and Terraform (HCL, modules, S3
  backend with DynamoDB lock, workspaces, plan/apply/destroy). Covers
  VPC+subnets+NAT+routes, Lambda+API Gateway+DynamoDB, ECS Fargate+ALB,
  RDS Aurora+Secrets Manager rotation, CloudFront+S3+WAF. Enforces
  security defaults: no hardcoded secrets, least-privilege IAM (no
  Action:*, Resource:*), encryption by default, deletion protection,
  cost-allocation tags. Validates with cfn-lint, cfn-nag, tflint,
  checkov. Handles drift detection and state pitfalls (CFN
  Replacement=TRUE, Terraform manual changes outside IaC). Emits a
  deterministic verdict AUTOMATED with IaC template or
  MANUAL_STEP_REQUIRED with specific gap. Use when generating AWS
  infrastructure templates, scaffolding a new service, or validating
  IaC for security before deploy.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline template authoring. Live
  validation uses aws cloudformation validate-template, create-change-set,
  describe-stack-drift-detection-status; aws cdk synth/assertions; terraform
  validate/plan. Requires AWS CLI v2, CDK v2, or Terraform 1.5+ installed
  for live validation flows.
keywords:
  - Infrastructure as Code
  - IaC
  - CloudFormation
  - CDK
  - Cloud Development Kit
  - Terraform
  - HCL
  - nested stacks
  - cross-stack references
  - drift detection
  - change sets
  - cfn-lint
  - cfn-nag
  - tflint
  - checkov
  - serverless
  - VPC
  - ECS Fargate
  - RDS Aurora
  - Secrets Manager
  - CloudFront
  - WAF
  - least-privilege IAM
  - template validation
tags: [cloudformation, cdk, terraform, iac, devtools, automation, security, validate, cfn-lint, checkov]
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
  verdict_shape: "AUTOMATED | MANUAL_STEP_REQUIRED"
  when_to_use: >-
    Generating an AWS infrastructure template (CloudFormation, CDK, or
    Terraform) for a common pattern (VPC, serverless, containerized service,
    data store, CDN), validating an existing template for security and
    correctness, scaffolding a new service with safe defaults, converting
    manually-provisioned resources to IaC, or preparing a template for a
    pull request / pipeline gate.
  when_not_to_use:
    - "AWS SAM transformer-specific questions (use a SAM-specific tool — SAM is a CloudFormation macro, the generated template still validates here)."
    - "AWS Application Composer visual editing sessions (this skill generates text templates, not visual canvas files)."
    - "Cross-provider Terraform (multi-cloud) orchestration — this skill is AWS-resource focused."
    - "Running terraform apply / cdk deploy against production (use an operate-type skill)."
    - "CDK v1 migration (use a migration-specific tool — this skill targets CDK v2)."
  activation_triggers:
    - "generate CloudFormation template for"
    - "write CDK code for"
    - "Terraform module for AWS"
    - "IaC for VPC with NAT"
    - "serverless template Lambda API Gateway DynamoDB"
    - "ECS Fargate service template"
    - "RDS Aurora with secret rotation IaC"
    - "validate this CloudFormation template"
    - "cfn-lint findings on"
    - "terraform plan shows"
    - "drift detection on stack"
    - "convert manual AWS resources to IaC"
  invocation_schema:
    type: object
    required: [pattern, tool]
    properties:
      pattern:
        type: string
        description: >-
          The AWS pattern to scaffold. One of: vpc, serverless-lambda-apigw,
          ecs-fargate-alb, rds-aurora-secret-rotation, cloudfront-s3-waf,
          or a free-form description.
      tool:
        type: enum
        enum: [cloudformation, cdk, terraform]
        description: The IaC tool to target.
      existing_template:
        type: string
        description: >-
          An existing template to validate (CFN YAML/JSON, CDK TS/Python,
          or Terraform HCL). When provided, the skill runs the validation
          + security gates and emits AUTOMATED or MANUAL_STEP_REQUIRED.
      env:
        type: string
        description: Target environment token (dev/stage/prod) for workspace or stack naming.
    output: >-
      Deterministic block: PATTERN / TOOL / VERDICT / TEMPLATE /
      VALIDATION / SECURITY / FINDINGS / REMEDIATION. VERDICT is one of
      AUTOMATED | MANUAL_STEP_REQUIRED. AUTOMATED means the template is
      complete, passes static validation, and meets the security baseline.
      MANUAL_STEP_REQUIRED means one or more gates failed — the output
      enumerates the specific gap and the required manual fix.
---

# IaC Template Automator

## What this skill does

Generates production-grade Infrastructure-as-Code templates for common AWS
patterns and validates them against a security + correctness baseline. The
skill supports three IaC tools — CloudFormation, CDK v2, and Terraform 1.5+
— and five canonical patterns: VPC, serverless (Lambda + API Gateway +
DynamoDB), ECS Fargate + ALB, RDS Aurora + Secrets Manager rotation, and
CloudFront + S3 + WAF.

The verdict is binary: **AUTOMATED** when the template is complete, statically
valid, and meets the security baseline (no hardcoded secrets, least-privilege
IAM, encryption-by-default, deletion protection on prod data stores,
cost-allocation tags); **MANUAL_STEP_REQUIRED** when any gate fails, with the
specific gap enumerated in FINDINGS.

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-template-spec-gate) | Starting any new template — blocks bad inputs before generation |
| 2 | [Decision tree](#decision-tree--classification-flow) | Picking the right tool and pattern for a request |
| 3 | [CloudFlow](#cloudformation-patterns) | Target is CloudFormation (template structure, nested stacks, change sets) |
| 4 | [CDK patterns](#cdk-patterns) | Target is CDK (L1/L2/L3 constructs, aspects, apps) |
| 5 | [Terraform patterns](#terraform-patterns) | Target is Terraform (HCL, modules, state backend, workspaces) |
| 6 | [Security baseline](#security-baseline-12-rules) | The 12 hard gates every template must pass |
| 7 | [Validation toolchain](#validation-toolchain) | cfn-lint, cfn-nag, tflint, checkov, CDK assertions |
| 8 | [Drift & state](#drift-detection--state-management) | Handling drift, replacements, manual out-of-band changes |
| 9 | [Output format](#output-format-per-template) | The exact VERDICT block the skill emits |
| 10 | [NEVER anti-patterns](#never-these-things) | The hardcoded list of generation taboos |
| 11 | [Recent AWS features](#recent-aws-features-2024-2026) | What changed in CFN/CDK/Terraform in the last 24 months |

## Mindset

**One-line takeaway:** IaC is a **delegation contract** between developer
intent and AWS state. The template's job is to encode intent unambiguously;
validation's job is to catch the gaps between intent and what the template
actually says; security's job is to catch the gaps between what the template
says and what is safe to deploy.

Three facts shape every generation decision:

- **Tooling choice drives everything else.** CloudFormation, CDK, and
  Terraform each have different abstractions, defaults, and foot-guns. A
  serverless pattern with CDK uses `LambdaRestApi` (L3, batteries-included);
  with CloudFormation it is `AWS::Serverless::Api` (SAM macro) or hand-rolled
  `AWS::ApiGateway::*` resources; with Terraform it is
  `aws_api_gateway_rest_api` + `aws_api_gateway_resource` + method +
  integration + deployment + stage (10+ resources). The same intent produces
  wildly different files. Always pick the tool before generating.

- **Defaults are not safe by default.** CloudFormation `AWS::S3::Bucket`
  with no properties creates a public-by-default bucket with no encryption,
  no versioning, no lifecycle, and no access logging. CDK `Bucket` is the
  same. Terraform `aws_s3_bucket` with only a name creates the same. The
  security baseline overrides every tool's defaults — encryption, BPA,
  versioning, and access logging are non-negotiable for prod data stores.

- **Drift is the silent failure of IaC.** A template that provisions
  cleanly today may diverge from real state tomorrow when someone edits a
  resource in the console, runs an out-of-band CLI command, or applies a
  different template that touches the same resource. CFN drift detection
  and `terraform plan` are the two ways to surface drift — both must be
  part of the output, not optional add-ons.

## Pre-flight: template spec gate (run before generation)

Validate the input specification before producing any template. Several
requirements block generation — proceeding with an invalid spec produces
an insecure or non-functional template.

| Attribute | Required | Effect on plan |
|---|---|---|
| `pattern` | YES | Drives the resource set: vpc / serverless / ecs-fargate / rds-aurora / cloudfront-s3-waf |
| `tool` | YES | cloudformation / cdk / terraform |
| `env` | Recommended | dev / stage / prod — drives deletion-protection, encryption defaults, NAT gateway count |
| `existing_template` | For validation mode | When provided, skip generation and run validation + security gates |
| `account_id`, `region` | For live validation | Required only for `validate-template`, `cdk synth`, `terraform plan` |

**If the spec is incomplete** (missing pattern or tool), output:

```text
PATTERN: <unknown>
TOOL: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>). Cannot generate a complete
template without <field>.
REQUIRED:
  - pattern (vpc | serverless-lambda-apigw | ecs-fargate-alb | rds-aurora-secret-rotation | cloudfront-s3-waf)
  - tool (cloudformation | cdk | terraform)
REMEDIATION: Provide both pattern and tool. Example: "generate a CloudFormation
template for a serverless app" or "write CDK code for a VPC".
```

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify the caller has `cloudformation:ValidateTemplate`, `cloudformation:CreateChangeSet` for CFN validation.
2. For CDK: verify `cdk` CLI is on PATH and `cdk --version` returns v2.x.
3. For Terraform: verify `terraform` CLI is on PATH and `terraform version` returns 1.5+.
4. Verify the toolchain linters are installed: `cfn-lint --version`, `tflint --version`, `checkov --version`.

## Decision tree — classification flow

Apply top-to-bottom. First matching rule wins.

```
START
  │
  ├─ existing_template provided? ────────────► VALIDATION MODE (Step 7)
  │
  ├─ pattern = vpc? ─────────────────────────► VPC pattern (Step 3/4/5)
  │                                              └─ sub-decision: CDK L3 Vpc (preferred) vs CFN resources vs Terraform module
  │
  ├─ pattern = serverless-lambda-apigw? ──────► Serverless pattern (Step 3/4/5)
  │                                              └─ sub-decision: SAM (CFN macro) vs CDK LambdaRestApi (L3) vs TF aws_lambda_function
  │
  ├─ pattern = ecs-fargate-alb? ─────────────► ECS Fargate pattern (Step 3/4/5)
  │                                              └─ sub-decision: CDK ApplicationLoadBalancedFargateService (L3) vs CFN resources vs TF aws_ecs_service
  │
  ├─ pattern = rds-aurora-secret-rotation? ──► RDS Aurora pattern (Step 3/4/5)
  │                                              └─ sub-decision: CDK DatabaseInstance (L2) vs CFN AWS::RDS::DBCluster vs TF aws_rds_cluster
  │
  ├─ pattern = cloudfront-s3-waf? ───────────► CloudFront pattern (Step 3/5)
  │
  └─ (unrecognized pattern) ─────────────────► MANUAL_STEP_REQUIRED with mapping hint
```

**Tool-selection shortcut:** if the user does not specify a tool, apply:
- CDK v2 if the team already uses TypeScript or Python for app code.
- Terraform if the team uses multi-cloud or has existing Terraform modules.
- CloudFormation if the team has no Node/Python build chain, or needs AWS-only native features (e.g., SAM macros, CFN StackSets, CDK Pipelines via CFN).

## Step 0: Expert knowledge — non-obvious IaC behaviors

These behaviors change the generated template if ignored:

- **`AWS::S3::Bucket` with no properties is public-by-default, unencrypted, unversioned.** Every S3 bucket in a generated template MUST set `BucketEncryption`, `VersioningConfiguration`, `PublicAccessBlockConfiguration`, and `LifecycleConfiguration`. CDK `Bucket` is identical — pass `encryption: BucketEncryption.KMS`, `versioned: true`, `blockPublicAccess: BlockPublicAccess.BLOCK_ALL`, and `enforceSSL: true` (via a bucket policy).

- **CloudFormation stack update can REPLACE resources.** Some property changes are not updatable in-place — CloudFormation creates a new resource, redirects references, then deletes the old. The classic foot-gun: changing an RDS `DBInstanceClass` or a DynamoDB `TableName`. Always check `Replacement=TRUE` in `describe-change-set` output before applying. This is irreversible for resources with mutable state (RDS data, DynamoDB items, S3 objects).

- **CDK synthesizes to CloudFormation — `cdk synth` is the source of truth.** The TypeScript/Python code is developer-facing; the synthesized `cdk.out/cdkstack.template.json` is what gets deployed. Debug any drift against the synthesized template, not the source code. CDK v1 produces different synthesis output than v2 — this skill targets v2 only.

- **Terraform state file (`terraform.tfstate`) is the source of truth, not the AWS API.** If someone manually changes a resource outside Terraform, the state file does not know. The next `terraform plan` shows the drift. If someone manually edits the state file (rare but catastrophic), `terraform plan` may show no drift while the real state diverges. Always use S3 backend with DynamoDB lock — never commit `.tfstate` to git.

- **`AWS::Serverless::*` resources require the SAM transform.** A CloudFormation template with `Type: AWS::Serverless::Function` MUST include `Transform: AWS::Serverless-2016-10-31` in the top-level template structure. Without the transform, `validate-template` fails with `Template format error: Unrecognized resource type`.

- **CDK L1 constructs (`CfnBucket`, `CfnFunction`) are 1:1 with CloudFormation.** L2 (`Bucket`, `Function`) add AWS-curated defaults. L3 (`ApplicationLoadBalancedFargateService`, `LambdaRestApi`) compose multiple L2s into a pattern. L3 is least code, most opinionated; L1 is most control, most code. Default to L2 for production, L3 for prototypes.

- **Terraform workspaces are NOT environments.** The Terraform docs explicitly warn: workspaces are a state-file isolation mechanism, not a substitute for separate env directories. The safe pattern is one directory per env (`envs/dev/`, `envs/prod/`) with shared modules in `modules/`. Workspaces work for isolating ephemeral test stacks within one env, not for prod-vs-dev separation.

- **`terraform import` does NOT generate config.** Importing an existing resource adds it to state but does NOT write the HCL to manage it. You must hand-write the `resource "aws_..."` block matching the imported resource, then run `terraform plan` to verify no diff. Skipping this step leaves the resource in state but unmanaged — the next apply may delete it.

- **CloudFormation Outputs are plaintext, not encrypted.** Never put secrets in `Outputs` — they are visible in the console, in CLI output, and in CloudTrail event payloads. Use `AWS::SecretsManager::Secret` and reference the secret ARN in outputs; consumers fetch the secret at runtime via `GetSecretValue`.

- **CDK `bucket.grantRead(lambda)` is convenient but coarse.** It grants `s3:GetObject` and `s3:ListBucket` on `bucket.arnForFiles('*')`. For least-privilege, narrow the key pattern: `bucket.grantRead(lambda, 'data/*.json')`. The default grants more than necessary.

- **`terraform plan` against a drifted state produces a destructive plan.** If the state file says "bucket has versioning enabled" and someone disabled it via console, `terraform plan` shows a plan to "re-enable versioning" — that looks benign. But if the state says "bucket exists" and someone DELETED it via console, `terraform plan` shows a plan to "create the bucket" — also looks benign, but data is gone. Always pair `terraform plan` with a recent `terraform show -json` to compare state vs reality.

- **CloudFormation `DeletionPolicy: Retain` keeps the resource but orphans it from the stack.** On stack delete, the resource is not deleted but the stack no longer tracks it. Re-importing it into a new stack is manual (`terraform import`-equivalent for CFN). Use `DeletionPolicy: Retain` for data stores (RDS, S3, DynamoDB), `UpdateReplacePolicy: Retain` for the same resources on replacement.

- **CDK aspects apply cross-cutting changes after construct tree construction.** An aspect like "add tags to everything" or "enforce encryption on all buckets" walks the construct tree post-build. This is powerful but order-dependent: an aspect that overrides an explicit property wins silently. Always log aspect application in a build hook.

- **Terraform `count` and `for_each` create resources that are addressable by index/key.** `count = 3` creates `aws_subnet.this[0]`, `[1]`, `[2]`. Removing an item from the middle shifts all subsequent indices, forcing Terraform to destroy-and-recreate. Use `for_each` with stable string keys for any list that may change membership.

- **CloudFormation drift detection does NOT cover all properties.** It detects drift on a subset of resource attributes — typically anything set by the customer. Service-side automatic changes (e.g., a Lambda runtime auto-update) do not register as drift. Run `describe-stack-drift-detection-status` weekly on prod stacks; do not rely on real-time drift alerts.

- **`cfn-lint` and `cfn-nag` catch different things.** `cfn-lint` checks spec compliance (correct property names, required fields, type mismatches). `cfn-nag` checks security posture (wildcard IAM, missing encryption, plaintext secrets). Run BOTH — neither is a subset of the other. The combined output is the validation surface.

- **Terraform AWS provider v5 has breaking changes from v4.** Most visible: the `s3` resource refactor (multiple small resources became one), the `default_tags` argument on the provider block, and the removal of several deprecated resources. Pin the provider version: `source = "hashicorp/aws" version = "~> 5.0"`. Do NOT upgrade without running `terraform plan` and reviewing every diff.

- **SAM CLI `sam deploy --capabilities CAPABILITY_NAMED_IAM` is required for any template that creates IAM resources.** Without it, CloudFormation rejects the create/update with `InsufficientCapabilities`. The skill always emits the required capability flag in deploy commands.

- **`AWS::CDK::Metadata` resource in synthesized templates contains construct metadata, including version info.** Some compliance frameworks flag this as information disclosure. Suppress with `cdk.json` `"metadata": {"cdk_version": false}` if your org treats CDK version as sensitive.

## CloudFormation patterns

### Template structure (canonical)

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: "Purpose of this stack — one sentence."
Metadata:
  Comment: "Generator: iac-template-automator. Owner: <team>."
Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, stage, prod]
    Default: dev
Mappings:
  RegionConfig:
    us-east-1: { AmiId: ami-0abcdef1234567890 }
    us-west-2: { AmiId: ami-0fedcba9876543210 }
Conditions:
  IsProd: !Equals [!Ref Environment, prod]
Resources:
  # Resources here
Outputs:
  StackName:
    Description: "Stack identifier for cross-stack references."
    Value: !Ref AWS::StackName
    Export:
      Name: !Sub "${AWS::StackName}-StackName"
Rules:
  # Rule-based validation
```

### Nested stacks vs cross-stack references

| Pattern | When to use | Trade-off |
|---|---|---|
| **Nested stack** (`Type: AWS::CloudFormation::Stack`) | Tight lifecycle coupling — child always created/deleted with parent | Hard to update child independently; output values flow up only |
| **Cross-stack reference** (`Fn::ImportValue`) | Loose coupling — stacks have independent lifecycles | Exported value cannot be modified while any consumer imports it; creates dependency graph |
| **StackSets** | Deploy same template across N accounts and/or regions | Requires admin in the management account; drift detection per instance |

**Cross-stack reference pitfall:** an `Export` cannot be deleted while any
other stack imports it. To change an exported value, you must first update
all consumers to stop importing it, then update the producer, then re-add
the imports. Plan cross-stack reference changes as multi-step deployments.

### Change sets (ALWAYS preview before apply)

```bash
# Create a change set against an existing stack
aws cloudformation create-change-set \
  --stack-name prod-app \
  --change-set-name prod-app-update-$(date +%s) \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --parameters ParameterKey=Environment,ParameterValue=prod

# Inspect changes BEFORE applying
aws cloudformation describe-change-set \
  --stack-name prod-app \
  --change-set-name prod-app-update-XXXXX \
  --query 'Changes[*].[ResourceChange.Action,ResourceChange.LogicalResourceId,ResourceChange.Replacement]'

# Look for Replacement=TRUE — these resources will be DESTROYED and RECREATED
# If any data-bearing resource (RDS, DynamoDB, S3 with data) shows TRUE,
# BLOCK the apply and require manual review.
```

### Drift detection

```bash
# Detect drift on a stack (async — takes minutes for large stacks)
aws cloudformation detect-stack-drift --stack-name prod-app

# Poll status
aws cloudformation describe-stack-drift-detection-status \
  --stack-name prod-app --stack-drift-detection-id <id>

# Get the drift report
aws cloudformation describe-stack-resource-drifts \
  --stack-name prod-app \
  --stack-resource-drift-status-filters MODIFIED DELETED
```

### CloudFormation: VPC + subnets + NAT + routes

```yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - { Key: Name, Value: !Sub "${AWS::StackName}-vpc" }
        - { Key: Environment, Value: !Ref Environment }

  InternetGateway:
    Type: AWS::EC2::InternetGateway
  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.1.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - { Key: Name, Value: !Sub "${AWS::StackName}-public-1" }

  # ... repeat for public-2, private-1, private-2, NAT gateway, route tables
```

### CloudFormation: Lambda + API Gateway + DynamoDB (serverless)

```yaml
Transform: AWS::Serverless-2016-10-31
Resources:
  Table:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub "${AWS::StackName}-table"
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - { AttributeName: pk, AttributeType: S }
        - { AttributeName: sk, AttributeType: S }
      KeySchema:
        - { AttributeName: pk, KeyType: HASH }
        - { AttributeName: sk, KeyType: RANGE }
      SSESpecification: { SSEEnabled: true }
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true }
      Tags:
        - { Key: Environment, Value: !Ref Environment }

  Function:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./src
      Handler: app.handler
      Runtime: python3.12
      MemorySize: 256
      Timeout: 30
      Environment:
        Variables:
          TABLE_NAME: !Ref Table
      Policies:
        - DynamoDBReadPolicy: { TableName: !Ref Table }
        - DynamoDBWritePolicy: { TableName: !Ref Table }
      Events:
        Api:
          Type: Api
          Properties:
            Path: /items
            Method: ANY
```

### CloudFormation: ECS Fargate + ALB

Generates `AWS::ECS::Cluster`, `AWS::ElasticLoadBalancingV2::LoadBalancer`
(ALB), two `AWS::ElasticLoadBalancingV2::TargetGroup` (one per AZ for
high-availability), `AWS::ElasticLoadBalancingV2::Listener` (443 with SSL),
`AWS::ECS::TaskDefinition` with Fargate, `AWS::ECS::Service` wired to the
target group, plus the `AWS::IAM::Role` execution and task roles scoped to
`ecs-tasks.amazonaws.com`. Always include
`AWS::ElasticLoadBalancingV2::ListenerRule` with priority and conditions.

### CloudFormation: RDS Aurora + Secrets Manager rotation

```yaml
DBCluster:
  Type: AWS::RDS::DBCluster
  Properties:
    Engine: aurora-postgresql
    EngineVersion: "16.5"
    MasterUsername: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:username}}"
    MasterUserPassword: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:password}}"
    DatabaseName: appdb
    StorageEncrypted: true
    DeletionProtection: !If [IsProd, true, false]
    Tags:
      - { Key: Environment, Value: !Ref Environment }

DBSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    GenerateSecretString:
      SecretStringTemplate: '{"username":"appadmin"}'
      GenerateStringKey: password
      ExcludeCharacters: '"@/\'
      PasswordLength: 32

SecretRotation:
  Type: AWS::SecretsManager::RotationSchedule
  Properties:
    SecretId: !Ref DBSecret
    RotationLambdaARN: !GetAtt RotationFunction.Arn
    RotationRules: { AutomaticallyAfterDays: 30 }
```

### CloudFormation: CloudFront + S3 + WAF

CloudFront + S3 origin with Origin Access Control (OAC, replaces the
deprecated OAI), WAFv2 web ACL with managed rule groups
(AWSManagedRulesCommonRuleSet, AWSManagedRulesSQLiRuleSet), bucket policy
scoped to `cloudfront.amazonaws.com` via service principal with
`StringEquals` on the S3 resource ARN. Default cache behavior: TLSv1.2,
forwarded values whitelist, logging to a separate S3 bucket.

## CDK patterns

### App + Stack structure (CDK v2)

```typescript
import { App, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class AppStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    // constructs here
  }
}

const app = new App();
new AppStack(app, 'prod-app', {
  env: { account: '111111111111', region: 'us-east-1' },
  tags: { Environment: 'prod', Owner: 'platform' },
});
```

### CDK: VPC (L3 Vpc construct — preferred)

```typescript
import { Vpc, SubnetType } from 'aws-cdk-lib/aws-ec2';

const vpc = new Vpc(this, 'Vpc', {
  ipAddresses: IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 3,
  subnetConfiguration: [
    { name: 'public', subnetType: SubnetType.PUBLIC, cidrMask: 24 },
    { name: 'private', subnetType: SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
    { name: 'isolated', subnetType: SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
  ],
  natGateways: 2, // prod: 2 for HA; dev: 0 or 1 for cost
  flowLogs: { CloudWatch: { trafficType: FlowTrafficType.ALL } },
});
```

The L3 `Vpc` construct creates the VPC, IGW, NAT gateways, public/private
subnets per AZ, route tables, EIPs, and S3 VPC endpoint in one call. Hand-
rolling the same in CFN or TF requires ~80 lines.

### CDK: Lambda + API Gateway + DynamoDB (L3 LambdaRestApi)

```typescript
import { LambdaRestApi } from 'aws-cdk-lib/aws-apigateway';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { Table, BillingMode, AttributeType } from 'aws-cdk-lib/aws-dynamodb';

const table = new Table(this, 'Table', {
  partitionKey: { name: 'pk', type: AttributeType.STRING },
  sortKey: { name: 'sk', type: AttributeType.STRING },
  billingMode: BillingMode.PAY_PER_REQUEST,
  encryption: TableEncryption.AWS_MANAGED,
  pointInTimeRecovery: true,
  removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
});

const fn = new NodejsFunction(this, 'Function', {
  runtime: Runtime.NODEJS_20_X,
  entry: 'src/handler.ts',
  handler: 'handler',
  environment: { TABLE_NAME: table.tableName },
});

table.grantReadWriteData(fn);

const api = new LambdaRestApi(this, 'Api', {
  handler: fn,
  proxy: true,
  deployOptions: { stageName: 'prod' },
});
```

### CDK: ECS Fargate + ALB (L3 ApplicationLoadBalancedFargateService)

```typescript
import { ApplicationLoadBalancedFargateService } from 'aws-cdk-lib/aws-ecs-patterns';

const service = new ApplicationLoadBalancedFargateService(this, 'Service', {
  cluster,
  memoryLimitMiB: 1024,
  cpu: 512,
  taskImageOptions: {
    image: ContainerImage.fromEcrRepository(repo, 'latest'),
    containerPort: 8080,
  },
  publicLoadBalancer: false, // internal ALB behind CloudFront
  desiredCount: 3,
});
```

### CDK: RDS Aurora + secret rotation (L2 DatabaseInstance)

```typescript
import { DatabaseCluster, DatabaseClusterEngine } from 'aws-cdk-lib/aws-rds';
import { Credentials } from 'aws-cdk-lib/aws-rds';
import { SecretRotation, SecretRotationEngine } from 'aws-cdk-lib/aws-secretsmanager-rotation';

const cluster = new DatabaseCluster(this, 'Db', {
  engine: DatabaseClusterEngine.auroraPostgres({ version: AuroraPostgresEngineVersion.VER_16_5 }),
  credentials: Credentials.fromGeneratedSecret('appadmin'),
  defaultDatabaseName: 'appdb',
  storageEncrypted: true,
  deletionProtection: true,
  writer: ClusterInstance.serverlessV2('writer'),
  readers: [ClusterInstance.serverlessV2('reader1')],
});

new SecretRotation(this, 'Rotation', {
  secret: cluster.secret!,
  rotationLambda: rotationFn,
  automaticallyAfter: Duration.days(30),
});
```

### CDK aspects (cross-cutting changes)

```typescript
import { Aspects, IAspect } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';

class EnforceEncryptionAspect implements IAspect {
  public visit(node: Construct) {
    if (node instanceof s3.Bucket && !node.encryptionKey) {
      node.enableEncryption();
    }
  }
}

Aspects.of(app).add(new EnforceEncryptionAspect());
```

## Terraform patterns

### Provider configuration (v5)

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "tf-state-prod-111111111111"
    key            = "app/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "platform"
    }
  }
}
```

### S3 backend with DynamoDB lock (REQUIRED for any team)

```hcl
# Bootstrapped OUT-OF-BAND (not in the same state file)
resource "aws_s3_bucket" "state" {
  bucket = "tf-state-prod-111111111111"
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

resource "aws_dynamodb_table" "locks" {
  name         = "tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}
```

### Terraform: VPC module

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.stack_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = var.environment == "prod" ? true : false
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true
  enable_dns_support   = true

  enable_flow_log                = true
  create_flow_log_cloudwatch_iam_role = true
  create_flow_log_cloudwatch_log_group = true

  tags = { Environment = var.environment }
}
```

### Terraform: Lambda + API Gateway + DynamoDB

Generates `aws_lambda_function`, `aws_apigatewayv2_api` (HTTP API preferred
over REST for new workloads — fewer resources, lower cost), `aws_dynamodb_table`
with `server_side_encryption { enabled = true }`, plus IAM role and policy.

### Terraform: ECS Fargate + ALB

Generates `aws_ecs_cluster`, `aws_ecs_task_definition` with `requires_compatibilities =
["FARGATE"]`, `aws_ecs_service`, `aws_lb_target_group`, `aws_lb_listener`,
`aws_lb_listener_rule`, plus the data source for the ALB. Always set
`deployment_circuit_breaker` to avoid infinite deploy loops.

### Terraform: lifecycle (plan/apply/destroy)

```bash
# Initialize providers and download modules
terraform init

# Format and validate
terraform fmt -recursive
terraform validate

# Preview changes (REQUIRED before apply)
terraform plan -out=tfplan

# Apply the planned changes (auto-approve is forbidden in prod)
terraform apply tfplan

# Destroy (NEVER run in prod without a manual confirmation gate)
terraform destroy
```

### Terraform: importing existing resources

```bash
# Import an existing resource into state
terraform import aws_s3_bucket.my_bucket my-bucket-name

# WARNING: import does NOT generate config. You must write the matching
# resource block by hand, then run terraform plan to verify no diff.

# Generate config from an imported resource (Terraform 1.5+)
terraform plan -generate-config-out=generated.tf
```

## Security baseline (12 rules)

Every generated template MUST pass these gates. A failure on any rule
flips the verdict from AUTOMATED to MANUAL_STEP_REQUIRED.

| # | Rule | Tool equivalent |
|---|---|---|
| 1 | No hardcoded secrets in any property or default value | cfn-nag W11, checkov CKV_AWS_41 |
| 2 | IAM policies must NOT use `Action: "*"` or `Resource: "*"` | cfn-nag F3, checkov CKV_AWS_1 |
| 3 | IAM roles must NOT use `Principal: {"Service": "*"}` or `{"AWS": "*"}` | cfn-nag F1 |
| 4 | S3 buckets MUST set `PublicAccessBlockConfiguration` with all 4 blocks | cfn-nag F14, checkov CKV_AWS_53 |
| 5 | S3 buckets MUST have `BucketEncryption` (SSE-KMS preferred) | cfn-nag W31, checkov CKV_AWS_19 |
| 6 | RDS / DynamoDB / EBS MUST have encryption at rest enabled | cfn-nag W92, checkov CKV_AWS_16 |
| 7 | RDS clusters in prod MUST have `DeletionProtection: true` | cfn-nag W33 |
| 8 | DynamoDB tables MUST have `PointInTimeRecoverySpecification` enabled | checkov CKV_AWS_80 |
| 9 | Lambda environment variables containing secrets MUST reference Secrets Manager | cfn-nag W37 |
| 10 | All resources MUST carry Environment + Owner tags (cost allocation) | checkov CKV_AWS_8 (defaults via provider) |
| 11 | CloudFront distributions MUST use TLSv1.2 minimum and redirect HTTP to HTTPS | checkov CKV_AWS_174 |
| 12 | Security groups MUST NOT allow `0.0.0.0/0` on ports 22, 3389, or database ports | cfn-nag W2, W9, W40 |

**Rule precedence:** security rules 1-3 are CRITICAL (block deployment).
Rules 4-9 are HIGH (block prod deployment, allow dev with a finding).
Rules 10-12 are MEDIUM (warn, do not block).

## Validation toolchain

### CloudFormation validation pipeline

```bash
# 1. Spec compliance — property names, types, required fields
cfn-lint template.yaml

# 2. Security posture — wildcard IAM, missing encryption, plaintext secrets
cfn-nag template.yaml

# 3. CloudFormation server-side validation (catches macros and transforms)
aws cloudformation validate-template \
  --template-body file://template.yaml

# 4. Change-set preview against an existing stack
aws cloudformation create-change-set \
  --stack-name <stack> --change-set-name preview-$(date +%s) \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND

aws cloudformation describe-change-set \
  --stack-name <stack> --change-set-name preview-XXXXX \
  --query 'Changes[*].ResourceChange.[Action,LogicalResourceId,Replacement]'
```

### CDK validation pipeline

```bash
# 1. Synthesize to CloudFormation
cdk synth --all

# 2. Type-check the source (TypeScript)
npm run build  # tsc --noEmit

# 3. Unit tests with CDK assertions
npm test  # jest — uses @aws-cdk/assertions

# 4. Lint the synthesized template
cfn-lint cdk.out/*.template.json
cfn-nag cdk.out/*.template.json
```

**CDK assertions example:**

```typescript
import { Template } from 'aws-cdk-lib/assertions';

test('bucket is encrypted', () => {
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::S3::Bucket', {
    BucketEncryption: {
      ServerSideEncryptionConfiguration: [{
        ServerSideEncryptionByDefault: { SSEAlgorithm: 'aws:kms' },
      }],
    },
  });
});
```

### Terraform validation pipeline

```bash
# 1. Format check (does not modify)
terraform fmt -check -recursive -diff

# 2. Syntax and provider validation
terraform init -backend=false
terraform validate

# 3. Lint with tflint (provider-aware — catches deprecated resources)
tflint --init
tflint

# 4. Security with checkov
checkov -d . --framework terraform

# 5. Plan (REQUIRED before apply — shows diff against real state)
terraform plan -out=tfplan

# Inspect the plan JSON for destructive actions
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] | test("delete|replace|create-delete"))'
```

### checkov baseline suppression

When a checkov finding is a false positive or accepted risk, suppress it
explicitly — never disable the rule globally.

```hcl
# Terraform inline suppression
resource "aws_s3_bucket" "logs" {
  bucket = "app-logs"
  #checkov:skip=CKV_AWS_18:Logs bucket does not need access logging (chicken-and-egg)
}
```

## Drift detection & state management

### CloudFormation drift detection

```bash
# Schedule drift detection (runs async)
DRIFT_ID=$(aws cloudformation detect-stack-drift --stack-name prod-app --query 'StackDriftDetectionId --output text)

# Poll status (returns DETECTION_IN_PROGRESS | DETECTION_COMPLETE | DETECTION_FAILED)
aws cloudformation describe-stack-drift-detection-status \
  --stack-name prod-app --stack-drift-detection-id $DRIFT_ID

# Get the drift report
aws cloudformation describe-stack-resource-drifts --stack-name prod-app \
  --stack-resource-drift-status-filters MODIFIED DELETED NOT_CHECKED
```

**Caveat:** drift detection does NOT cover every property. Service-side
auto-updates (Lambda runtime patches, RDS engine minor version bumps) do
not register as drift. Run drift detection weekly on prod stacks as a
baseline; pair with `configservice get-resource-config-history` for
property-level drift on critical resources.

### Terraform drift detection

```bash
# Plan shows drift as a diff
terraform plan -detailed-exitcode
# Exit codes:
#   0 = no diff (no drift)
#   1 = error
#   2 = diff present (DRIFT DETECTED)
```

**Caveat:** `terraform plan` compares state file to AWS API. If the state
file itself is stale (someone ran `terraform apply` on a different machine
without pushing state), `plan` shows a false drift. Always verify state
recency via `terraform state pull` timestamp before interpreting plan output.

### Common drift causes

- Console clicks (operator edits a resource in the AWS console).
- Out-of-band CLI commands (`aws s3api put-bucket-policy` outside IaC).
- Service-side auto-remediation (Config rule or SSM Automation kicks in).
- Lambda runtime auto-update (deprecation handling).
- AWS Support troubleshooting (rare but real).

## NEVER (these things)

- NEVER hardcode secrets in any template property, default value, or
  environment variable. Use `Parameters` with `NoEcho: true` (still weak —
  visible in stack parameters), or better, `AWS::SecretsManager::Secret`
  with `GenerateSecretString`, or `{{resolve:secretsmanager:...}}` for CFN,
  `secret.parsedJsonSecretString` for CDK, or `data.aws_secretsmanager_secret`
  for Terraform. A secret in a CloudFormation Parameter is recoverable from
  CloudTrail event history — Parameters are NOT a secrets store.

- NEVER use `Action: "*"` or `Resource: "*"` in an IAM policy. Both
  expand blast radius. The exception is a permissions BOUNDARY (which is
  a maximum, not a grant) — but even there, prefer listing the specific
  service namespaces you intend to delegate. Use the IAM Policy Simulator
  to derive least-privilege from CloudTrail history.

- NEVER deploy an IAM role with `Principal: {"AWS": "*"}` or
  `{"Service": "*"}`. Both allow any AWS account or any service to assume
  the role. Always scope to a specific account, service, or OIDC/SAML
  provider with `aws:SourceArn` or `aws:SourceAccount` conditions.

- NEVER omit `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`
  on data-bearing resources (RDS, DynamoDB, S3 with data, EFS). Without
  these, a stack delete or a property-replacement destroys data
  permanently. For prod, also enable `DeletionProtection: true` on RDS
  clusters at the resource level — it is a second line of defense.

- NEVER commit `terraform.tfstate` to git. The state file contains
  sensitive resource attributes (secret values in some cases, resource
  ARNs, account IDs). Always use a remote backend (S3 with DynamoDB lock
  at minimum). Add `*.tfstate` and `*.tfstate.*` to `.gitignore`.

- NEVER run `terraform apply -auto-approve` in production. Always review
  the plan interactively. Set `-auto-approve` only in ephemeral dev/test
  environments, and gate prod applies behind a CI/CD pipeline that
  requires human approval on the plan step.

- NEVER trust `terraform import` to generate config. Import only writes
  to state. You must hand-write the matching `resource` block and run
  `terraform plan` to verify zero-diff before any apply. Skipping this
  leaves the imported resource unmanaged — the next apply may destroy it.

- NEVER use Terraform workspaces as environments. Workspaces are a state
  isolation mechanism within one config — they share all variables,
  modules, and provider blocks. The correct pattern for prod-vs-dev is
  separate directories (`envs/dev/`, `envs/prod/`) sharing modules in
  `modules/`. Workspaces are fine for ephemeral PR-preview stacks within
  one env.

- NEVER skip `terraform validate`, `cfn-lint`, or `cfn-nag` in CI. These
  tools catch issues that the human eye misses — property name typos,
  required field omissions, security anti-patterns. A pipeline that
  deploys templates without linting is a pipeline that ships drift and
  security regressions to prod.

- NEVER put secrets in CloudFormation `Outputs`. Outputs are visible in
  the console, in CLI output, in CloudTrail event payloads, and in
  StackSets aggregation APIs. Use a Secrets Manager secret and output
  only the secret ARN; consumers fetch the value via
  `aws secretsmanager get-secret-value` at runtime.

- NEVER omit `Capabilities` on a CFN create/update if the template
  creates IAM resources or uses nested applications. CFN rejects the
  request with `InsufficientCapabilities` if `CAPABILITY_NAMED_IAM` or
  `CAPABILITY_AUTO_EXPAND` is missing. Always emit the right capability
  flag in deploy commands.

- NEVER change an RDS `DBInstanceIdentifier` or a DynamoDB `TableName`
  without planning for replacement. Both are immutable identifiers —
  CloudFormation will destroy and recreate the resource. Snapshot RDS
  before the change, and verify no clients reference the old identifier.

- NEVER skip `terraform plan -out=tfplan` before apply. Saving the plan
  to a file and applying THAT file guarantees the apply runs the exact
  changes you reviewed. Applying without `-out` re-evaluates the diff,
  which can change between the plan step and the apply step if someone
  else touched the resources in between.

- NEVER suppress cfn-nag or checkov findings globally. Suppress per-
  resource with an inline comment (checkov: `#checkov:skip=CKV_AWS_X:reason`;
  cfn-nag: `Metadata: { cfn_nag: { rules_to_suppress: [...] } }`). Always
  include a justification. Global suppression hides real findings in
  future templates.

- NEVER generate a CloudFront distribution with `ViewerProtocolPolicy:
  allow-all`. Always use `redirect-to-https` (default) or `https-only`.
  The same for origin protocol policy: use `https-only` for origin
  communication, never `http-only` or `match-viewer`.

- NEVER use CDK `asset.HashType.SOURCE` as a deploy trigger for prod. The
  hash includes file metadata that varies across machines — the same
  code can produce different hashes, forcing needless redeployments. Use
  deterministic builds via `docker build --no-cache` and pin lockfiles.

## Output format (per template)

```text
PATTERN: <vpc | serverless-lambda-apigw | ecs-fargate-alb | rds-aurora-secret-rotation | cloudfront-s3-waf | custom>
TOOL: <cloudformation | cdk | terraform>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TEMPLATE:
  <the generated template content, or path to template file if large>
VALIDATION:
  - [PASS] cfn-lint: no findings
  - [PASS] cfn-nag: no findings
  - [PASS] validate-template: ok
  - [WARN] change-set preview: 1 resource Replacement=TRUE (see FINDINGS)
SECURITY:
  - [PASS] no hardcoded secrets
  - [PASS] IAM least-privilege (no Action:* / Resource:*)
  - [PASS] S3 encryption enabled (SSE-KMS)
  - [PASS] DynamoDB PITR enabled
  - [WARN] RDS DeletionProtection missing on dev cluster (dev-only)
FINDINGS:
  - [INFO] VPC uses CDK L3 Vpc construct — preferred over hand-rolled L1
  - [HIGH] Changing DBInstanceClass on prod-app-db triggers Replacement=TRUE
REMEDIATION:
  1. <step 1>
  2. <step 2>
```

### Worked example — AUTOMATED serverless template

```text
PATTERN: serverless-lambda-apigw
TOOL: cloudformation
VERDICT: AUTOMATED
TEMPLATE:
  Transform: AWS::Serverless-2016-10-31
  Resources:
    Table: { Type: AWS::DynamoDB::Table, Properties: { ... SSESpecification: { SSEEnabled: true }, PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true } } }
    Function: { Type: AWS::Serverless::Function, Properties: { ... Policies: [ DynamoDBReadPolicy, DynamoDBWritePolicy ] } }
VALIDATION:
  - [PASS] cfn-lint: 0 findings
  - [PASS] cfn-nag: 0 findings
  - [PASS] validate-template: ok (CAPABILITY_NAMED_IAM required)
SECURITY:
  - [PASS] No hardcoded secrets (Lambda reads from Secrets Manager via env var SECRET_ARN)
  - [PASS] IAM least-privilege (DynamoDBReadPolicy/WritePolicy scoped to !Ref Table)
  - [PASS] DynamoDB SSE enabled + PITR enabled
FINDINGS:
  - [INFO] SAM Transform required (Transform: AWS::Serverless-2016-10-31) — present
  - [INFO] Deploy with --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
REMEDIATION: None required. Deploy with:
  aws cloudformation deploy --stack-name prod-app --template-file template.yaml \
    --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides Environment=prod
```

### Worked example — MANUAL_STEP_REQUIRED (hardcoded secret)

```text
PATTERN: rds-aurora-secret-rotation
TOOL: cloudformation
VERDICT: MANUAL_STEP_REQUIRED
TEMPLATE: (not generated — gate failed)
VALIDATION:
  - [BLOCK] cfn-nag F3: IAM policy with Action: '*' on the rotation Lambda role
  - [BLOCK] cfn-nag W11: MasterUserPassword hardcoded as plaintext string
SECURITY:
  - [FAIL] Hardcoded secret in MasterUserPassword: "MyPassword123!"
  - [FAIL] IAM role RotationExecutionRole has Action: "*" on Resource: "*"
FINDINGS:
  - [CRITICAL] MasterUserPassword is a plaintext literal. CloudTrail records this
    value in the CreateStack event. Rotate immediately via update-stack.
  - [CRITICAL] RotationExecutionRole grants admin permissions — a compromised
    rotation Lambda can do anything in the account.
REMEDIATION:
  1. Replace MasterUserPassword with {{resolve:secretsmanager:DBSecret:SecretString:password}}
  2. Add AWS::SecretsManager::Secret with GenerateSecretString
  3. Scope RotationExecutionRole to rds:ModifyDBCluster + secretsmanager:GetSecretValue + secretsmanager:PutSecretValue
  4. Re-run cfn-nag — both findings should clear
```

## Pre-flight safety checks (run before any deploy CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`aws cloudformation deploy`, `cdk deploy`, `terraform apply`), the
  automator MUST emit:
  `CONFIRM: About to <action> on <stack-name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` and wait for explicit `yes`.

- **Change-set preview is REQUIRED for CFN updates to existing stacks.**
  Never run `aws cloudformation deploy` against an existing prod stack
  without first running `create-change-set` and inspecting for
  `Replacement=TRUE`. Data-bearing resources with replacement require
  manual confirmation.

- **`terraform plan -out=tfplan` is REQUIRED before apply.** Apply the
  saved plan file, not a fresh plan. Review the JSON for destructive
  actions: `terraform show -json tfplan | jq '.resource_changes[] |
  select(.change.actions[] | test("delete|replace|create-delete"))'`.

- **`cdk diff` is REQUIRED before `cdk deploy` to existing stacks.**
  `cdk diff` compares the synthesized template to the deployed stack.
  Any resource showing `[-old] [+new]` (replacement) must be manually
  confirmed before deploy.

- **Backup state before destructive changes.**
  - CFN: `aws cloudformation describe-stacks --stack-name <name> > backup.json`
  - Terraform: `cp terraform.tfstate terraform.tfstate.bak.$(date +%s)`
  - CDK: state lives in CloudFormation — same backup as CFN.

- **Pin provider versions in Terraform.** Always specify
  `version = "~> 5.0"` for the AWS provider. Unpinned providers can
  introduce breaking changes via minor version bumps that silently alter
  plan output.

- **Pin CDK version in package.json.** Always specify a tilde range
  (`"aws-cdk-lib": "~2.150.0"`). Caret ranges allow minor version bumps
  that may change synthesized output and trigger unnecessary diffs.

## Edge-case handling

- **Circular cross-stack references.** Stack A exports a value that Stack
  B imports; Stack B exports a value that Stack A imports. CloudFormation
  detects the cycle and rejects both creates. Solution: lift the shared
  resource into a third stack (Stack C) that both A and B import from.

- **Lambda runtime deprecation.** AWS announces runtime deprecations
  (e.g., nodejs16.x EOL). Generated templates MUST use a supported
  runtime (python3.12, nodejs20.x). Cross-reference
  https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html for
  the current supported list.

- **Terraform provider schema cache.** `terraform validate` uses a cached
  provider schema. After upgrading the provider version, run
  `terraform init -upgrade` to refresh the cache, otherwise validate may
  report phantom errors.

- **CDK bundling requires Docker.** `NodejsFunction` and
  `PythonFunction` bundle assets via Docker. If Docker is not running,
  `cdk synth` fails with `Error: docker exited with code 1`. Provide a
  fallback or warn the operator.

- **CloudFormation template size limit.** 460,800 bytes after transforms.
  Templates approaching the limit must use nested stacks or
  `AWS::Include` transforms to split. CDK and Terraform handle this
  automatically (CDK via assets; Terraform via modules).

- **Terraform `for_each` on a list with empty values.** If `for_each =
  toset(var.list)` and the list has empty strings, Terraform errors.
  Filter with `compact(var.list)`.

## Reference — IaC tool comparison

| Dimension | CloudFormation | CDK v2 | Terraform |
|---|---|---|---|
| Authoring language | YAML / JSON | TypeScript / Python | HCL |
| Abstraction levels | Resources / Modules / Macros | L1 / L2 / L3 / Aspects | Resources / Modules |
| State backend | AWS-managed (per stack) | AWS-managed (via CFN) | Self-managed (S3 + DynamoDB lock) |
| Drift detection | `detect-stack-drift` (limited properties) | Inherited from CFN | `terraform plan` (full) |
| Resource coverage | ~1,000 resource types | Inherited from CFN | ~1,000 (via aws provider) |
| Multi-resource replacement | Atomic per-stack | Atomic per-stack | Sequential per-resource |
| Plan preview | `describe-change-set` | `cdk diff` | `terraform plan` (best-in-class) |
| IAM capability flag | `CAPABILITY_NAMED_IAM` | Inherited from CFN | None |
| Vendor lock-in | AWS-only | AWS-only (community has minimal multi-cloud) | Multi-cloud |

## Recent AWS features (2024-2026)

- **CDK v2 default synthesizer (2024):** The new default synthesizer uses
  bootstrap roles with stricter permissions (`cdk-hnb659fds`). Teams
  migrating from v1 must re-bootstrap with the new role suffix or
  deployments fail with `NeedPerform` errors.
- **Terraform AWS provider v5 (2024):** Breaking changes from v4 — the
  S3 bucket refactor (multiple `aws_s3_bucket_*` resources consolidated
  into `aws_s3_bucket`), `default_tags` moved to provider block, several
  deprecated resources removed. Pin to `~> 5.0` and review the upgrade
  guide before migrating.
- **AWS Application Composer (2024-2025):** Visual CloudFormation designer
  in the console. Generates SAM-based templates from a drag-and-drop
  canvas. Useful for prototyping; for production, prefer text-authored
  templates for reviewability and version control.
- **CloudFormation resource import (2024):** `ImportValue`-style import
  of existing resources into a new or existing stack without disruption.
  Useful for migrating manually-provisioned resources into IaC. Pairs
  with `DeletionPolicy: Retain` for safety.
- **CDK GitOps pipeline (2024-2025):** `cdk-pipelines-github` and
  `cdk-pipelines-codepipeline` enable push-to-deploy workflows. The
  pipeline runs synth, asset upload, and `cdk deploy` across environments
  with approval gates. Generated templates should target
  `pipelines.CodePipeline` for prod-grade CD/CD.
- **CloudFormation StackSets managed execution (2024-2025):** New
  `ManagedExecution` flag enables StackSets to retry failed deployments
  to individual accounts/regions without failing the entire operation.
  Always set `ManagedExecution: { Active: true }` on org-wide StackSets.
- **Terraform 1.7+ `terraform plan -generate-config-out` (2025):**
  Generates config for imported resources, eliminating the hand-write
  step after `terraform import`. Requires Terraform 1.7+.
- **AWS SAM CLI `sam build --use-container` (2024-2025):** Builds Lambda
  packages in a Docker container matching the Lambda runtime, ensuring
  native dependency compatibility (esp. Python `cryptography`, Node
  `sharp`). Recommend for any Lambda with native deps.

## Domain

AWS CloudOps / Infrastructure-as-Code Automation & DevTools.

## AWS documentation

- **AWS CloudFormation User Guide** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/
- **CloudFormation Best Practices** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html
- **AWS CDK Developer Guide** — https://docs.aws.amazon.com/cdk/v2/guide/
- **CDK API Reference** — https://docs.aws.amazon.com/cdk/api/v2/
- **Terraform AWS Provider** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **cfn-lint** — https://github.com/aws-cloudformation/cfn-lint
- **cfn-nag** — https://github.com/stelligent/cfn_nag
- **checkov** — https://www.checkov.io/
- **tflint** — https://github.com/terraform-linters/tflint
- **AWS SAM** — https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/
