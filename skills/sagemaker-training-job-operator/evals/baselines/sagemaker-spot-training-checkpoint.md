# Baseline (no-skill) response: sagemaker-spot-training-checkpoint

This file captures what a generic assistant produces WITHOUT the
sagemaker-training-job-operator skill loaded.

---

To launch a spot training job in SageMaker, you can use
`create-training-job` with `--enable-managed-spot-training`. You'll
also want to set up checkpointing so the job can resume after
interruptions.

Here's roughly what the command looks like:

```
aws sagemaker create-training-job \
  --training-job-name resnet-spot-2026-08 \
  --algorithm-specification '...' \
  --enable-managed-spot-training
```

Make sure your PyTorch script saves checkpoints to S3. You might
also want to set `MaxRuntimeInSeconds` and `MaxWaitTimeInSeconds`
to control how long the job can run.
