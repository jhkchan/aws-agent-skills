# Worked Examples — SageMaker Model Registry Operator

Secondary worked examples moved out of the SKILL.md body. Loaded on demand.


## Worked example — approve blocked (BLOCKED)

```text
OPERATION: approve
VERDICT: BLOCKED
TARGET: fraud-detection-classifier / version 5, us-east-1
PRE_CHECKS:
  - [PASS] describe-model-package returns ModelApprovalStatus PendingManualApproval (transition to Approved is legal)
  - [FAIL] No InferenceSpecification on package version 5. The package was registered as a documentation-only package (model card source). Approving it will not enable deployment because there is no inference spec.
  - [PASS] Caller holds sagemaker:UpdateModelPackage
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
STATE: PendingManualApproval (cannot usefully approve)
VERSION: 5
NOTES:
  - Re-register the package with an InferenceSpecification before approving for deployment. The current package can still be used as a Model Card source.
  - Transition PendingManualApproval → Approved is technically legal without an InferenceSpecification, but the approved package cannot be deployed to a SageMaker endpoint.
```
