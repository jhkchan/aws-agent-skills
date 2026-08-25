# Error Handling — SageMaker Model Registry Operator

Diagnostic flows for failed or stalled registry operations, moved out of the SKILL.md body. Loaded on demand.


## Diagnostic flows

### Package stuck in `PendingManualApproval`

1. `describe-model-package --model-package-arn <arn>` — capture
   `ModelApprovalStatus`, `ApprovalDescription`, `InferenceSpecification`.
2. If no `InferenceSpecification`: the package is non-deployable;
   approving it is allowed but downstream deploy will fail. Warn
   the operator.
3. If `ValidationSpecification` is set: check whether validation
   jobs completed. If validation failed, the package is
   effectively un-registered — re-register.
4. If the package has been in `PendingManualApproval` for an
   extended period, surface the model metrics (AUC, precision,
   drift) to the approver.

### Projects pipeline did not trigger on approval

1. `describe-model-package` — confirm `ModelApprovalStatus:
   Approved`.
2. `events list-rules` — find the rule targeting the project's
   CodePipeline; verify its `EventPattern` matches the model
   package group ARN.
3. `codepipeline list-pipeline-executions` — check whether the
   pipeline has a recent execution.
4. If the rule is missing or mis-patterned, recreate it:
   `events put-rule` with
   `EventPattern: {"source": ["aws.sagemaker"], "detail-type": ["SageMaker Model Package State Change"], "detail": {"ModelPackageGroupName": ["<group>"], "ModelApprovalStatus": ["Approved"]}}`.
5. If the pipeline exists but the deploy stage fails, check
   CodeBuild logs for IAM or resource conflicts.

### Model Card content mismatch

1. `describe-model-card --model-card-name <name>` — compare
   `Content` with the source package's `describe-model-package`.
2. If the card was created with `--source-uri-type ModelPackage`,
   it inherits at creation time only. Subsequent package updates
   do NOT refresh the card — re-create the card or use
   `update-model-card` with new content.
3. If the card content is hand-authored and out of sync, run
   `update-model-card` with the corrected JSON.
