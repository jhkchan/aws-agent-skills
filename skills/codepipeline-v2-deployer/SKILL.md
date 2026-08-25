---
name: codepipeline-v2-deployer
description: Provisions production-grade CodePipeline V2-type pipelines with event-driven triggers (no polling), structure (stages and actions), source actions (CodeCommit, S3, GitHub via CodeConnections), build actions (CodeBuild), deploy actions (CloudFormation CREATE_CHANGE_SET / ECS deploy, S3 deploy, Service Catalog), manual approval actions, namespace variables passed between stages, cross-account deployment via KMS key policy + IAM roles, artifact bucket security (block public access, KMS encryption), and EC2/CodeDeploy deployments. Emits a READY_TO_DEPLOY checklist and ordered aws codepipeline create-pipeline commands. Use when provisioning a V2 pipeline, configuring event-based triggers with branch filter, wiring cross-account CloudFormation deploy, setting up manual approval gates, or replacing V1 polling pipelines with V2 event-driven.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws codepipeline create-pipeline, update-pipeline, create-connection (CodeConnections), put-job- approval-result, aws kms create-key / put-key-policy, aws iam create-role / attach-role-policy, and aws s3api create-bucket with block-public-access (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new CodePipeline V2-type pipeline for production, configuring event-driven triggers with branch / path filter, wiring cross-account CloudFormation deploy via KMS-encrypted artifacts, setting up manual approval gates between stages, using namespace variables to pass data between stages, configuring ECS or S3 or Service Catalog deploy actions, replacing V1 polling pipelines with V2 event-driven triggers, or hardening the artifact bucket (block public access + KMS).
  activation_triggers: create a CodePipeline, provision pipeline V2, event-driven pipeline, CodePipeline trigger, CodePipeline branch filter, CodePipeline manual approval, cross-account deployment, namespace variables CodePipeline, CodePipeline GitHub source, CodeConnections pipeline, CodePipeline ECS deploy, CodePipeline CloudFormation deploy, CodePipeline CodeDeploy, V1 to V2 migration
  invocation_schema: 'Input shape (one of): (a) a deployment specification including pipeline type (V2), source (CodeCommit / S3 / GitHub / CodeConnections), build (CodeBuild), deploy (CloudFormation / ECS / S3 / Service Catalog / CodeDeploy), triggers (event filter), namespace variables, cross-account targets, manual approval stages; (b) a partial spec for interactive refinement; (c) an existing V1 pipeline for V2 migration review. Output shape: { PIPELINE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CodePipeline, CodePipeline V2, pipeline type V2, event-driven pipeline, trigger, Git trigger, branch filter, CodeConnections, source action, CodeCommit source, S3 source, GitHub source, CodeBuild, build action, deploy action, CloudFormation deploy, ECS deploy, S3 deploy, Service Catalog deploy, CodeDeploy, EC2 deploy, manual approval, namespace variables, pipeline variables, cross-account, KMS key, artifact bucket, IAM role, CloudWatch Events, EventBridge
  tags: codepipeline, dev-tools, deploy, pipeline-v2, event-driven, triggers, codebuild, cloudformation-deploy, ecs-deploy, cross-account, manual-approval, namespace-variables, codeconnections, kms-artifacts
---

# CodePipeline V2 Deployer

## Mindset

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| Pipeline type | V2 (event-driven, no polling) | 1 |
| Source | CodeCommit / S3 / GitHub via CodeConnections | 2 |
| Trigger | Event-driven filter (branch, paths, tags) | 3 |
| Build | CodeBuild project, artifacts to S3 | 4 |
| Deploy | CloudFormation / ECS / S3 / Service Catalog / CodeDeploy | 5 |
| Manual approval | Optional approval gate between stages | 6 |
| Namespace variables | Variables passed between stages | 7 |
| Cross-account | KMS key + IAM roles for target accounts | 8 |
| Artifact bucket | Block public access + KMS encryption | 9 |
| Pipeline IAM role | Scoped to source/build/deploy actions | 10 |

## Pre-flight: deployment specification gate

Validate the input specification. Several requirements **block
deployment** — proceeding with an invalid spec produces a
non-functional or insecure pipeline.

**Live-account pre-flight checks (skip if doing offline plan):**
1. Verify IAM permissions for `codepipeline:CreatePipeline`,
   `UpdatePipeline`, `codebuild:CreateProject` (or existing project
   ARN), `iam:CreateRole`, `iam:AttachRolePolicy`, `kms:CreateKey`,
   `kms:PutKeyPolicy`, `s3:CreateBucket`, `s3:PutBucketPolicy`,
   `s3:PutPublicAccessBlock`.
2. For GitHub source, verify a CodeConnections connection exists in
   `us-east-1` (the connection must be in us-east-1 even if the
   pipeline is in another region) and is in `AVAILABLE` state.
3. For cross-account deploy, verify the target account ID, KMS key
   ARN, and cross-account IAM role ARN. The KMS key policy MUST grant
   the pipeline role `kms:GenerateDataKey` and `kms:Decrypt`.
4. For CloudFormation deploy, verify the target stack name and the IAM
   execution role in the target account. For ECS, verify the cluster,
   service, and task definition family exist.

| Attribute | Value | Effect on plan |
|---|---|---|
| `pipelineType` | `V2` / `V1` | V2 = event-driven, triggers required, namespace variables supported. V1 = polling, no triggers, no variables. |
| Source | `CodeCommit` / `S3` / `GitHub` (CodeConnections) | Determines trigger type and connection ARN. |
| Trigger | `event-driven` filter | Required for V2 — without one, the pipeline never auto-runs. |
| Deploy | `CloudFormation` / `ECS` / `S3` / `ServiceCatalog` / `CodeDeploy` | Determines IAM role policy scope and (for CFN) change-set mode. |
| Cross-account | `true` / `false` | If true, requires KMS key policy + cross-account IAM role. |

**If the deployment spec is incomplete** (missing source, trigger, or
deploy action), output:

```text
PIPELINE_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting
pipeline would be non-functional or insecure.
REQUIRED:
  - source (CodeCommit / S3 / GitHub via CodeConnections)
  - trigger_filter (branch / paths / tags — required for V2)
  - deploy_action (CloudFormation / ECS / S3 / ServiceCatalog / CodeDeploy)
  - pipeline_role_arn or role policy document
```

## STRICT output contract

When this skill is invoked with a V2 pipeline provisioning request,
the agent MUST respond with the deployment plan defined in the "Output
format" section using the literal all-caps labels `PIPELINE_SPEC:`,
`VERDICT:`, `ARCHITECTURE:`, `CHECKLIST:`, `FINDINGS:`, and
`DEPLOY_COMMANDS:`. Do NOT preface the block with prose, headings, or
disclaimers — emit it as the first lines of the response. This
contract is what assertion-based evals and downstream provisioning
pipelines rely on; deviating from the literal labels breaks automation
silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear. The two
verdicts are mutually exclusive.

## Quick navigation

| Section | When to read |
|---|---|
| Pre-flight specification gate | Always — verify before planning |
| Step 0 — Expert heuristic: V1 → V2 migration | Migrating from polling |
| Step 1 — Pipeline type confirmation (V2) | Boundary call |
| Step 2-3 — Source + Trigger | CodeCommit / S3 / GitHub + filter scoping |
| Step 4-5 — Build (CodeBuild) + Deploy actions | Action wiring |
| Step 6-7 — Manual approval + Namespace variables | Gated releases, stage-to-stage data |
| Step 8-10 — Cross-account + Artifact bucket + Pipeline role | Security + IAM |
| NEVER do these things | Review before signing off |
| Output format | The literal plan template |
| references/triggers-and-namespace-variables-reference.md | Trigger filter + variable deep dive |
| references/cross-account-and-deploy-actions-reference.md | Cross-account + per-deploy-type contracts |

## Process — Architecture planning (apply in order)

### Step 0: Expert heuristic — V1 to V2 migration gotchas

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


### Step 1: Pipeline type confirmation (V2)

| Dimension | V1 | V2 |
|---|---|---|
| Trigger model | Polling or CloudWatch Events rule | Triggers (event-driven, sub-second) |
| Trigger filter | Branch only (via EventBridge rule) | Branch, paths, tags, glob patterns |
| Namespace variables | No | Yes (stage-to-stage) |
| Stage conditions | No | Yes (skip stages based on variables) |
| Pricing | $1/active pipeline/month | $0.002/pipeline-execution |

**Pick V2 when ALL hold:** source supports event-driven triggers
(CodeCommit, S3 via EventBridge, GitHub via CodeConnections); you want
sub-second trigger latency (vs V1's ~17s polling); you want
pipeline-level variables or stage conditions; you want per-execution
pricing. Pick V1 only for legacy pipelines that cannot be migrated.
New pipelines should default to V2.

### Step 2: Source action

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

| Source | Provider | Connection | Trigger type |
|---|---|---|---|
| CodeCommit | `CodeCommit` | Native (no connection) | `referenceCreated` / `referenceUpdated` |
| S3 | `S3` | Native | `PutObject` via EventBridge |
| GitHub | `CodeStarSourceConnection` | CodeConnections (us-east-1) | `push` events |
| GitLab / Bitbucket | `CodeStarSourceConnection` | CodeConnections | `push` events |



The connection ARN MUST be created in us-east-1 via
`aws codeconnections create-connection`, even if the pipeline is in
another region. The connection requires a one-time browser handshake
to authorize AWS to access the GitHub repo.

### Step 3: Trigger configuration (event-driven filter)

V2 triggers replace V1's polling / CloudWatch Events rule. The filter
scopes which pushes start a run:

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).


**Critical trigger rules:**
- A trigger with NO filter fires on EVERY push to EVERY branch —
  always scope `Branches.Includes` to production branches.
- `Branches.Includes` supports glob (`release/*` matches
  `release/v1`). `main` is exact-match only.
- `FilePaths.Includes` limits runs to changes under those paths. Use
  `Excludes` for docs/CI-only changes.
- `Tags` filters on Git tags (annotated or lightweight). Useful for
  "deploy only on tagged releases."
- Multiple triggers are OR'd; within a trigger, branches/paths/tags
  are AND'd.

### Step 4: Build (CodeBuild)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).


The `Namespace: BuildVars` block exposes the build's exported
variables to downstream stages as `#{BuildVars.IMAGE_TAG}`. The
CodeBuild project must declare the variables it exports in
`buildspec.yml` under `exported-variables`:


### Step 5: Deploy actions

| Deploy type | Provider | Key configuration |
|---|---|---|
| CloudFormation | `CloudFormation` | `ActionMode: CREATE_REPLACE`, `StackName`, `RoleArn` (target), `TemplatePath` |
| ECS | `ECS` | `ClusterName`, `ServiceName`, `Image1` (direct image) or `TaskDefinitionTemplatePath` |
| S3 deploy | `S3` | `BucketName`, `Extract: true` (unzip artifact) |
| Service Catalog | `ServiceCatalog` | `ProductId`, `ProvisionedProductName` |
| CodeDeploy | `CodeDeploy` | `ApplicationName`, `DeploymentGroupName`, `DeploymentStyle: BLUE_GREEN` / `IN_PLACE` |
| Manual approval | `Manual` | `ExternalEntityLink` (optional), `CustomData` (reviewer context) |

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).


For cross-account, `RoleArn` points to a role in the TARGET account;
the pipeline role in the source account needs `sts:AssumeRole` on it.

**ECS deploy (direct image):** uses `Image1: #{BuildVars.IMAGE_URI}`
(a namespace variable from Build); the deploy cannot start until the
build's exported variable is resolved. Configure `ClusterName`,
`ServiceName`, `Image1`.

**CodeDeploy for EC2 (in-place or blue/green):** configure
`ApplicationName`, `DeploymentGroupName`, `DeploymentStyle`
(`IN_PLACE` or `BLUE_GREEN`). EC2 instances must have the CodeDeploy
agent and the CodeDeploy service role configured.

### Step 6: Manual approval gate

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).


The pipeline blocks until `put-job-approval-result --result APPROVED`
(or REJECTED). Configure an SNS topic to notify reviewers via
email/Slack. `ExternalEntityLink` points to a Change Management
ticket; `CustomData` is free-form reviewer context. Approval timeouts
are NOT enforced — the pipeline waits indefinitely. Use an external
scheduled Lambda to auto-reject stale approvals.

### Step 7: Namespace variables

Defined by setting `Namespace: <name>` on an action and exporting
variables from the action (CodeBuild's `exported-variables`,
CloudFormation's `OutputFileName`, or literal `Variables` block).

**Consumption patterns:**
- Downstream action configuration: `Image1: #{BuildVars.IMAGE_URI}`
- Stage condition: `Conditions: [{ConditionKey: "#{BuildVars.ENV}", ConditionValue: prod, Operator: StringEquals}]`
- Nested namespace: `#{BuildVars.Deeply.Nested.Key}` (dotted paths for JSON-exported values)

**Critical variable rules:**
- Variables flow forward only — a stage cannot consume a variable from
  a later stage.
- A missing variable renders as empty string (no error). Validate
  with a stage condition before using in a deploy.
- Variables are scoped per-execution. Concurrent pipeline runs do not
  share variable state.
- Secrets must NOT be namespace variables — they appear in plaintext
  in the pipeline execution history. Use Secrets Manager or Parameter
  Store SecureString, referenced by ARN in the action's IAM role.

### Step 8: Cross-account deployment

Moved verbatim to [references/cross-account-and-deploy-actions-reference.md](references/cross-account-and-deploy-actions-reference.md) - load on demand (see References below).


### Step 9: Artifact bucket security

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


### Step 10: Pipeline IAM role

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Expert heuristic: trigger filter precision and the "every push" trap

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Expert heuristic: namespace variables and the silent-empty-string failure

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Output format (per V2 pipeline deployment plan)

Every V2 deployment plan MUST emit a single block using these literal
labels, in this order. Do NOT substitute markdown headings or camelCase
variants — assertion-based evals and downstream provisioning parse the
literal labels `PIPELINE:`, `VERDICT:`, `CHECKLIST:`, `FINDINGS:`,
`DEPLOY_COMMANDS:`.

```text
PIPELINE: <pipeline-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [x] Pipeline type: V2 (event-driven, no polling; PollForSourceChanges=false)
  [x] Source: CodeCommit <repo/main> | S3 <bucket/key> | GitHub via CodeConnections <connection-arn + repo/branch>
  [x] Trigger filter: Branches=[main], FilePaths=src/**, Tags=deploy=prod (NOT unscoped)
  [x] Build: CodeBuild project <name>, exports namespace variables <list>
  [x] Test stage: CodeBuild <test-project> with unit + integration tests
  [x] Manual approval: enabled between <stage A> and <stage B> | none (ExternalEntityLink + SNS topic arn)
  [x] Deploy: CloudFormation <CREATE_REPLACE on stack> | ECS <cluster/service> | CodeDeploy <app/group> | S3 <bucket> | ServiceCatalog <product>
  [x] Artifacts: S3 <bucket-name> (block-public-access=true, SSE-KMS CMK <key-arn>, versioning=enabled)
  [x] Cross-account: target=<account>, KMS key policy grants kms:Decrypt+GenerateDataKey to <role>, IAM role <arn> | n/a
  [x] Pipeline IAM role: arn:aws:iam::<source>:role/<name> (no wildcard resources on S3/KMS/CodeBuild)
  [x] Namespace variables: validated non-empty via stage condition (no silent empty strings)
FINDINGS:
  - [INFO] <observation (pricing, propagation time, etc.)>
  - [WARN] <caution (trigger scoping, approval timeout, etc.)>
DEPLOY_COMMANDS:
  <ordered list of aws codepipeline / kms / iam / s3api commands>
```

### FORBIDDEN output patterns — NEVER

1. NEVER emit `VERDICT: READY_TO_DEPLOY` while any CHECKLIST item is
   `[ ]` (unchecked). Any unmet requirement forces
   `PREREQUISITES_MISSING`.

2. NEVER emit a V2 pipeline trigger without a filter (no `Branches`,
   `FilePaths`, or `Tags` criteria). An unscoped trigger fires on EVERY
   push to EVERY branch — flooding history, burning per-execution
   costs ($0.002 × N feature pushes/day), and risking unintended prod
   deploys from feature branches.

3. NEVER emit a cross-account deploy plan where the KMS key policy is
   missing `kms:Decrypt` and `kms:GenerateDataKey` grants to the target
   account's deployment role. S3 bucket policy alone does NOT grant
   cross-account access to encrypted objects — the deploy fails with
   "Access Denied" that looks like S3 but is actually KMS.

4. NEVER emit a pipeline IAM role with `"Resource": "*"` on `s3:GetObject`,
   `kms:*`, or `codebuild:*`. Wildcards create a privilege escalation
   path — a malicious CodeBuild project can exfiltrate other pipelines'
   artifacts. Scope every resource to the exact ARN.

5. NEVER emit secrets (tokens, passwords, signing keys) as namespace
   variables. Namespace variables render in plaintext in CloudTrail,
   the pipeline execution history, and the console. Use Secrets Manager
   or Parameter Store SecureString, referenced by ARN in the action's
   IAM role.

6. NEVER emit a V2 pipeline with `PollForSourceChanges: true`. V2
   rejects this with a confusing "Invalid action configuration" error.
   After V1→V2 migration, set `DetectOptions: false` and add a trigger
   block. Also delete the legacy CloudWatch Events rule — a leftover
   rule fires alongside the V2 trigger and produces duplicate executions.

7. NEVER emit a deployment plan that consumes a namespace variable
   (e.g., `#{BuildVars.IMAGE_URI}`) without a stage condition validating
   the variable is non-empty. A missing variable silently renders as
   `""` — ECS rejects the empty image string with a confusing
   "InvalidParameterException", not a clear "variable undefined" error.

### Worked example — READY_TO_DEPLOY (CI/CD with test stage + manual approval + prod CFN deploy)

```text
PIPELINE: payments-service-cicd
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [x] Pipeline type: V2 (event-driven; PollForSourceChanges: false — replaced legacy V1 CloudWatch Events rule)
  [x] Source: CodeCommit repo payments-service, branch main (OutputArtifacts: SourceOutput)
  [x] Trigger filter: Branches=[main], FilePaths.Includes=[src/**], FilePaths.Excludes=[docs/**, README.md] (NO unscoped trigger)
  [x] Build: CodeBuild project payments-service-build, exports IMAGE_URI, IMAGE_TAG, BUILD_VERSION
  [x] Test stage: CodeBuild project payments-service-tests (unit + integration, buildspec at tests/buildspec.yml) — gates Build stage via InputArtifact
  [x] Manual approval: enabled between Test and DeployProd (ExternalEntityLink: https://internal.example.com/change/CHG-78901, SNS topic arn:aws:sns:us-east-1:111111111111:prod-payments-approval)
  [x] Deploy: CloudFormation CREATE_REPLACE on stack prod-payments-service, RoleArn arn:aws:iam::222222222222:role/CrossAccountCFNExecution (target account 222222222222), TemplatePath BuildOutput::template.yaml, Capabilities CAPABILITY_IAM
  [x] Artifacts: S3 payments-pipeline-artifacts (block-public-access all true, SSE-KMS CMK arn:aws:kms:us-east-1:111111111111:key/abc-123, versioning enabled, lifecycle Glacier 90d)
  [x] Cross-account: target=222222222222, KMS key policy grants kms:Decrypt+GenerateDataKey to arn:aws:iam::222222222222:role/CrossAccountCFNExecution, IAM role trust allows arn:aws:iam::111111111111:role/payments-pipeline-role
  [x] Pipeline IAM role: arn:aws:iam::111111111111:role/payments-pipeline-role (scoped to exact ARNs — no wildcards on S3/KMS/CodeBuild/CodeCommit; iam:PassRole scoped to CrossAccountCFNExecution)
  [x] Namespace variables: validated via stage condition on DeployProd — `Conditions: [{ConditionKey: "#{BuildVars.IMAGE_URI}", Operator: StringEquals, ConditionValue: "", Not: true}]` (empty IMAGE_URI blocks deploy)
FINDINGS:
  - [INFO] Pricing: $0.002/execution + $1/active pipeline/month + $0.01/build-minute for CodeBuild
  - [WARN] Manual approval has no enforced timeout — wire an external scheduled Lambda to auto-reject approvals older than 48 hours
  - [WARN] After V1→V2 migration, delete the legacy CloudWatch Events rule payments-cicd-legacy-trigger to prevent duplicate executions
DEPLOY_COMMANDS:
  # 1. Create KMS CMK with cross-account key policy (source account 111111111111)
  aws kms create-key --policy file://kms-key-policy.json --description "payments-pipeline-artifacts CMK"

  # 2. Create artifact bucket with block-public-access + KMS + versioning
  aws s3api create-bucket --bucket payments-pipeline-artifacts --region us-east-1 \
    --block-public-access BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket payments-pipeline-artifacts \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"arn:aws:kms:us-east-1:111111111111:key/abc-123"}}]}'
  aws s3api put-bucket-versioning --bucket payments-pipeline-artifacts --versioning-configuration Status=Enabled

  # 3. Create cross-account CFN execution role in TARGET account 222222222222
  aws iam create-role --role-name CrossAccountCFNExecution --assume-role-policy-document file://trust-policy.json

  # 4. Create the pipeline role in SOURCE account 111111111111
  aws iam create-role --role-name payments-pipeline-role --assume-role-policy-document file://pipeline-trust-policy.json
  aws iam put-role-policy --role-name payments-pipeline-role --policy-name scoped --policy-document file://pipeline-role-policy.json

  # 5. Create the V2 pipeline (trigger filter scoped to main + src/**)
  aws codepipeline create-pipeline --cli-input-json file://payments-service-cicd.json

  # 6. Verify
  aws codepipeline get-pipeline-state --name payments-service-cicd
```

### Decision tree — V2 pipeline shape selection

```
Start: V2 deployment requirement
├─ Source = CodeCommit / GitHub via CodeConnections / S3 (event-driven capable)?
│   └─ No (legacy V1-only source) → emit ERROR — V2 requires event-driven source
├─ Cross-account deploy target?
│   ├─ Yes → KMS key policy grants kms:Decrypt + GenerateDataKey to target role?
│   │       ├─ Yes → CFN deploy action with RoleArn in target account
│   │       └─ No  → PREREQUISITES_MISSING (KMS key policy is the actual blocker, not S3)
│   └─ No  → same-account CFN / ECS / CodeDeploy / S3 / ServiceCatalog
├─ Gated release required?
│   ├─ Yes → Insert Manual approval action between Test and Deploy stages
│   │       (wire SNS topic for reviewer notification; schedule external Lambda
│        for stale-approval auto-reject — CodePipeline does NOT enforce timeouts)
│   └─ No  → Continuous deploy (Test → Deploy direct)
├─ Trigger scope:
│   ├─ Filter present (Branches + FilePaths + Tags)? → READY_TO_DEPLOY
│   └─ No filter → PREREQUISITES_MISSING (unscoped trigger = every push to every branch)
└─ Namespace variables consumed downstream?
    ├─ Stage condition validates non-empty? → READY_TO_DEPLOY
    └─ No validation → PREREQUISITES_MISSING (silent empty-string deploy risk)
```

## Verification commands (run after deployment)

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).


## Edge-case handling

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## NEVER do these things

1. **NEVER create a V2 pipeline trigger without a filter.** A trigger
   with no `Branches` / `FilePaths` / `Tags` filter fires on EVERY
   push to EVERY branch, flooding history, burning per-execution
   costs, and risking unintended production deploys from feature
   branches. Always scope `Branches.Includes` to production branches.

2. **NEVER share the artifact bucket without KMS cross-account
   policy.** S3 bucket policy alone does NOT grant cross-account
   access to encrypted objects. Without the matching KMS key policy
   granting the target role `kms:Decrypt` and `kms:GenerateDataKey`,
   the deploy action fails with "Access Denied" that looks like S3
   but is actually KMS. Configure both.

3. **NEVER pass secrets as namespace variables.** Namespace variables
   render in plaintext in CloudTrail, the pipeline execution history,
   and the console. Use Secrets Manager or Parameter Store
   SecureString, referenced by ARN in the action's IAM role.

4. **NEVER use a wildcard in the pipeline IAM role for S3, KMS, or
   CodeBuild.** `"Resource": "*"` on `s3:GetObject` lets the pipeline
   read any bucket. `"Resource": "*"` on `codebuild:*` lets it start
   any CodeBuild project — a malicious project can exfiltrate other
   pipelines' artifacts. Scope to exact ARNs.

5. **NEVER leave `PollForSourceChanges: true` on a V2 pipeline.** V2
   rejects this with a confusing error. After V1 → V2 migration, set
   `DetectOptions: false` and add a trigger. Also delete the legacy
   CloudWatch Events rule from V1 — a leftover rule fires alongside
   the V2 trigger and produces duplicate executions.

Additional hard constraints: approval timeouts are NOT enforced
(CodePipeline waits indefinitely); a missing namespace variable
silently renders as empty string; S3-managed encryption (SSE-S3) is
incompatible with cross-account (requires customer-managed KMS CMK);
`iam:PassRole` on `*` is a privilege escalation path.

## Pre-flight safety checks (run before any deployment CLI)

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).


## Remediation guidance

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) - Step 0 + expert-heuristic deep dives, edge-case catalog, Step 9/10 hardening, recent AWS features
- [references/worked-examples.md](references/worked-examples.md) - per-step source / trigger / build / deploy / approval config examples
- [references/diagnostic-commands.md](references/diagnostic-commands.md) - verification commands + pre-flight safety checks
- [references/error-handling.md](references/error-handling.md) - remediation ordering + fixes
- [references/cross-account-and-deploy-actions-reference.md](references/cross-account-and-deploy-actions-reference.md) - cross-account KMS/IAM wiring deep dive
- [references/triggers-and-namespace-variables-reference.md](references/triggers-and-namespace-variables-reference.md) - trigger filter + namespace variable detail

## Domain

AWS CloudOps / CodePipeline V2 Provisioning.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## AWS documentation

- **CodePipeline User Guide + Pipeline types (V1 vs V2)** — https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html
- **V2 triggers / Namespace variables / Cross-account actions** — https://docs.aws.amazon.com/codepipeline/latest/userguide/triggers-v2.html
- **CodeConnections** — https://docs.aws.amazon.com/codeconnections/latest/userguide/welcome.html
- **CodePipeline CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/codepipeline/
- **Tutorial: V2 pipeline with manual approval** — https://docs.aws.amazon.com/codepipeline/latest/userguide/tutorials-simple-deploy.html
- **Blog: V2 pipeline launch** — https://aws.amazon.com/blogs/devops/introducing-aws-codepipeline-v2/
