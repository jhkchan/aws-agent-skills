# Baseline (no-skill) response: sagemaker-approve-for-production

This file captures what a generic assistant produces WITHOUT the
sagemaker-model-registry-operator skill loaded.

---

To approve the model package, you can use
`update-model-package`:

```
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5 \
  --model-approval-status Approved
```

Once approved, the model is ready for deployment to a SageMaker
endpoint. If you have a SageMaker Projects pipeline set up, it
should deploy automatically.
