# cicd-pipeline-automator — advanced patterns (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## What this skill does (capability overview)

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

## Stage matrix (which AWS service handles each stage)

**Stage matrix (which AWS service handles each stage):**

| Stage | Provider(s) | Common pitfalls |
|---|---|---|
| Source | CodeCommit, GitHub (CodeStar Connection), S3, ECR | GitHub v1 OAuth is DEPRECATED — use CodeStar Connection |
| Build | CodeBuild (managed image, custom image, VPC) | Wrong runtime image, missing VPC config for private resources |
| Test | CodeBuild (unit/integration), CodeGuru Reviewer | Quality gate misconfigured, security scan not blocking |
| Deploy | CloudFormation, CodeDeploy, S3, ECS, Service Catalog, Elastic Beanstalk, Alex Skills Kit | Empty change-set, wrong deploy role, missing artifact encryption |
| Approval | Manual (SNS notification) | Missing NotificationArn = silent gate |
| Invoke | Lambda, Step Functions, SSM Automation | Lambda async invocation without error handling |

## Mindset — three CodePipeline realities

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

## Step 0: Expert knowledge — non-obvious CodePipeline behaviors

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
