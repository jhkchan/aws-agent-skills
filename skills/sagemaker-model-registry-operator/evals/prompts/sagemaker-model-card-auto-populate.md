# Eval prompt: sagemaker-model-card-auto-populate

Create a SageMaker Model Card auto-populated from a registered
model package. Walk the pre-flight checks and emit the standard
VERDICT block.

## Scenario

An operator wants to create a Model Card
"fraud-detection-2026-08-card" in `us-east-1`, auto-populated
from a registered model package.

## Known facts

- **Source package ARN:**
  `arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5`
  (current `ModelApprovalStatus`: `Approved`).
- **Card name:** "fraud-detection-2026-08-card".
- **Card status intent:** `PendingReview` (submitted for review
  immediately after creation).
- **Card content (subjective):**
  - Model creator: "risk-platform".
  - Model artifact:
    `s3://ml-models/fraud-detection/2026-08/output/model.tar.gz`.
  - Purpose of model: "Real-time fraud scoring for checkout".
  - Intended uses: "Online payment fraud detection".
- **Caller permissions:** `sagemaker:CreateModelCard`.
- **Region:** us-east-1.

## Symptom

The operator needs the exact `create-model-card` command with
`--source-uri` and `--source-uri-type ModelPackage`.
