---
name: cicd-pipeline-automator
description: Designs and implements AWS-native CI/CD pipelines end-to-end using CodePipeline, CodeBuild, CodeDeploy, CloudFormation, CDK, and Terraform. Generates working pipeline-as-code templates (CloudFormation AWS::CodePipeline::Pipeline, CDK Pipeline module, Terraform aws_codepipeline) wired with source (CodeCommit / GitHub / CodeStar Connection), build (buildspec.yml, VPC-aware CodeBuild), test (unit, integration, CodeGuru Reviewer security scans), and deploy (CloudFormation change-set, CodeDeploy in-place / blue-green, ECS rolling, S3, Service Catalog) stages. Handles cross-account deployment (IAM roles, KMS artifact key, resource-based policy), blue/green (Lambda traffic shifting 10/90, ECS circuit breaker, Route53 weighted), pipeline monitoring (CloudWatch Events on state changes, SNS failure notifications, manual approval), and CodePipeline V2 event-driven triggers. Emits a verdict (AUTOMATED with pipeline template | MANUAL_STEP_REQUIRED with specific gap). Use when building a CI/CD pipeline, designing.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws codepipeline create-pipeline, update-pipeline, get-pipeline, get-pipeline-state, start-pipeline- execution, list-pipelines, aws codebuild create-project, batch-get- projects, aws codedeploy create-application, aws cloudformation create-change-set, execute-change-set, aws codestar-connections create-connection (AWS CLI v2, SSO...
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
  when_to_use: Designing or implementing a CI/CD pipeline using CodePipeline, CodeBuild, CodeDeploy, CloudFormation, CDK, or Terraform. Setting up source (CodeCommit, GitHub, CodeStar Connection), build (buildspec.yml, VPC-aware CodeBuild), test (unit, integration, CodeGuru), or deploy (CloudFormation change-set, CodeDeploy in-place or blue/green, ECS rolling, S3, Service Catalog) stages. Wiring cross-account deployment (IAM roles, KMS key, bucket policy). Implementing blue/green (Lambda traffic shifting, ECS circuit breaker, Route53 weighted). Adding pipeline monitoring (CloudWatch Events, SNS, manual approval). Migrating to CodePipeline V2 or troubleshooting pipeline failures.
  activation_triggers: build CI/CD pipeline, create CodePipeline, design deployment pipeline, blue/green deployment, Lambda canary deploy, ECS rolling deploy, cross-account deployment, CodeStar Connection, buildspec.yml, pipeline as code, CloudFormation deploy pipeline, CDK pipelines, Terraform aws_codepipeline, CodePipeline V2 migration, pipeline not triggering, CodeBuild timeout, manual approval gate, SNS pipeline failure notification
  invocation_schema: 'Input: either (a) a deployment scenario describing app, source, build, test, deploy targets, and constraints (language, environment, cross-account, blue/green), OR (b) an existing pipeline definition + the operation (create, update, troubleshoot, migrate V2). Output: deterministic OPERATION/VERDICT/REQUIREMENTS/PIPELINE_TEMPLATE/ MANUAL_GAPS block per operation, where VERDICT is AUTOMATED (full template generated) or MANUAL_STEP_REQUIRED (specific gap blocks automation).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CodePipeline, CodeBuild, CodeDeploy, CI/CD, pipeline as code, CloudFormation, CDK, Terraform, blue/green, canary, cross-account deployment, CodeStar Connection, CodeCommit, GitHub, buildspec, change-set, manual approval, pipeline monitoring, CodePipeline V2, CodeCatalyst
  tags: codepipeline, codebuild, codedeploy, ci-cd, devtools, automate, cloudformation, cdk, terraform
---

# CI/CD Pipeline Automator

## What this skill does

Capability overview moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the full capability summary (the Quick navigation table covers the essentials).

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

**Stage matrix** moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing providers per stage (source/build/test/deploy/approval/invoke + pitfalls).

## Mindset

**One-line takeaway:** pipeline-as-code is the only sustainable way
to manage CI/CD at scale. Hand-built pipelines in the console have no
review trail, no rollback, no diff. Driven by three CodePipeline
realities:

The three CodePipeline realities moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for design rationale (source-credential trap, cross-account KMS, V2 triggers vs V1 polling).

## Pre-flight: requirement gate

Run before emitting any template. Missing requirements produce
MANUAL_STEP_REQUIRED with the exact gap.

**Live-account pre-flight (skip if offline plan audit):**
Full command list moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand for live pre-flight (pipelines, connections, build images, deploy roles, KMS key, artifact bucket, STS).

**Malformed input:** rule moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
If the scenario is missing required fields, emit `VERDICT: MANUAL_STEP_REQUIRED` with `GAP: Scenario missing required field <field>. Provide <field> to proceed.`

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

All Step 0 behaviors moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a design depends on a non-obvious CodePipeline behavior (pipeline vs action roles, encryptionKey, triggers, cross-account, execution modes).

### Step 1: Source stage design

| Source | Provider | Credential | Trigger |
|---|---|---|---|
| CodeCommit | `CodeCommit` (AWS) | None (IAM-native) | EventBridge on `referenceUpdated` |
| GitHub | `CodeStarConnection` (AWS) | CodeStar Connection ARN | V2 trigger OR EventBridge rule |
| GitHub (legacy) | `GitHub` (ThirdParty) | OAuth token (DEPRECATED) | Polling or webhook (deprecated) |
| S3 | `S3` (AWS) | Pipeline role on bucket | EventBridge on `ObjectCreated` |
| ECR | `ECR` (AWS) | Pipeline role on ECR | EventBridge on `ImagePushed` |

**V2 trigger example** moved verbatim to [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md).
Load on demand when wiring V2 Git triggers (Triggers → GitConfiguration → Push → Branches / FilePathIncludes).

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

**buildspec.yml minimum** moved verbatim to [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md).
Load on demand when emitting the build stage.

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

All deploy-strategy blocks (CloudFormation change-set, CodeDeploy in-place and blue/green, ECS circuit breaker, Route 53 weighted) moved verbatim to [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md).
Load on demand when designing the Deploy stage.

### Step 5: Cross-account deployment design

The three IAM pieces + trust-policy JSON + KMS/bucket policy grants moved verbatim to [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md).
Load on demand for cross-account wiring (source-account role, target trust with aws:SourceAccount, artifact KMS decrypt).

### Step 6: Pipeline monitoring design

EventBridge failure-rule and manual-approval blocks moved verbatim to [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md).
Load on demand for monitoring/approval wiring (missing NotificationArn = silent gate).

### Step 7: Emit template (AUTOMATED) or gap (MANUAL_STEP_REQUIRED)

If all pre-flight requirements pass, emit the complete pipeline-as-code
template (CloudFormation / CDK / Terraform, per the operator's
preference). The template includes:
The includes list (CodePipeline / CodeBuild / IAM / KMS / S3 / Events / SNS resources) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when emitting the AUTOMATED template.

If any requirement is missing, emit `MANUAL_STEP_REQUIRED` with the
specific gap and the exact CLI / IaC snippet to close it.

## Patterns — pipeline-as-code templates

All three full templates (CloudFormation, CDK, Terraform) moved verbatim to [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md).
Load on demand for boilerplate lookup.

## Diagnostic flows

All five flows (pipeline not triggering, CodeBuild timeout, empty change-set, IAM AccessDenied, KMS cross-account) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when troubleshooting a running pipeline.

## Output format (per operation)

Template block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
The same literal labels are enforced below under "STRICT output contract"; the primary worked example follows below.

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
Full block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when a requirement is [FAIL] (cross-account KMS gap).

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
pipeline template that fails silently on first run or a gap report
that leaves the operator stuck. Self-check EVERY emitted block against
these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT substitute markdown headings or camelCase variants.

```text
OPERATION: <create | update | troubleshoot | migrate-v2>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TARGET: <pipeline-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
PIPELINE_TEMPLATE: <inline CloudFormation / CDK / Terraform, or "(held in draft)">
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet to close the gap>
    REASON: <why this cannot be automated>
NOTES: <trigger model, detection lag, cross-account caveats>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: AUTOMATED` when any requirement is `[FAIL]`.**
   A single `[FAIL]` MUST produce `VERDICT: MANUAL_STEP_REQUIRED`. The
   AUTOMATED verdict certifies that the template is apply-ready — any
   unresolved gap invalidates that certification.

2. **NEVER emit a `[FAIL]` requirement without a corresponding
   `MANUAL_GAPS` entry.** Every `[FAIL]` line in REQUIREMENTS MUST have
   a matching GAP/REMEDIATION/REASON block in MANUAL_GAPS with the
   exact CLI or IaC snippet that closes the gap. A `[FAIL]` with no
   remediation leaves the operator stuck.

3. **NEVER emit a pipeline using GitHub v1 (`ThirdParty/GitHub`).** The
   v1 OAuth integration is DEPRECATED and uses a persistent token. All
   GitHub/GitLab/Bitbucket sources MUST use CodeStar Connection
   (`AWS/CodeStarConnection`). If the operator provides a v1 source,
   emit `MANUAL_STEP_REQUIRED` with the CodeStar Connection migration.

4. **NEVER emit a cross-account deploy role without the
   `aws:SourceAccount` condition on the trust policy.** A
   `Principal: {"Service": "codepipeline.amazonaws.com"}` without a
   source-account condition allows ANY pipeline in ANY account to
   assume the role. The REMEDIATION snippet MUST include the condition.

5. **NEVER emit a manual approval gate without `NotificationArn`.** An
   approval action without NotificationArn is a silent gate — approvers
   are never alerted and the pipeline sits in `InProgress` indefinitely.
   If no SNS topic exists, emit `MANUAL_STEP_REQUIRED` with the
   `aws sns create-topic` snippet.

6. **NEVER emit `VERDICT: AUTOMATED` without an EventBridge
   failure-notification rule in the PIPELINE_TEMPLATE.** A pipeline
   that fails silently leaves stale code in production. The template
   MUST include the `AWS::Events::Rule` matching `FAILED` and
   `CANCELED` states targeting an SNS topic.

7. **NEVER emit a V1 pipeline with `PollForSourceChanges: false`
   without the corresponding EventBridge trigger rule in the template.**
   Setting false without the rule means the pipeline never auto-triggers.
   Either set `PollForSourceChanges: true` (with a warning about polling
   cost) or emit V2 with triggers.

8. **NEVER emit `PIPELINE_TEMPLATE: (held in draft)` without listing
   which specific `[FAIL]` items blocked it.** The MANUAL_GAPS block
   MUST enumerate every gap. A draft hold with no gap list forces the
   operator to diff the requirements manually.

### Perfect example output — AUTOMATED

Every requirement is [PASS]. The template is complete. Copy this shape.
Full example moved verbatim to [references/worked-examples.md](references/worked-examples.md).
The primary worked example above — "Worked example — AUTOMATED (greenfield pipeline)" — stays in this file.

### Perfect example output — MANUAL_STEP_REQUIRED
Full example moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the MANUAL_STEP_REQUIRED exemplar.

**Self-check before emit:**
- [ ] Any `[FAIL]` in REQUIREMENTS → VERDICT is MANUAL_STEP_REQUIRED?
- [ ] Every `[FAIL]` has a matching GAP/REMEDIATION/REASON block?
- [ ] No GitHub v1 (`ThirdParty/GitHub`) in the template?
- [ ] Cross-account role has `aws:SourceAccount` condition?
- [ ] Approval gate has `NotificationArn`?
- [ ] AUTOMATED template includes EventBridge failure rule?
- [ ] No `PollForSourceChanges: false` without EventBridge rule (V1)?

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for 2024-2026 CodePipeline / CodeBuild / CodeDeploy / CodeCatalyst feature coverage.

## Error handling — procedure-level pipeline failures

All five failure branches (CodeBuild VPC errors, empty change-set, cross-account AssumeRole, CodeConnections revision, approval timeout) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a pipeline-build or deploy step fails.

## Edge cases

All three edge cases (approval auto-reject timeout, cross-partition source, DeletionPolicy: Retain) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for these rare cases.

## References (load on demand)

- [references/pipeline-templates-and-deployment-strategies.md](references/pipeline-templates-and-deployment-strategies.md) — full CloudFormation/CDK/Terraform templates; deploy strategies (Step 4); cross-account IAM (Step 5); monitoring/approval wiring (Step 6); buildspec and V2 triggers.
- [references/worked-examples.md](references/worked-examples.md) — output-format template, MANUAL_STEP_REQUIRED example, perfect AUTOMATED/MANUAL exemplars, template includes list.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live pre-flight commands, malformed-input rule, troubleshooting flows.
- [references/error-handling.md](references/error-handling.md) — procedure-level pipeline failure branches.
- [references/advanced-patterns.md](references/advanced-patterns.md) — capability overview, stage matrix, design rationale, Step 0 expert knowledge, edge cases, 2024-2026 features.

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
