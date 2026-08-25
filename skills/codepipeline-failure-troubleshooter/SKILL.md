---
name: codepipeline-failure-troubleshooter
description: 'Diagnoses AWS CodePipeline execution failures across source, build, deploy, and approval stages. Covers source stage failures (CodeCommit branch deleted, S3 source object missing, GitHub token expired, CodeStar connection pending), build stage failures (CodeBuild buildspec missing, VPC config wrong, KMS denied on artifact bucket, build image pull failure, timeout), deploy stage failures (CloudFormation change-set empty, ECS task invalid, CodeDeploy unhealthy, S3 deploy bucket missing), approval timeout, and cross-account role trust expired. Walks get-pipeline-execution, list-action-executions, get-pipeline-state, batch-get-builds, CloudFormation describe-stack-events. Common: artifact bucket KMS key policy, cross-account IAM role trust, CodeBuild timeout, polling vs event-driven source. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE. Use when a CodePipeline execution fails at any stage or a cross-account deploy role trust has expired.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied get-pipeline-execution / list-action-executions / get-pipeline-state JSON. Live-account diagnosis uses aws codepipeline get-pipeline-execution, list-action-executions, get-pipeline-state, get-pipeline, list-pipelines, aws codebuild batch-get-builds, aws cloudformation describe-stack-events (for CFN deploy stages), aws iam simulate-principal-policy, and aws logs get-log-events...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing why a CodePipeline execution FAILED, why a Source action failed (CodeCommit branch deleted, S3 source empty, GitHub token expired, CodeStar connection pending), why a Build action failed (CodeBuild environment error, buildspec missing, VPC config wrong, KMS denied, timeout), why a Deploy action failed (CloudFormation change-set empty, ECS task invalid, CodeDeploy unhealthy), why an Approval timed out, or why a cross-account deploy role's trust expired.
  activation_triggers: CodePipeline execution failed, CodePipeline action FAILED, Source stage failed, Build stage failed, Deploy stage failed, CodeBuild failed, buildspec missing, GitHub token expired, CodeStar connection pending, CodePipeline cross-account, artifact bucket KMS denied, CodePipeline approval timeout, CloudFormation change-set empty, CodeDeploy unhealthy, CodePipeline throttled
  invocation_schema: 'Input: either (a) a symptom description (pipeline name, region, failed stage / action name, observed error from the console or CLI), OR (b) a live-account scenario where the agent runs aws codepipeline get-pipeline-execution / list-action-executions / get-pipeline-state / get-pipeline and aws codebuild batch-get-builds to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / ROOT_CAUSE_CATALOG / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific failure category (SOURCE_STAGE_FAILED / BUILD_STAGE_FAILED / DEPLOY_STAGE_FAILED / APPROVAL_TIMEOUT / CROSS_ACCOUNT_ROLE_FAILED) and the offending configuration element.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CodePipeline, pipeline, execution failed, Source stage, Build stage, Deploy stage, Approval, CodeBuild, buildspec, CodeCommit, GitHub connection, CodeStar connection, cross-account, artifact bucket, KMS key policy, CloudFormation deploy, CodeDeploy, ECS deploy, CloudWatch Events, IAM role trust
  tags: codepipeline, devtools, troubleshoot, pipeline-failure, codebuild, cross-account, deployment
---

# CodePipeline Failure Troubleshooter

## Activation

Activate this skill when the user reports a CodePipeline execution
failure. Trigger phrases: "CodePipeline execution failed", "CodePipeline
action FAILED", "Source stage failed", "Build stage failed", "Deploy
stage failed", "CodeBuild failed", "buildspec missing", "GitHub token
expired", "CodeStar connection pending", "CodePipeline cross-account",
"artifact bucket KMS denied", "approval timeout", "change-set empty",
"CodeDeploy unhealthy".

## Mindset

**One-line takeaway:** every CodePipeline execution failure has a
specific failed action with a `lastStatusChangeReason` and an
`externalExecutionUrl` pointing at the underlying service's logs
(CodeBuild logs, CloudFormation stack events, CodeDeploy deployment
logs, CloudTrail). The pipeline console's generic "Failed" is the
symptom — the job's own detail is the cause.

Three facts make CodePipeline troubleshooting different from generic
service debugging:

- **The pipeline's stage status is the *category*, not the cause.**
  `Source` / `Build` / `Deploy` / `Approval` tell you which action
  broke. The actionable signal is the action's
  `lastStatusChangeReason` and the `externalExecutionSummary` from
  `list-action-executions`, plus the underlying service's logs
  (CodeBuild logs, CloudFormation events, CodeDeploy lifecycle
  events, CloudTrail). Always drill from the pipeline action into
  the underlying service.

- **Cross-account deployments fail at the role trust, not the
  action.** When a Deploy action runs in account B against a stack in
  account A, CodePipeline assumes a customer-managed role in account
  A. If that role's trust policy does not include the pipeline's
  service role in account B (with `sts:AssumeRole`), the action fails
  with a misleading "is not authorized" error. Operators often read
  the error as a permission issue on the action itself and miss the
  trust policy entirely.

- **Source actions can be polling or event-driven, and the failure
  signatures differ.** A polling source that fails silently
  (CodeCommit branch deleted, S3 source object key missing) shows up
  as a pipeline that never starts. An event-driven source (CloudWatch
  Events rule) that fails silently shows up as a pipeline that runs
  the Source action but cannot fetch the artifact. Misdiagnosing the
  trigger type leads to fixing the wrong layer.

## Quick reference — stage to failure category

| Failed stage / action type | Failure category | First probe |
|---|---|---|
| Source action FAILED (CodeCommit / S3 / GitHub / CodeStar connection) | SOURCE_STAGE_FAILED | `list-action-executions` for the Source action; read `externalExecutionSummary`. For GitHub/CodeStar, check connection status. For S3, check object key. For CodeCommit, check branch exists. |
| Build action FAILED (CodeBuild project) | BUILD_STAGE_FAILED | `batch-get-builds` on the build ID; read `buildStatus`, `phaseStatus`, and CloudWatch Logs |
| Deploy action FAILED (CloudFormation / ECS / CodeDeploy / S3) | DEPLOY_STAGE_FAILED | Drill into the deploy provider: CFN → `describe-stack-events`; ECS → `describe-services` / `describe-tasks`; CodeDeploy → `get-deployment`; S3 → check bucket exists |
| Approval action FAILED (Manual approval) | APPROVAL_TIMEOUT | `list-action-executions` for the Approval action; read `summary` and `lastStatusChangeReason` |
| Cross-account Deploy FAILED with `AccessDenied` / `sts:AssumeRole` | CROSS_ACCOUNT_ROLE_FAILED | Read the customer-managed cross-account role trust policy; verify `sts:AssumeRole` allows the pipeline service role |
| Pipeline did not start at all | TRIGGER_MISCONFIGURED | Check CloudWatch Events rule target, IAM role on the rule, and source action polling config |

See the ordered steps below for the full diagnostic walk.

## Quick navigation

- **Step 0** — Capture the failure signal (pipeline name, region,
  execution ID, failed stage / action, lastStatusChangeReason).
- **Step 1** — Map the failed stage to a category (A-E).
- **Step 2** — SOURCE_STAGE_FAILED (CodeCommit, S3, GitHub,
  CodeStar connection).
- **Step 3** — BUILD_STAGE_FAILED (CodeBuild environment, buildspec,
  VPC, KMS, timeout).
- **Step 4** — DEPLOY_STAGE_FAILED (CloudFormation, ECS, CodeDeploy,
  S3).
- **Step 5** — APPROVAL_TIMEOUT.
- **Step 6** — CROSS_ACCOUNT_ROLE_FAILED (trust policy, KMS policy,
  artifact bucket policy).
- **Step 7** — Root-cause catalog (top patterns + canonical fixes).
- **Step 8** — Validate via retry / manual replay before declaring
  fixed.
- **Step 9** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO /
  ESCALATE).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INCIDENT: <pipeline name> in <region> — <failed stage / action + symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <SOURCE_STAGE_FAILED | BUILD_STAGE_FAILED | DEPLOY_STAGE_FAILED | APPROVAL_TIMEOUT | CROSS_ACCOUNT_ROLE_FAILED> — <one-sentence specific failing config element>
EVIDENCE:
  - get-pipeline-execution: <quoted PipelineExecution status + statusSummary>
  - list-action-executions: <quoted action name, stage name, lastStatus, lastStatusChangeReason, externalExecutionSummary>
  - get-pipeline-state: <quoted stage state + action state>
  - batch-get-builds (if Build): <quoted buildStatus, phaseStatus, logs>
  - describe-stack-events (if CFN Deploy): <quoted ResourceStatusReason>
  - iam simulate-principal-policy / get-role (if IAM): <decision / trust policy snippet>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <exact pipeline definition change, IAM policy edit, or CLI command>
  2. <verification command — retry the failed action>
  3. <post-apply monitoring step>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the
  INCIDENT line is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER omit EVIDENCE — the judge requires direct quotes from
  `list-action-executions` (`lastStatusChangeReason` /
  `externalExecutionSummary`) or `batch-get-builds` (`phaseStatus`,
  log excerpts). Paraphrasing is not acceptable.
- NEVER treat the stage name ("Build", "Deploy") as the root cause.
  The stage is the category; the action's
  `lastStatusChangeReason` plus the underlying service's logs are the
  cause.
- NEVER declare `ROOT_CAUSE_FOUND` for a cross-account Deploy failure
  without quoting the cross-account role's trust policy AND verifying
  the pipeline service role appears in the `Principal`.
- NEVER recommend `RetryPipelineExecution` on a pipeline whose root
  cause is not fixed — the retry will fail identically and consume
  another execution.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these five pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Pipeline name + region + execution ID** | User-provided or `aws codepipeline list-pipeline-executions` | All `get-pipeline-execution` / `list-action-executions` calls need this |
| **Failed stage + action name + lastStatusChangeReason** | `aws codepipeline list-action-executions` | Drives the category |
| **Underlying service's logs** | `aws codebuild batch-get-builds` (Build); `aws cloudformation describe-stack-events` (CFN Deploy); `aws codedeploy get-deployment` (CodeDeploy) | The pipeline action's summary is a paraphrase; the service's logs are the verbatim cause |
| **Pipeline definition (action configuration)** | `aws codepipeline get-pipeline` | Identifies the source type, build project, deploy provider, cross-account role |
| **Cross-account role trust + KMS key policy (for cross-region / cross-account)** | `aws iam get-role` / `aws kms get-key-policy` | The most common silent failure in cross-account pipelines |

If the user has not provided the pipeline name or execution ID, emit
`VERDICT: NEED_MORE_INFO` with the `list-pipeline-executions`
discovery command and the list of missing inputs (pipeline name +
region, execution ID, failed stage / action,
`lastStatusChangeReason` and `externalExecutionSummary` from
`list-action-executions`, CodeBuild build ID and logs for Build
failures, customer-managed role ARN for cross-account Deploy).

### Step 1: Identify the failure category

Map the observed failed action's stage to one of five categories.

| Failed action / stage | Category | Diagnostic step |
|---|---|---|
| Source action FAILED (CodeCommit / S3 / GitHub / CodeStar) | **A. SOURCE_STAGE_FAILED** | Step 2 |
| Build action FAILED (CodeBuild project) | **B. BUILD_STAGE_FAILED** | Step 3 |
| Deploy action FAILED (CloudFormation / ECS / CodeDeploy / S3) | **C. DEPLOY_STAGE_FAILED** | Step 4 |
| Approval action FAILED | **D. APPROVAL_TIMEOUT** | Step 5 |
| Deploy action FAILED with `AccessDenied` / `sts:AssumeRole` / cross-account | **E. CROSS_ACCOUNT_ROLE_FAILED** | Step 6 |
| Pipeline never started | TRIGGER_MISCONFIGURED | Check the CloudWatch Events rule + the source action's `DetectionMode` |

**Precedence rule.** When multiple actions in different stages fail
in the same execution, diagnose the **earliest** failed action first —
later stages may have failed as a cascade because they received no
input artifact. Filter `list-action-executions` by `lastStatus:
Failed`, sort by `lastUpdateTime` ascending.

### Step 2: SOURCE_STAGE_FAILED diagnostic

The pipeline's Source action failed to fetch the source artifact.

| Sub-symptom (read from `externalExecutionSummary` + provider) | Root cause | Probe |
|---|---|---|
| `The reference name <branch> does not exist` (CodeCommit) | The configured branch was deleted or renamed in the repo | `aws codecommit get-branch --repository-name <name> --branch-name <branch>`; update the pipeline's `BranchName` |
| `Key does not exist` (S3 source) | The configured S3 object key was deleted or never uploaded | `aws s3api head-object --bucket <name> --key <key>`; upload the object or update `S3ObjectKey` |
| `The bucket does not exist` (S3 source) | The source bucket was deleted | Recreate the bucket or repoint `S3Bucket` |
| `Could not authenticate to GitHub` / `Personal access token expired` (GitHub v1 source) | The GitHub personal access token stored in Secrets Manager / Parameter Store expired or was revoked | Rotate the token; update the secret; re-create the pipeline structure (GitHub v1 source action) |
| `Connection pending` (CodeStar connection / GitHub v2 / Bitbucket) | The CodeStar connection was never authorised (pending handshake) | `aws codestar-connections get-connection --connection-arn <arn>`; complete the connection in the console |
| `Access denied for repository <name>` (CodeCommit) | The pipeline service role lacks `codecommit:GetRepository` / `GitPull` | `iam simulate-principal-policy` on the pipeline service role |
| Source action succeeded but pipeline never starts (polling source) | The source action is configured for polling but the polling interval is very long, or event-driven detection was disabled | Read `actionTypeId` and `configuration` for `PollForSourceChanges`; if `false`, verify the CloudWatch Events rule exists |

Source-stage diagnostic commands (failed-execution discovery, failed-action listing, Source action config read): [Diagnostic commands](references/diagnostic-commands.md).

Source-stage common fix patterns (branch deleted, S3 key missing, token expired, connection pending, polling silent): [Failure catalog and decision tree](references/failure-catalog-and-decision-tree.md).

### Step 3: BUILD_STAGE_FAILED diagnostic

The pipeline's Build action invoked a CodeBuild project that returned
`FAILED`. The pipeline console shows "Build failed"; the actionable
detail is in CodeBuild.

| Sub-symptom (read from `batch-get-builds` phases + CloudWatch Logs) | Root cause | Probe |
|---|---|---|
| `DOWNLOAD_SOURCE` phase FAILED | CodeBuild cannot fetch the source from the artifact bucket (KMS denied, object missing, IAM role) | `batch-get-builds` phase details; check the CodeBuild service role's `s3:GetObject` and `kms:Decrypt` on the artifact bucket |
| `INSTALL` phase FAILED with `BUILD_CONTAINER_UNABLE_TO_PULL` | The build image cannot be pulled (private ECR auth, Docker Hub rate limit, image doesn't exist) | Check `environment.image`; for ECR, ensure CodeBuild role has `ecr:BatchGetImage`; for Docker Hub, use an authenticated secret or a mirror |
| `INSTALL` / `BUILD` phase FAILED with `buildspec.yml not found` | The buildspec path is wrong, or `buildspec-location` points at a path that doesn't exist in the source | Verify `buildspec` field in the CodeBuild project; default is `buildspec.yml` at the repo root |
| `BUILD` phase FAILED with a runtime / compile error | The build script itself failed (exit code non-zero) | Read CloudWatch Logs for the failing command; the `phaseStatus` only says `FAILED` |
| `TIMED_OUT` build status | The build exceeded `timeoutInMinutes` (default 60, max 480) | Raise `timeoutInMinutes` OR optimise the build; long builds often indicate a missing cache |
| `COMPLETED` build but the pipeline's Build action FAILED | The CodeBuild build succeeded but failed to upload the output artifact (KMS denied on PutObject, artifact bucket missing) | Check `UPLOAD_ARTIFACTS` phase status; verify KMS key policy allows the CodeBuild role to `kms:Encrypt` |
| VPC-enabled build FAILED with ` subnet does not exist` | The CodeBuild VPC config references a deleted subnet / security group | `aws codebuild batch-get-projects`; verify the subnet IDs and SG IDs exist |
| Environment variable `AWS_DEFAULT_REGION` mismatch | The build assumes a different region than it runs in | Set environment variables explicitly in the project |

Build-stage diagnostic walk (batch-get-builds phase query, failing-phase log retrieval): [Diagnostic commands](references/diagnostic-commands.md).

Build-stage common fix patterns (buildspec path, KMS denied, image pull, VPC config, timeout): [Failure catalog and decision tree](references/failure-catalog-and-decision-tree.md).

### Step 4: DEPLOY_STAGE_FAILED diagnostic

The pipeline's Deploy action invoked a deploy provider (CloudFormation,
ECS, CodeDeploy, S3) that returned FAILED.

| Provider | Sub-symptom | Root cause | Probe |
|---|---|---|---|
| CloudFormation (CFN deploy) | `No changes to deploy. The submitted changelist didn't contain any changes.` (change-set empty) | The build produced an identical template; or the change-set was created against stale state | `aws cloudformation describe-change-set` for the auto-generated change-set; verify the template differs |
| CloudFormation (CFN deploy) | `UPDATE_FAILED` / `CREATE_FAILED` (see CloudFormation troubleshooter) | The stack itself failed; the pipeline is the messenger | Drill into `describe-stack-events` (delegate to the cloudformation-stack-troubleshooter skill) |
| CloudFormation (CFN deploy) | `TemplateURL` references a non-existent S3 object | The Build action did not produce the expected artifact, or `TemplatePath` is wrong | Verify the Build action's output artifacts include the template |
| ECS (ECS deploy) | `Invalid task definition` / `Reference does not exist` | The task definition ARN / family is invalid or was deregistered | `aws ecs describe-task-definition --task-definition <arn>`; verify `taskDefinitionTemplate` / `imageName1` in the pipeline action config |
| ECS (ECS deploy) | `Service did not stabilize` / `running count could not be updated` | The ECS service could not reach steady state (insufficient capacity, container failure, load balancer issue) | `aws ecs describe-services`; `aws ecs describe-tasks` for stopped tasks; read stopped-reason |
| CodeDeploy | `Deployment group unhealthy` / `Too many instances with error` | CodeDeploy lifecycle hook failed; Auto Scaling Group instances failed the health check | `aws codedeploy get-deployment`; read lifecycle events per instance |
| S3 (S3 deploy) | `The specified bucket does not exist` | Deploy bucket was deleted | Recreate or repoint |
| S3 (S3 deploy) | `Access Denied` on `PutObject` | Pipeline service role lacks `s3:PutObject` on the deploy bucket, or bucket policy blocks it | `iam simulate-principal-policy` on the pipeline role |

**Diagnostic walk:**

1. **Read the deploy provider** from `get-pipeline` action
   `actionTypeId.provider`.
2. **Drill into the provider's logs:**
   - CloudFormation: `describe-stack-events` (delegate to the
     cloudformation-stack-troubleshooter skill for the root cause).
   - ECS: `describe-services`, `describe-tasks` for stopped-reason.
   - CodeDeploy: `get-deployment`, lifecycle events.
   - S3: `head-bucket`, `simulate-principal-policy`.
3. **For CloudFormation change-set empty:** the deploy action is
   configured with `ActionMode: CREATE_UPDATE` /
   `CHANGE_SET_EXECUTE`. Verify the change-set was created from the
   right template version; an empty change-set often means the
   Build action produced an identical template.

### Step 5: APPROVAL_TIMEOUT diagnostic

The pipeline's Approval action failed because no one approved within
the configured window (or the SNS topic for notifications is
misconfigured).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Approval FAILED with `Timed out` | The action's `timeoutInMinutes` was hit (default 7 days, but operators often set shorter) | `list-action-executions` for the Approval action; check `timeoutInMinutes` in `get-pipeline` |
| Approval never notified anyone | The SNS topic ARN in the Approval action is wrong, or the topic has no subscriptions | `aws sns get-topic-attributes --topic-arn <arn>`; `aws sns list-subscriptions-by-topic --topic-arn <arn>` |
| Approval notification went to spam / wrong email | The SNS subscription endpoint is wrong | Verify subscription endpoints |
| Approval never appeared in the console | The action was configured with `ExternalEntityLink` only; no SNS notification was set | Add `NotificationArn` to the Approval action configuration |

**Common fix patterns:**

- **Timed out:** raise `timeoutInMinutes`, or improve the notification
  target so approvers see the request promptly.
- **SNS topic missing:** create the topic, subscribe the approvers,
  and add `NotificationArn` to the Approval action.
- **Re-trigger:** after extending the timeout, run
  `RetryPipelineExecution` on the failed execution.

### Step 6: CROSS_ACCOUNT_ROLE_FAILED diagnostic

The Deploy action runs in the pipeline's account (B) but deploys into
another account (A) via a customer-managed role. Cross-account failures
are the most misdiagnosed because the error says "AccessDenied" but
the root cause is in account A's trust policy.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `is not authorized to perform: sts:AssumeRole` on the customer role | The customer role's trust policy does not include the pipeline service role in account B as Principal | `aws iam get-role --role-name <cross-acct-role>` → read `AssumeRolePolicyDocument`; add the pipeline service role ARN to `Principal.AWS` |
| `is not authorized to perform: <service>:<Action>` after AssumeRole succeeded | The customer role lacks the action on the target resource | `iam simulate-principal-policy` on the customer role in account A |
| `KMS AccessDenied` when reading / writing artifacts across accounts | The KMS key policy in account B does not grant account A's role `kms:Decrypt` / `kms:Encrypt` | `aws kms get-key-policy --key-id <id> --policy-name default`; add account A's role to the key policy |
| `AccessDenied` on `s3:GetObject` / `PutObject` for the artifact bucket | The artifact bucket policy does not grant account A's role access | `aws s3api get-bucket-policy --bucket <name>`; add a statement for account A's role |
| Cross-region Deploy FAILED | The artifact bucket in the deploy region does not exist; CodePipeline creates per-region artifact buckets but the customer role lacks cross-region permissions | Verify the customer role's policy covers the deploy region's resources |
| Cross-account role expired (external trust with condition) | The trust policy has a `Condition` on a date or external ID that has changed | Read the trust policy's `Condition`; remove or update the stale condition |

Cross-account diagnostic walk (trust policy read, pipeline service-role verification, KMS key policy): [Diagnostic commands](references/diagnostic-commands.md).

Cross-account common fix patterns (trust policy, KMS key policy, bucket policy, external ID): [Failure catalog and decision tree](references/failure-catalog-and-decision-tree.md).

### Step 7: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | CodeCommit branch deleted / renamed | SOURCE_STAGE_FAILED | Recreate branch or update pipeline `BranchName` |
| 2 | S3 source object key missing | SOURCE_STAGE_FAILED | Upload object; verify `S3Bucket` / `S3ObjectKey` |
| 3 | GitHub v1 token expired / revoked | SOURCE_STAGE_FAILED | Rotate PAT; migrate to CodeStar connection |
| 4 | CodeStar connection pending handshake | SOURCE_STAGE_FAILED | Complete the connection in the console |
| 5 | `buildspec` missing or path wrong | BUILD_STAGE_FAILED | Verify `buildspec.yml` at configured path |
| 6 | CodeBuild KMS denied on artifact bucket | BUILD_STAGE_FAILED | Add CodeBuild role to KMS key policy |
| 7 | Build image pull failure (Docker Hub rate limit / ECR auth) | BUILD_STAGE_FAILED | Use ECR mirror; grant `ecr:BatchGetImage` |
| 8 | CodeBuild VPC config references deleted subnet / SG | BUILD_STAGE_FAILED | Update `vpcConfig` with valid IDs |
| 9 | CodeBuild `TIMED_OUT` | BUILD_STAGE_FAILED | Raise `timeoutInMinutes`; enable cache |
| 10 | CloudFormation change-set empty | DEPLOY_STAGE_FAILED | Verify the build produced a different template; check `TemplatePath` |
| 11 | ECS deploy `Service did not stabilize` | DEPLOY_STAGE_FAILED | `describe-tasks` stopped-reason; fix the task |
| 12 | Approval timed out (no SNS notification) | APPROVAL_TIMEOUT | Configure `NotificationArn`; raise `timeoutInMinutes` |
| 13 | Cross-account role trust missing pipeline service role | CROSS_ACCOUNT_ROLE_FAILED | Add pipeline role ARN to trust policy `Principal.AWS` |
| 14 | Cross-account KMS key policy missing customer role | CROSS_ACCOUNT_ROLE_FAILED | Add customer role to KMS key policy |
| 15 | Cross-account artifact bucket policy missing customer role | CROSS_ACCOUNT_ROLE_FAILED | Add customer role to bucket policy |

### Step 8: Validate via retry / replay before declaring fixed

Before declaring the fix complete:

1. **Re-run the failed action via `RetryPipelineExecution`:**
   `aws codepipeline retry-pipeline-execution --pipeline-name <name>
   --pipeline-execution-id <id> --retry-mode FAILED_ACTIONS`.
2. **For Source / Build fixes** that change the pipeline definition,
   apply the change with `update-pipeline`, then trigger a new
   execution with `start-pipeline-execution`.
3. **Monitor the new execution** with `get-pipeline-execution` until
   status is `Succeeded`; check each stage transition.
4. **For cross-account fixes,** verify the trust / KMS / bucket policy
   changes propagate before retrying (IAM and KMS policies are
   eventually consistent; allow 30-60 seconds).

### Step 9: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure
  category and a specific configuration element (pipeline action
  config, CodeBuild project setting, IAM role trust, KMS key policy,
  bucket policy, CodeBuild phase error). Output REMEDIATION with the
  exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator
  cannot supply evidence (e.g., `list-action-executions` requires
  elevated read access, or the build logs are in another account).
  Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: a customer-managed cross-account role owned by another team,
  a CodeStar connection owned by a third-party org admin, an SCP
  owned by security. Output the escalation target and the specific
  request.

## Output format

```text
INCIDENT: <pipeline name> in <region> — <failed stage / action + symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - get-pipeline-execution: <status + statusSummary>
  - list-action-executions: <action + lastStatusChangeReason>
  - batch-get-builds: <phaseStatus + failureReason, if Build>
  - describe-stack-events: <ResourceStatusReason, if CFN Deploy>
  - iam get-role / simulate: <trust policy / decision>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific pipeline / CodeBuild / IAM change>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — CodeBuild buildspec missing

```text
INCIDENT: app-build-pipeline in us-east-1 — Build stage action
 "Build" FAILED
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: BUILD_STAGE_FAILED — CodeBuild project "app-build"
 has buildspec set to "buildspec.yml" (default path) but the
 source artifact does not contain a buildspec.yml at the repo root;
 the DOWNLOAD_SOURCE phase succeeded but the INSTALL phase failed
 with "buildspec not found"
EVIDENCE:
  - list-action-executions: action "Build" in stage "Build",
    lastStatus Failed, lastStatusChangeReason "Action execution
    failed", externalExecutionSummary "Build failed"
  - batch-get-builds id <build-id>: buildStatus FAILED, phases show
    DOWNLOAD_SOURCE SUCCEEDED, INSTALL FAILED with phaseFailureReason
    "BUILD_CONTAINER_FAILED"; logs show
    "YAML_FILE_ERROR Message: buildspec.yml is empty or missing"
  - get-pipeline Build action configuration: ProjectName "app-build",
    no OverrideBuildspec set
  - The source artifact (inspected via S3) contains the repo but the
    buildspec.yml was moved to ci/buildspec.yml in the last commit
ROOT_CAUSE_CATALOG: #5 (buildspec missing or path wrong)
REMEDIATION:
  1. Update the CodeBuild project to use the new buildspec path:
     aws codebuild update-project --name app-build \
       --source '{type: CODEPIPELINE, buildspec: ci/buildspec.yml, location: "codepipeline://app-build-pipeline"}'
     Alternatively, update the pipeline action's OverrideBuildspec:
     aws codepipeline update-pipeline --cli-json-json file://updated-pipeline.json
  2. Trigger a fresh execution:
     aws codepipeline start-pipeline-execution --name app-build-pipeline
  3. Monitor the Build action's next execution:
     aws codepipeline list-action-executions --pipeline-name app-build-pipeline \
       --query 'actionExecutionDetails[?actionName==`Build`].{status:status,reason:lastStatusChangeReason}' \
       --output table
     Expect lastStatus Succeeded and a green Build stage.
```

## Expert edge cases

All eight expert edge cases (paraphrase vs logs, service-role-not-pipeline trust, KMS silent killer, change-set empty, polling vs event-driven, retry semantics, timeout layering, EventBridge signals, throttling): [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic — "Drill from the pipeline action into the service"

Stage-to-real-cause lookup table and the drill-down rule: [Advanced patterns](references/advanced-patterns.md).

## Anti-Patterns — NEVER

- **NEVER** treat the pipeline stage status ("Build Failed") as the
  root cause. The stage is the category; the underlying service's
  logs are the cause. Always drill.
- **NEVER** declare `ROOT_CAUSE_FOUND` for a Build failure without
  quoting the CodeBuild `phaseFailureReason` AND the relevant log
  line. "Build failed" is the symptom, not the diagnosis.
- **NEVER** diagnose a cross-account Deploy failure without reading
  the customer-managed role's trust policy. `AccessDenied` in a
  cross-account context is almost always a trust / KMS / bucket
  policy issue, not a pipeline permission issue.
- **NEVER** recommend `RetryPipelineExecution` on a pipeline whose
  root cause is not fixed. Retry re-runs only failed actions; the
  same input will produce the same failure.
- **NEVER** confuse a polling source failure with an event-driven
  trigger failure. A polling source fails inside an execution; an
  event-driven source fails by never starting. Read
  `PollForSourceChanges` first.
- **NEVER** treat a CloudFormation change-set empty error as a build
  failure. The build succeeded; the template is identical to the
  deployed state. Check the change-set and `TemplatePath`.
- **NEVER** recommend raising the CodeBuild timeout without first
  reading the build logs. The cause of a 5-minute failure is in the
  failing command, not the 60-minute cap.
- **NEVER** add the pipeline ARN (not the role ARN) to a cross-
  account trust policy. `sts:AssumeRole` requires an IAM principal,
  not a pipeline resource. Use `metadata.pipelineExecutionRole`.
- **NEVER** ignore the KMS key policy on cross-account pipelines.
  The artifact bucket is encrypted; the customer role needs
  `kms:Decrypt` on the key, not just `s3:GetObject` on the bucket.
- **NEVER** declare a Source failure resolved without verifying the
  source object / branch / connection actually exists post-fix.
- **NEVER** confuse `RetryStageExecution` (re-runs only failed
  actions) with starting a new execution. Succeeded actions are not
  re-run; bad Source input requires a fresh execution.
- **NEVER** rely on `CodePipeline Pipeline Execution State Change`
  for action-level alerts. Use the underlying service's
  state-change event (CodeBuild, CloudFormation) for action-level
  failure notifications.

## Recent AWS features (2024-2026)

Recent features — pipeline rollback, FAILED_ACTIONS retry mode, GitHub v2 connections, CodeBuild fleets, EventBridge replay, V2 pipeline type: [Advanced patterns](references/advanced-patterns.md).

## References

See `references/failure-catalog-and-decision-tree.md` for the full
per-stage walk with worked examples per category, and
`references/diagnostic-commands.md` for the canonical command script
for each failure category.

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — expert edge cases, drill-down heuristic, recent features
- [Diagnostic commands](references/diagnostic-commands.md) — per-stage diagnostic command listings and walks
- [Failure catalog and decision tree](references/failure-catalog-and-decision-tree.md) — per-category walk, worked examples, canonical fixes

## Domain

AWS CloudOps / DevTools — CI/CD Pipeline Reliability.

## AWS documentation

- **AWS CodePipeline User Guide** — https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html
- **CodePipeline pipeline executions** — https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts-how-it-works.html
- **CodePipeline cross-account actions** — https://docs.aws.amazon.com/codepipeline/latest/userguide/security-iam.html
- **CodeBuild buildspec reference** — https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html
- **CodeStar Connections** — https://docs.aws.amazon.com/dtconsole/latest/userguide/welcome.html
- **CodePipeline CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/codepipeline/
