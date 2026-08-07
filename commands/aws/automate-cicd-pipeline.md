---
description: Automate CI/CD pipeline design and implementation using AWS-native tools (CodePipeline, CodeBuild, CodeDeploy, CloudFormation, CDK, Terraform) — generates working pipeline-as-code templates with deterministic requirement checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "build CI/CD pipeline"
  - "create CodePipeline"
  - "design deployment pipeline"
  - "blue/green deployment"
  - "Lambda canary deploy"
  - "ECS rolling deploy"
  - "cross-account deployment"
  - "CodeStar Connection"
  - "buildspec.yml"
  - "pipeline as code"
  - "CloudFormation deploy pipeline"
  - "CDK pipelines"
  - "Terraform aws_codepipeline"
  - "CodePipeline V2 migration"
  - "pipeline not triggering"
  - "CodeBuild timeout"
  - "manual approval gate"
  - "SNS pipeline failure notification"
  - "cross-account deploy role"
routes_to: cicd-pipeline-automator
---

# /aws:automate-cicd-pipeline

Activate the `cicd-pipeline-automator` skill and design/implement a
CI/CD pipeline with deterministic requirement checks, CONFIRM gate,
and full pipeline-as-code emission.

## What it does

Reads a deployment scenario plus the intended operation and applies
the priority-ordered requirement-check sequence:

1. Pre-flight requirement gate — short-circuit cases where source
   credentials, build image, deploy roles, KMS key, or artifact
   bucket are missing or misconfigured.
2. Requirement gate — MANUAL_STEP_REQUIRED if any check fails
   (CodeStar Connection Pending, cross-account KMS gap, missing
   deploy role, wrong build image).
3. AUTOMATED — emit the complete pipeline-as-code template
   (CloudFormation / CDK / Terraform, per operator preference) with
   all stages wired, IAM roles, KMS artifact key, EventBridge
   triggers, SNS failure notifications, manual approval gates, and
   the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — snapshot get-pipeline first
   (UpdatePipeline replaces with no diff), execute create-pipeline /
   update-pipeline / deploy CloudFormation stack.
5. Post-verification — describe pipeline structure, verify source
   action fires on push, verify deploy role assumes correctly,
   verify EventBridge rule is active. COMPLETED only if ALL post-
   verification checks pass.

Emits a deterministic VERDICT per operation:

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

## When to invoke

Paste a deployment scenario plus the intended operation, or just
describe the scenario and ask any of:

- "build a CI/CD pipeline for my Node service"
- "design blue/green deploy for Lambda"
- "set up cross-account deployment"
- "migrate V1 pipeline to V2"
- "add a manual approval gate"

A bare repo + deploy target ("pipeline for acme/checkout to ECS")
also routes here via the orchestrator.

## Inputs

- Source provider: CodeCommit, GitHub (CodeStar Connection), S3, ECR.
- Build: language/runtime, CodeBuild image (managed or custom), VPC
  config (if private resources), cache (LOCAL or S3), buildspec path.
- Test: unit, integration, CodeGuru Reviewer, security scans (Snyk,
  Checkov, Trivy).
- Deploy target: CloudFormation (change-set), CodeDeploy (in-place
  for EC2, blue/green for Lambda/ECS), S3, ECS, Service Catalog.
- Cross-account: target account ID, deploy role ARN, artifact KMS key
  ARN, artifact bucket name.
- Manual approval: SNS topic ARN for notifications.
- Monitoring: SNS topic for failure notifications.
- Template format: CloudFormation (default), CDK, or Terraform.

## Outputs

- One VERDICT block per operation.
- REQUIREMENTS list with `[PASS]` / `[FAIL]` per check and reason
  for failure.
- For AUTOMATED: the complete pipeline-as-code template with all IAM
  roles, KMS key, artifact bucket, EventBridge rules, SNS topics,
  and stages wired.
- For MANUAL_STEP_REQUIRED: the specific gap, the exact CLI / IaC
  snippet to close it, and the reason it cannot be automated.
- NOTES with trigger model (V2 event-driven), detection lag, and
  cross-account caveats.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for CI/CD pipeline engineering).
- `/aws:audit-codepipeline-pipeline` for the audit/classification
  side — the auditor finds mis-configured pipelines; this automator
  designs and implements them.
- `/aws:audit-codebuild-project` for the CodeBuild project security
  audit.
- `/aws:audit-codedeploy-deployment-group` for the CodeDeploy
  deployment group audit.
