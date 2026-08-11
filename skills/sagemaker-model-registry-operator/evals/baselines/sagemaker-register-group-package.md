# Baseline (no-skill) response: sagemaker-register-group-package

This file captures what a generic assistant produces WITHOUT the
sagemaker-model-registry-operator skill loaded.

---

You can register your model in SageMaker Model Registry with
`create-model-package`. Here's roughly what the command looks
like:

```
aws sagemaker create-model-package \
  --model-package-name fraud-detection-2026-08-v1 \
  --inference-specification '...' \
  --approval-status PendingManualApproval
```

Make sure your model artifact is in S3 and your inference image
is in ECR. You can check the status with
`describe-model-package`.
