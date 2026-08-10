# Eval prompt: cp-build-buildspec-missing

Diagnose the following CodePipeline execution failure. Walk the
BUILD_STAGE_FAILED decision tree and emit the standard VERDICT block.

## Scenario

A CodePipeline `app-cicd` in `us-east-1` fails at the Build stage.
The Build action invokes the CodeBuild project `app-build`.

## Known facts

- `list-action-executions` shows the Build action with:
  - `lastStatus: Failed`
  - `externalExecutionId: <codebuild-build-id>`
  - `externalExecutionSummary: "Build failed"`
- `aws codebuild batch-get-builds --ids <build-id>` shows:
  - `buildStatus: FAILED`
  - `phases`:
    - `DOWNLOAD_SOURCE` — SUCCEEDED (the source artifact was fetched
      from the pipeline artifact bucket)
    - `INSTALL` — FAILED with `phaseFailureReason: "BUILD_CONTAINER_FAILED"`
  - `logs.deepLink` points at the CloudWatch log stream.
- The CloudWatch log stream contains:
  ```
  YAML_FILE_ERROR Message: buildspec.yml is empty or missing
  ```
- `get-pipeline` Build action configuration shows `ProjectName: app-build`
  and no `OverrideBuildspec` set.
- The CodeBuild project `app-build` has `source.buildspec` unset
  (defaults to `buildspec.yml` at the repository root).
- The last commit in the source artifact moved `buildspec.yml` from
  the repository root to `ci/buildspec.yml` and deleted the original
  file at the root.
- No KMS access errors appear in the CodeBuild logs.

## Symptom

Every pipeline execution now fails at the Build stage immediately
after the INSTALL phase begins.
