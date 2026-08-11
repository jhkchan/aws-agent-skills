# Baseline (no-skill) response: sagemaker-approve-blocked-no-inference-spec

This file captures what a generic assistant produces WITHOUT the
sagemaker-model-registry-operator skill loaded.

---

You can approve the package with:

```
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:111122223333:model-package/research-classifier/7 \
  --model-approval-status Approved
```

This will mark the package as approved and ready for deployment.
