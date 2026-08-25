# Advanced Patterns — CodePipeline Failure Troubleshooter

Load-on-demand expert material moved verbatim from SKILL.md: expert edge cases, heuristics, and recent features.

## Expert edge cases

These patterns represent genuine, non-obvious CodePipeline failure
modes that a senior operator would catch but a generalist would miss.

### The pipeline action summary is a paraphrase; the service's logs are the cause

The pipeline's `externalExecutionSummary` is a generic phrase like
"Build failed" or "Deployment failed". The verbatim cause lives in
the underlying service: CodeBuild phase logs, CloudFormation
`describe-stack-events`, CodeDeploy lifecycle events, CloudTrail.
Always drill from the pipeline action into the service.

### Cross-account role trust must reference the pipeline *service* role, not the pipeline itself

Operators often add the pipeline ARN (not the role) to the trust
policy. `sts:AssumeRole` requires an IAM principal (role or user), not
a pipeline resource. The pipeline's `roleArn` field
(`metadata.pipelineExecutionRole` in `get-pipeline`) is the principal
that must appear in the trust policy's `Principal.AWS`.

### KMS key policy is the silent killer of cross-account pipelines

Even with a perfect trust policy and IAM permissions, a cross-account
deploy will fail if the KMS key encrypting the artifact bucket does
not grant the customer role `kms:Decrypt`. The error appears as
`AccessDenied` on `s3:GetObject`, but the underlying cause is the KMS
key policy. The KMS key policy must list both the pipeline account's
roles AND the customer account's role.

### CloudFormation change-set empty does NOT mean the build failed

The "No changes to deploy" error in a CloudFormation deploy action is
often misread as a build failure. The build succeeded; the resulting
template is byte-identical to the deployed one. The cause is either
(a) no source change between executions, (b) the build produces
non-deterministic output that happens to match, or (c) the
`TemplatePath` points at the wrong artifact. Inspect the change-set
with `describe-change-set` to confirm.

### Polling vs event-driven source failures differ in symptom

A polling source (`PollForSourceChanges: true`) that fails shows up
as a Source action failure inside an execution. An event-driven
source (`PollForSourceChanges: false`, CloudWatch Events rule) that
fails shows up as a pipeline that never starts (no execution at
all). Misdiagnosing the trigger type leads to fixing the wrong layer.
Read the source action's `PollForSourceChanges` field first.

### `RetryPipelineExecution` only re-runs FAILED actions

`RetryStageExecution` and `RetryPipelineExecution` re-run only the
failed actions (and downstream stages). They do NOT re-run succeeded
actions. If the root cause is in a succeeded action's input (e.g., a
Source action that fetched the wrong commit), retry will not fix it —
you must start a new execution.

### CodeBuild timeout vs pipeline stage timeout

CodeBuild has its own `timeoutInMinutes` (default 60, max 480). The
pipeline stage does not have a separate timeout — it inherits the
CodeBuild timeout. Operators often look for a "stage timeout" setting
and miss the CodeBuild project's `timeoutInMinutes`.

### CloudWatch Events on CodePipeline are not failure events

The `CodePipeline Pipeline Execution State Change` event fires on
state transitions, but `FAILED` is a stage-level signal, not an
action-level signal. For action-level alerts, use EventBridge rules on
`CodeBuild Build State Change` (Build actions) or
`CloudFormation Resource Status Change` (CFN deploy actions).

### CodePipeline throttles under high concurrency

`StartPipelineExecution` is throttled at the account level. A busy
event-driven source can trigger more executions than allowed, and the
Source action fails with `ThrottlingException`. Debounce the trigger
(batch source changes) or request a Service Quota increase.

## Expert heuristic — "Drill from the pipeline action into the service"

The single most common diagnostic mistake is treating the pipeline
console's stage status ("Build Failed", "Deploy Failed") as the root
cause. It is not. It is the category. The actionable signal is the
underlying service's logs — CodeBuild phases, CloudFormation events,
CodeDeploy lifecycle, CloudTrail.

Quick lookup table for common stage → real cause mappings:

| Stage / action | What the pipeline shows | Where the real cause lives |
|---|---|---|
| Source | "Source failed" | The source provider (CodeCommit / S3 / GitHub / CodeStar connection); read `externalExecutionSummary` |
| Build | "Build failed" | `batch-get-builds` phase details + CloudWatch Logs for the failing command |
| Deploy (CFN) | "Deploy failed" | `describe-stack-events` — delegate to the cloudformation-stack-troubleshooter skill |
| Deploy (ECS) | "Deploy failed" | `describe-tasks` stopped-reason |
| Deploy (CodeDeploy) | "Deploy failed" | `get-deployment` lifecycle events per instance |
| Approval | "Approval timed out" | The SNS topic config and `timeoutInMinutes` |
| Cross-account | "AccessDenied" | The customer role trust policy + KMS key policy + bucket policy |

When in doubt, run:
`aws codepipeline list-action-executions --pipeline-name <name>`
and read the failed action's `externalExecutionId`, then drill into
that service's logs.

## Recent AWS features (2024-2026)

- **Pipeline rollback (GA 2024-2025):** automatic rollback to the
  last successful execution when a stage fails, with retention of
  rollback history. Enabled per-stage. Read `RollbackEnabled` in
  `get-pipeline`.
- **RetryPipelineExecution with FAILED_ACTIONS mode (2024):**
  retry only the failed actions (and downstream) without re-running
  succeeded ones — cleaner than `RetryStageExecution`.
- **CodeStar Connections enhanced GitHub v2 (2024-2025):** app-key
  based GitHub connections with automatic rotation, replacing the
  PAT-based v1 source. Migrate v1 → v2 to eliminate token-expiry
  failures.
- **CodeBuild on-demand fleet + reserved capacity (2024-2025):**
  reserved capacity reduces cold-start latency for frequently-run
  builds; mitigates `DOWNLOAD_SOURCE` / `INSTALL` timeouts caused by
  ephemeral capacity contention.
- **EventBridge replay for pipeline triggers (2024):** replay missed
  source events from a time window, useful for diagnosing trigger
  misconfigurations.
- **CodePipeline V2 type (2024-2026):** pipeline-type V2 supports
  stage-level triggers, paralel executions, and per-stage rollback.
  V1 and V2 have different feature surfaces — read `pipelineType`
  in `get-pipeline` before recommending features.
