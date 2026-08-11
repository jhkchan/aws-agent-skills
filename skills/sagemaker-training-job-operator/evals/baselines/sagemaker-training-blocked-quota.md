# Baseline (no-skill) response: sagemaker-training-blocked-quota

This file captures what a generic assistant produces WITHOUT the
sagemaker-training-job-operator skill loaded.

---

Your job can't launch because you don't have enough P5 instances in
your account. The default quota for `ml.p5.48xlarge` is 0, so you
need to request an increase.

Go to the Service Quotas console and request a quota increase for
SageMaker `ml.p5.48xlarge`. Once approved, you'll be able to launch
your training job.

Alternatively, you could use `ml.p4de.24xlarge` which might have
quota available.
