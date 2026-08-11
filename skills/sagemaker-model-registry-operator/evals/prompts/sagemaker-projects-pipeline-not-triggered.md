# Eval prompt: sagemaker-projects-pipeline-not-triggered

Diagnose why a SageMaker Projects deploy pipeline did not trigger
after a model package was approved. Walk the pre-flight checks
and emit the standard VERDICT block.

## Scenario

An operator reports that after approving model package version 5
of group "fraud-detection-classifier" in `us-east-1`, the
SageMaker Projects deploy pipeline "fraud-detection-deploy" did
not trigger.

## Known facts

- **Approved package:** version 5 of
  "fraud-detection-classifier"; `describe-model-package`
  confirms `ModelApprovalStatus: Approved`.
- **EventBridge rule** "fraud-detection-approved" exists.
- **EventBridge rule bug:** the rule's
  `EventPattern.detail.ModelPackageGroupName` is set to
  "fraud-detection-research" (wrong group — should be
  "fraud-detection-classifier").
- **CodePipeline** "fraud-detection-deploy" has no recent
  executions.
- **Caller permissions:** `events:PutRule`,
  `events:PutTargets`, `codepipeline:ListPipelineExecutions`.

## Symptom

The operator wants the root cause and the remediation.
