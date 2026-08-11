# Baseline (no-skill) response: sagemaker-model-card-auto-populate

This file captures what a generic assistant produces WITHOUT the
sagemaker-model-registry-operator skill loaded.

---

You can create a Model Card with `create-model-card`. Here's
roughly what the command looks like:

```
aws sagemaker create-model-card \
  --model-card-name fraud-detection-2026-08-card \
  --model-card-content '...' \
  --model-card-status PendingReview
```

You'll need to write the JSON content for the card manually,
including the model overview and intended uses. The card will be
visible in SageMaker Studio once created.
