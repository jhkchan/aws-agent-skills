# Eval prompt: sagemaker-approve-blocked-no-inference-spec

Approve a SageMaker model package. Walk the pre-flight checks and
emit the standard VERDICT block.

## Scenario

An operator wants to approve model package version 7 of group
"research-classifier" in `us-east-1`.

## Known facts

- **Current `ModelApprovalStatus`:** `PendingManualApproval`.
- **InferenceSpecification:** missing. The package was
  registered without an inference spec — it is intended only as
  a Model Card source (documentation).
- **Caller permissions:** `sagemaker:UpdateModelPackage`.

## Symptom

The operator wants to know whether approving the package is safe
and whether it will enable deployment.
