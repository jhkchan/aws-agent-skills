# Advanced patterns - CodePipeline V2 Deployer (load on demand)

## Mindset - V2 vs V1 background (moved from SKILL.md)

**One-line takeaway:** a V2 pipeline is not "a V1 pipeline with extra
features" — it is an **event-driven, variable-aware orchestration
product** where triggers fire on Git pushes (no polling), namespace
variables carry data between stages, and stages can run selectively
based on filter conditions. The trigger configuration and the
cross-account IAM/KMS wiring are the load-bearing decisions; the
stages themselves are deterministic once those are correct.

Three facts make V2 provisioning different from V1:

- **V2 is event-driven by design — polling is gone.** V1 polled
  CodeCommit / S3 on a schedule (avg 17s latency, per-poll cost). V2
  uses triggers that fire on CloudWatch Events from the source —
  sub-second latency, no polling cost. A V2 pipeline with NO trigger
  never runs automatically.

- **Triggers have filter conditions (branches, file paths, tags).**
  V2 triggers accept a JSON filter that scopes which pushes start a
  pipeline run. A trigger without a filter starts a run on EVERY push
  to EVERY branch — a common mistake that floods the pipeline history.
  Always scope to `refs/heads/main` (or your production branch).

- **Namespace variables pass data between stages.** V2 introduces
  stage-level variables (`Namespace`) that downstream stages consume.
  This replaces V1 hacks like "stash the value in an SSM Parameter
  from CodeBuild and read it in the next stage." Variables flow
  forward only.

## Step 0 - Expert heuristic: V1 to V2 migration gotchas

Migrating a V1 pipeline to V2 looks like changing one field
(`pipelineType: V1` → `V2`). It is not. The migration touches
triggers, IAM, and variables.

```text
V1 → PollForSourceChanges: true (or false + CloudWatch Events rule)
     No namespace variables; stages run sequentially.
V2 → PollForSourceChanges MUST be false (V2 rejects polling).
     Triggers block replaces CloudWatch Events rule.
     Namespace variables flow forward across stages.
     Stage conditions can skip stages based on variables.
```

**Migration failure modes:**
- **Stale `PollForSourceChanges: true`.** V2 rejects this with a
  confusing "Invalid action configuration" error. Set
  `DetectOptions: false` and use a trigger instead.
- **CloudWatch Events rule orphan.** V1 pipelines often have a
  side-car rule calling `StartPipelineExecution`. After migration,
  delete the rule — V2 triggers handle this natively, and a leftover
  rule can fire BOTH the V2 trigger and the legacy rule (duplicate
  executions).
- **IAM role trust policy scope.** V1 roles trust
  `codepipeline.amazonaws.com` broadly. V2 supports condition keys
  like `codepipeline:FullPipelineArn` — tighten the trust policy.
- **Stage variable references.** If V1 used SSM Parameter Store to
  pass values between stages (a common workaround), V2 namespace
  variables replace this. Migrate the workaround or it will continue
  to run alongside the new wiring (silent conflict).

A baseline model treats V1→V2 as a one-line change. The real change
touches triggers, IAM, variables, and stage conditions.

## Expert heuristic: trigger filter precision and the every-push trap

V2 triggers without a filter fire on every push. A baseline model
suggests the simplest possible trigger (no filter) "because we want
every commit to deploy." This is wrong in two ways:

```text
push to feature/auth-refactor branch
  → V2 trigger (no filter) fires
  → CodeBuild runs full test suite
  → CloudFormation deploy attempts to update prod stack
  → if change-set has IAM changes: pipeline blocks at CAPABILITY_IAM
  → if change-set has no IAM changes: prod stack updated from a feature branch
cost: $0.002 × N feature pushes/day + risk of unintended prod change
```

**Resolution heuristics:**
- Always scope `Branches.Includes` to production branches (`main`,
  `release/*`).
- For monorepos, scope `FilePaths.Includes` to the service's sub-tree
  — pushes touching only `docs/` should NOT trigger the deploy.
- Use a SEPARATE trigger for `feature/*` that runs a build-only
  pipeline (no deploy) — gates merge quality without deploying.
- For tagged releases, use `Tags.Includes: ["deploy=prod"]` to enforce
  "deploy only when explicitly tagged."

A baseline model treats "trigger" as a boolean. In V2, trigger
filters are the primary blast-radius control.

## Expert heuristic: namespace variables and the silent-empty-string failure

Namespace variables that are missing (undefined in the producing
action) render as empty string `""` in the consuming action — NOT an
error. A pipeline that deploys `Image1: #{BuildVars.IMAGE_URI}` with
an undefined `IMAGE_URI` will deploy an empty image string, which ECS
silently rejects with a confusing "InvalidParameterException."

**Resolution heuristics:**
- Always add a stage condition that validates the variable is
  non-empty before the deploy stage:
  `Conditions: [{ConditionKey: "#{BuildVars.IMAGE_URI}", ConditionOperator: StringEquals, ConditionValue: "", Not: true}]`
- Verify the CodeBuild project's `exported-variables` block lists
  every variable consumed downstream. Missing variables in
  `exported-variables` produce empty strings silently.
- For CloudFormation deploys, use `OutputFileName` to write a JSON
  file of outputs, then reference via `#{DeployVars.Outputs.StackId}`.
- Secrets must NEVER be namespace variables — they render in plaintext
  in CloudTrail and the pipeline execution history.

A baseline model assumes a missing variable throws an error. In V2
it silently deploys an empty string.

## Step 9 - Artifact bucket security (commands + hardening)

```bash
aws s3api create-bucket --bucket my-pipeline-artifacts --region us-east-1 \
  --block-public-access BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-encryption --bucket my-pipeline-artifacts \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"arn:aws:kms:us-east-1:111111111111:key/abc"}}]}'

aws s3api put-bucket-versioning --bucket my-pipeline-artifacts \
  --versioning-configuration Status=Enabled
```

**Mandatory hardening:**
- Block all public access (all four sub-settings true).
- KMS encryption with a customer-managed key (CMK), not S3-managed
  (SSE-S3). Cross-account requires CMK.
- Versioning enabled for rollback (a bad deploy can restore the prior
  artifact).
- Lifecycle rule to transition to Glacier after 90 days (cost
  optimization).
- Bucket policy denies unencrypted uploads (`aws:SecureTransport:
  false`) and denies uploads without the KMS key.

## Step 10 - Pipeline IAM role (policy + hard constraints)

The pipeline role is the blast radius. Scope it to:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
     "Resource": ["arn:aws:s3:::my-pipeline-artifacts","arn:aws:s3:::my-pipeline-artifacts/*"],
     "Condition": {"StringEquals": {"s3:x-amz-server-side-encryption-aws-kms-key-id": "arn:aws:kms:us-east-1:111111111111:key/abc"}}},
    {"Effect": "Allow", "Action": ["kms:Decrypt","kms:GenerateDataKey","kms:DescribeKey"],
     "Resource": "arn:aws:kms:us-east-1:111111111111:key/abc"},
    {"Effect": "Allow", "Action": ["codecommit:GetRepository","codecommit:GetBranch","codecommit:GitPull"],
     "Resource": "arn:aws:codecommit:us-east-1:111111111111:my-service"},
    {"Effect": "Allow", "Action": ["codebuild:StartBuild","codebuild:BatchGetBuilds"],
     "Resource": "arn:aws:codebuild:us-east-1:111111111111:project/my-service-build"},
    {"Effect": "Allow", "Action": ["sts:AssumeRole"],
     "Resource": "arn:aws:iam::<target-account>:role/CrossAccountCFNExecution"}
  ]
}
```

**Hard constraints:**
- The `Condition` on S3 forces KMS encryption — without it, the
  pipeline can upload unencrypted artifacts.
- The CodeBuild / CodeCommit / CloudFormation actions are scoped to
  the exact project / repo / role. Wildcards create a privilege
  escalation path (a malicious CodeBuild project could read other
  pipelines' artifacts).
- For V2, the trust policy can scope to
  `codepipeline:FullPipelineArn` so the role cannot be assumed by
  other pipelines in the account.

## Edge-case handling

- **Trigger fires but pipeline does not start.** Verify the trigger's
  `SourceActionName` matches the source action's `Name` exactly
  (case-sensitive). Renaming the source action without updating the
  trigger is a common mistake.

- **Cross-account deploy fails with "Access Denied" on S3 GetObject.**
  The KMS key policy does not grant the target role `kms:Decrypt`.
  The S3 bucket policy may be correct but the KMS key policy is the
  actual blocker. Verify both.

- **CodeBuild exports empty variables.** The variable is not listed
  in `exported-variables` in `buildspec.yml`, OR the build failed
  before setting the variable. Always add `exported-variables` and
  validate with a stage condition.

- **Manual approval blocks forever.** Approval timeouts are NOT
  enforced. Use an external scheduled Lambda to auto-reject stale
  approvals (e.g., older than 48 hours).

- **V1 → V2 migration shows duplicate executions.** A leftover
  CloudWatch Events rule from V1 fires alongside the V2 trigger.
  Delete the rule: `aws events delete-rule --name <name>`.

- **GitHub source connection shows PENDING.** CodeConnections requires
  a one-time browser handshake. Open the console in us-east-1, click
  "Update pending connection," authorize via the GitHub OAuth flow.

- **ECS deploy fails with "TaskDefinition not found."** The task
  definition family must exist before the pipeline runs. For new
  services, run a one-time `aws ecs register-task-definition`.

## Recent AWS features (2024-2026)

- **Pipeline V2 type (GA):** event-driven triggers (no polling),
  namespace variables between stages, stage conditions, per-execution
  pricing. V1 pipelines continue to work; new pipelines should
  default to V2.
- **Pipeline V2 with EC2 / CodeDeploy:** V2 supports CodeDeploy
  deploy actions for EC2 in-place and blue/green (including target
  group swapping). Manual approvals now support `ExternalEntityLink`
  and richer `CustomData`.
- **Stage-level conditions and pipeline rollback (2024-2025):** V2
  supports `Conditions` blocks that skip stages based on namespace
  variables, plus `RollbackStage` for automatic rollback on stage
  failure.
- **CodeConnections (formerly CodeStar Connections):** renamed;
  supports GitHub, GitLab, Bitbucket, GitHub Enterprise Server.
  Connections are region-locked to us-east-1.
- **Trigger filter enhancements:** filters now support
  `FilePaths.Excludes` (negate paths) and glob patterns in branch
  filters (`release/*` matches `release/v1.2`).

