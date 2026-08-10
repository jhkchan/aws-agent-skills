# End-to-end usage scenario: codepipeline-failure-troubleshooter

A walkthrough showing the skill diagnosing a CodePipeline
`BUILD_STAGE_FAILED` failure caused by a moved `buildspec.yml`. This
exercises Step 0 (signal capture), Step 1 (stage categorisation),
Step 3 (BUILD_STAGE_FAILED walk), the root-cause catalog, and the
remediation workflow.

## Input (user prompt)

> Our `app-cicd` pipeline in `us-east-1` is failing at the Build
> stage. The CodeBuild project `app-build` returns `buildStatus
> FAILED`. The logs say `YAML_FILE_ERROR Message: buildspec.yml is
> empty or missing`. The last commit moved `buildspec.yml` from the
> repo root to `ci/buildspec.yml`. The CodeBuild project's `buildspec`
> field is unset (defaults to root). No KMS errors.

## Skill output

```text
INCIDENT: app-cicd in us-east-1 — Build stage action "Build" FAILED
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: BUILD_STAGE_FAILED — CodeBuild project "app-build" has
 buildspec set to "buildspec.yml" (default path) but the source
 artifact does not contain a buildspec.yml at the repo root; the
 last commit moved it to ci/buildspec.yml. The DOWNLOAD_SOURCE phase
 succeeded; the INSTALL phase FAILED with phaseFailureReason
 "BUILD_CONTAINER_FAILED" because the buildspec could not be located.
EVIDENCE:
  - list-action-executions: action "Build" in stage "Build",
    lastStatus Failed, externalExecutionSummary "Build failed"
  - batch-get-builds id <build-id>: buildStatus FAILED;
    phases show DOWNLOAD_SOURCE SUCCEEDED, INSTALL FAILED with
    phaseFailureReason "BUILD_CONTAINER_FAILED"
  - CloudWatch Logs (deepLink): "YAML_FILE_ERROR Message:
    buildspec.yml is empty or missing"
  - get-pipeline Build action config: ProjectName "app-build",
    no OverrideBuildspec set
  - CodeBuild project app-build source.buildspec: unset (defaults
    to root path)
ROOT_CAUSE_CATALOG: #5 (buildspec missing or path wrong)
REMEDIATION:
  1. Update the CodeBuild project's buildspec path to match the new
     location:
     aws codebuild update-project --name app-build \
       --source '{"type":"CODEPIPELINE","buildspec":"ci/buildspec.yml","location":"codepipeline://app-cicd"}'
     (Verify the JSON is correct for your project's source block.)
     Alternatively, set OverrideBuildspec on the pipeline's Build
     action via update-pipeline — that scopes the override to this
     pipeline only.
  2. Trigger a fresh execution:
     aws codepipeline start-pipeline-execution --name app-cicd
  3. Monitor the Build action's next execution:
     aws codepipeline list-action-executions --pipeline-name app-cicd \
       --query 'actionExecutionDetails[?actionName==`Build`].{status:status,reason:lastStatusChangeReason}' \
       --output table
     Expect lastStatus Succeeded and a green Build stage.
  4. For future-proofing, prefer an explicit buildspec path in the
     CodeBuild project (do not rely on the root-path default).
```

## What the skill caught that a generic assistant misses

1. **The phase sequence narrows the cause.** A generic assistant
   often stops at "buildspec missing." The skill notes that
   `DOWNLOAD_SOURCE` succeeded (the artifact was fetched) and
   `INSTALL` failed — confirming the buildspec is missing *from the
   source*, not from the artifact-bucket fetch.

2. **The fix location matters.** A generic assistant suggests "update
   the buildspec path." The skill identifies two distinct fix
   locations: the CodeBuild project (`source.buildspec`) for a global
   change, OR the pipeline action's `OverrideBuildspec` for a
   pipeline-scoped override.

3. **The post-fix verification step.** A generic assistant typically
   says "retry the pipeline." The skill specifies
   `start-pipeline-execution` (a fresh run, since the pipeline
   definition changed) and a monitoring command targeting the
   Build action specifically.

4. **The forward-looking note.** The skill recommends pinning an
   explicit buildspec path rather than relying on the default —
   preventing the same failure on the next repo restructure.

## Slash-command invocation

```
/aws:troubleshoot-codepipeline-failure
```

Or via the orchestrator:

```
/aws:pipeline
You: "app-cicd Build stage failing — buildspec.yml missing"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
codepipeline-failure-troubleshooter]` and hands off to this skill
for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the failing account:

```bash
# Identify the most recent failed execution.
aws codepipeline list-pipeline-executions --pipeline-name app-cicd \
  --query 'pipelineExecutionSummaries[?status==`Failed`].{id:pipelineExecutionId,start:startTime,summary:summary}' \
  --output table

# List the failed actions in that execution.
aws codepipeline list-action-executions --pipeline-name app-cicd \
  --filter '{"pipelineExecutionId": "<id>"}' \
  --query 'actionExecutionDetails[?status==`Failed`].{stage:stageName,action:actionName,reason:lastStatusChangeReason,external:externalExecutionSummary,externalExecutionId:externalExecutionId}' \
  --output table

# For the Build action, read the CodeBuild build phases.
aws codebuild batch-get-builds --ids <build-id> \
  --query 'builds[0].{status:buildStatus,phases:phases[*].{type:phaseType,status:phaseStatus,reason:phaseFailureReason},logs:logs}'

# Read the failing phase's logs.
aws logs get-log-events \
  --log-group-name /aws/codebuild/app-build \
  --log-stream-name <stream> \
  --start-from-head
```

If `DOWNLOAD_SOURCE` SUCCEEDED, `INSTALL` FAILED, and the logs show
`buildspec.yml is empty or missing`, the diagnosis is confirmed. The
fix is to point the CodeBuild project (or the pipeline action's
`OverrideBuildspec`) at the actual buildspec location.

## Related scenarios

The same skill handles:

- **SOURCE_STAGE_FAILED** — GitHub token expired, CodeStar connection
  pending, CodeCommit branch deleted, S3 source object missing.
- **DEPLOY_STAGE_FAILED** — CloudFormation change-set empty, ECS task
  invalid, CodeDeploy unhealthy, S3 deploy bucket missing.
- **APPROVAL_TIMEOUT** — `timeoutInMinutes` exceeded; SNS topic
  missing or unconfigured.
- **CROSS_ACCOUNT_ROLE_FAILED** — trust policy lists the wrong
  pipeline role (common after a rename); KMS key policy missing the
  customer role; artifact bucket policy missing the customer role.
