---
name: iac-template-automator
description: 'Generates and validates Infrastructure-as-Code templates for common AWS patterns across CloudFormation (template structure, nested stacks, cross-stack refs, drift detection, change sets), CDK v2 (L1/L2/L3 constructs, Apps, Stacks, aspects), and Terraform (HCL, modules, S3 backend with DynamoDB lock, workspaces, plan/apply/destroy). Covers VPC+subnets+NAT+routes, Lambda+API Gateway+DynamoDB, ECS Fargate+ALB, RDS Aurora+Secrets Manager rotation, CloudFront+S3+WAF. Enforces security defaults: no hardcoded secrets, least-privilege IAM (no Action:*, Resource:*), encryption by default, deletion protection, cost-allocation tags. Validates with cfn-lint, cfn-nag, tflint, checkov. Handles drift detection and state pitfalls (CFN Replacement=TRUE, Terraform manual changes outside IaC). Emits a deterministic verdict AUTOMATED with IaC template or MANUAL_STEP_REQUIRED with specific gap. Use when generating AWS infrastructure templates, scaffolding a new service, or validating IaC for security before deploy.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline template authoring. Live validation uses aws cloudformation validate-template, create-change-set, describe-stack-drift-detection-status; aws cdk synth/assertions; terraform validate/plan. Requires AWS CLI v2, CDK v2, or Terraform 1.5+ installed for live validation flows.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Generating an AWS infrastructure template (CloudFormation, CDK, or Terraform) for a common pattern (VPC, serverless, containerized service, data store, CDN), validating an existing template for security and correctness, scaffolding a new service with safe defaults, converting manually-provisioned resources to IaC, or preparing a template for a pull request / pipeline gate.
  when_not_to_use: AWS SAM transformer-specific questions (use a SAM-specific tool — SAM is a CloudFormation macro, the generated template still validates here)., AWS Application Composer visual editing sessions (this skill generates text templates, not visual canvas files)., Cross-provider Terraform (multi-cloud) orchestration — this skill is AWS-resource focused., Running terraform apply / cdk deploy against production (use an operate-type skill)., CDK v1 migration (use a migration-specific tool — this skill targets CDK v2).
  activation_triggers: generate CloudFormation template for, write CDK code for, Terraform module for AWS, IaC for VPC with NAT, serverless template Lambda API Gateway DynamoDB, ECS Fargate service template, RDS Aurora with secret rotation IaC, validate this CloudFormation template, cfn-lint findings on, terraform plan shows, drift detection on stack, convert manual AWS resources to IaC
  invocation_schema: "{output: \"Deterministic block: PATTERN / TOOL / VERDICT / TEMPLATE / VALIDATION /\\\n    \\ SECURITY / FINDINGS / REMEDIATION. VERDICT is one of AUTOMATED | MANUAL_STEP_REQUIRED.\\\n    \\ AUTOMATED means the template is complete, passes static validation, and meets\\\n    \\ the security baseline. MANUAL_STEP_REQUIRED means one or more gates failed \\u2014\\\n    \\ the output enumerates the specific gap and the required manual fix.\", properties: {\n    env: {description: Target environment token (dev/stage/prod) for workspace or\n        stack naming., type: string}, existing_template: {description: 'An existing\n        template to validate (CFN YAML/JSON, CDK TS/Python, or Terraform HCL). When\n        provided, the skill runs the validation + security gates and emits AUTOMATED\n        or MANUAL_STEP_REQUIRED.', type: string}, pattern: {description: 'The AWS\n        pattern to scaffold. One of: vpc, serverless-lambda-apigw, ecs-fargate-alb,\n        rds-aurora-secret-rotation, cloudfront-s3-waf, or a free-form description.',\n      type: string}, tool: {description: The IaC tool to target., enum: [cloudformation,\n        cdk, terraform], type: enum}}, required: [pattern, tool], type: object}"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Infrastructure as Code, IaC, CloudFormation, CDK, Cloud Development Kit, Terraform, HCL, nested stacks, cross-stack references, drift detection, change sets, cfn-lint, cfn-nag, tflint, checkov, serverless, VPC, ECS Fargate, RDS Aurora, Secrets Manager, CloudFront, WAF, least-privilege IAM, template validation
  tags: cloudformation, cdk, terraform, iac, devtools, automation, security, validate, cfn-lint, checkov
---
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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 0: Expert knowledge".
> Load when: generating any template — S3 public-by-default buckets, Replacement=TRUE, state-file truth, SAM transform, workspaces, import-without-config.

## CloudFormation patterns

> **Moved verbatim** → [references/iac-pattern-library.md](references/iac-pattern-library.md) § "CloudFormation patterns".
> Load when: targeting CloudFormation — canonical structure, nested stacks vs cross-stack refs, change sets, drift, and the five full pattern templates.

## CDK patterns

> **Moved verbatim** → [references/iac-pattern-library.md](references/iac-pattern-library.md) § "CDK patterns".
> Load when: targeting CDK v2 — App/Stack structure, L3 Vpc/LambdaRestApi/Fargate/RDS constructs, aspects.

## Terraform patterns

> **Moved verbatim** → [references/iac-pattern-library.md](references/iac-pattern-library.md) § "Terraform patterns".
> Load when: targeting Terraform — provider v5 config, S3+DynamoDB backend, VPC module, lifecycle, import.

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

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Validation toolchain".
> Load when: running cfn-lint/cfn-nag/validate-template, CDK synth + assertions, tflint/checkov/plan pipelines, or suppressing checkov baselines.

## Drift detection & state management

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Drift detection & state management".
> Load when: surfacing drift (CFN detect-stack-drift, terraform plan -detailed-exitcode) or diagnosing drift causes.

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

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — MANUAL_STEP_REQUIRED".
> Load when: emitting a MANUAL_STEP_REQUIRED verdict for a failed security gate (hardcoded secret, wildcard IAM).

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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Edge-case handling".
> Load when: circular cross-stack refs, runtime deprecation, provider schema cache, CDK Docker bundling, 460,800-byte limit, for_each empty values.

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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features".
> Load when: deciding CDK v2 bootstrap roles, provider v5 upgrade, StackSets ManagedExecution, or import config generation.

## References (load on demand)

- [references/iac-pattern-library.md](references/iac-pattern-library.md) — full CFN/CDK/Terraform pattern templates (template structure, nested stacks, change sets, VPC, serverless, ECS Fargate, RDS Aurora, CloudFront+S3+WAF, backends, lifecycle, import)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — validation pipelines (cfn-lint, cfn-nag, validate-template, CDK synth/assertions, tflint, checkov, plan) and drift-detection commands
- [references/worked-examples.md](references/worked-examples.md) — MANUAL_STEP_REQUIRED worked example (hardcoded secret + wildcard IAM role)
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious IaC behaviors, edge-case catalog, recent AWS features
- [references/security-baseline-reference.md](references/security-baseline-reference.md) — security baseline deep reference (existing)

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
