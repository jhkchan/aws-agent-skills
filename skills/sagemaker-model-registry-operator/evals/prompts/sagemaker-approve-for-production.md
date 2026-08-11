# Eval prompt: sagemaker-approve-for-production

Approve a SageMaker model package for production deployment. Walk
the pre-flight checks and emit the standard VERDICT block.

## Scenario

An operator wants to approve model package version 5 of group
"fraud-detection-classifier" in `us-east-1`.

## Known facts

- **Package ARN:**
  `arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5`
- **Current `ModelApprovalStatus`:** `PendingManualApproval`.
- **InferenceSpecification:** present with supported instance
  types `ml.m5.large` / `ml.m5.xlarge`.
- **SageMaker Project** "fraud-detection-deploy" is wired to
  this group with an EventBridge rule that triggers the deploy
  pipeline on `Approved` transitions.
- **Caller permissions:** `sagemaker:UpdateModelPackage`.
- **Reviewer:** risk-platform review board.
- **Metrics reviewed:** AUC=0.94 with no bias drift vs the
  2026-07 model.

## Symptom

The operator needs the exact `update-model-package` command
with an audit-trail approval description.
