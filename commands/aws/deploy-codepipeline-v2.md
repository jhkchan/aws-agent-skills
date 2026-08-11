---
description: Provision a production-grade CodePipeline V2 with event-driven triggers, source/build/deploy actions, namespace variables, manual approval, and cross-account deploy.
nl_triggers:
  - "create a CodePipeline"
  - "provision pipeline V2"
  - "event-driven pipeline"
  - "CodePipeline trigger"
  - "CodePipeline branch filter"
  - "CodePipeline manual approval"
  - "cross-account deployment"
  - "namespace variables CodePipeline"
  - "CodePipeline GitHub source"
  - "CodeConnections pipeline"
  - "CodePipeline ECS deploy"
  - "CodePipeline CloudFormation deploy"
  - "CodePipeline CodeDeploy"
  - "V1 to V2 migration"
routes_to: codepipeline-v2-deployer
---

# /aws:deploy-codepipeline-v2

Activate the `codepipeline-v2-deployer` skill and produce a deployment
plan for a production-grade CodePipeline V2 pipeline.

## What it does

Reads a deployment specification (pipeline type V2, source, trigger,
build, deploy, cross-account, manual approval, namespace variables)
and produces an ordered deployment plan with:

1. Pre-flight specification gate — validates pipeline type (V2),
   source action (CodeCommit / S3 / GitHub via CodeConnections),
   trigger filter (branch / path / tag), deploy action (CloudFormation
   / ECS / S3 / Service Catalog / CodeDeploy). Blocks deployment
   (PREREQUISITES_MISSING) on missing fields.
2. V1 vs V2 fit — confirms V2 is correct (event-driven triggers,
   namespace variables, per-execution pricing, no polling).
3. Source action — CodeCommit (native), S3 (EventBridge), or GitHub /
   GitLab / Bitbucket via CodeConnections (us-east-1).
4. Trigger configuration — event-driven filter scoped to production
   branches and service paths. Flags unscoped triggers (fire on every
   push to every branch).
5. Build action — CodeBuild with exported namespace variables
   (IMAGE_URI, IMAGE_TAG).
6. Deploy actions — CloudFormation (CREATE_REPLACE / CHANGE_SET_REPLACE),
   ECS (direct image), S3 (extract), Service Catalog, CodeDeploy
   (in-place / blue-green for EC2).
7. Manual approval gate — between stages, with ExternalEntityLink,
   CustomData, and SNS notification.
8. Namespace variables — flow forward only; consumed in downstream
   action configs and stage conditions. Validates against silent
   empty-string failures.
9. Cross-account deployment — KMS key policy + cross-account IAM role
   + S3 bucket policy coordination. Warns that "Access Denied" on S3
   is usually a KMS policy issue.
10. Artifact bucket security — block public access + KMS CMK (not
    SSE-S3) + versioning.
11. Pipeline IAM role — scoped to exact ARNs (no wildcards on S3, KMS,
    CodeBuild, CodeCommit).

Emits a deterministic deployment plan per pipeline:

```text
PIPELINE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Type / Source / Trigger / Build / Deploy / Approval / Variables /
  Cross-account / Artifact bucket / Pipeline role
CHECKLIST:
  [x] Pipeline type V2 confirmed (event-driven, no polling)
  [x] Source action configured (CodeCommit / S3 / GitHub)
  [x] Trigger with branch/path/tag filter (NOT unscoped)
  ...
FINDINGS:
  - [INFO] Pricing: $0.002/execution (event-driven)
  - [WARN] Trigger filter MUST scope to production branches
DEPLOY_COMMANDS:
  <ordered list of aws codepipeline / kms / iam / s3api commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create a CodePipeline V2 with CodeCommit source"
- "provision an event-driven pipeline with branch filter"
- "set up a cross-account pipeline to deploy CloudFormation"
- "add a manual approval gate between build and deploy"
- "configure a GitHub pipeline via CodeConnections"
- "deploy ECS via CodePipeline with namespace variables"
- "migrate V1 polling pipeline to V2 event-driven"

A bare source + build + deploy + "deploy V2 pipeline" also routes
here via the orchestrator.

## Inputs

- **Required:** pipeline_type (V2), source (CodeCommit / S3 / GitHub
  via CodeConnections), trigger_filter (branch / paths / tags),
  deploy_action (CloudFormation / ECS / S3 / ServiceCatalog /
  CodeDeploy), pipeline_role_arn or role policy document.
- **Optional:** build_project, manual_approval (between stages),
  namespace_variables, cross_account_target_role_arn,
  kms_key_arn, artifact_bucket_name, sns_topic_arn for approvals.

## Outputs

- One VERDICT block per pipeline (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- ARCHITECTURE summary with type/source/trigger/build/deploy/approval/
  variables/cross-account/artifact-bucket/role.
- CHECKLIST with all 10 deployment dimensions validated.
- FINDINGS with cost estimates and V2-specific warnings (unscoped
  trigger, no approval timeout, silent empty-string variables).
- DEPLOY_COMMANDS with ordered `aws codepipeline`, `aws kms`,
  `aws iam`, and `aws s3api` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for CodePipeline V2 provisioning).
- `/aws:audit-codepipeline-pipeline` for post-deployment auditing
  (PollForSourceChanges misconfig, missing triggers, IAM wildcards,
  artifact bucket public exposure).
- `/aws:audit-codebuild-project` for build project security.
- `/aws:audit-codecommit-repository` for source repository posture.
