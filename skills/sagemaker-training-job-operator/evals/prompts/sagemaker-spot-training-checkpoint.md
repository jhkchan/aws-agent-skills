# Eval prompt: sagemaker-spot-training-checkpoint

Plan the launch of a SageMaker training job with managed spot training
and checkpointing. Walk the pre-flight checks and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, MODEL_ARTIFACT, LOG_GROUP, CONFIRM).

## Scenario

An operator wants to launch a SageMaker training job
`resnet-spot-2026-08` in `us-east-1` on `ml.p4de.24xlarge` with
managed spot training.

## Known facts

- **Algorithm:** PyTorch ResNet-50 training script at
  `s3://ml-code/resnet/train.tar.gz`, entry point `train.py`.
- **Framework image:**
  `763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.3.0-gpu-py311-cu121-ubuntu22.04-sagemaker`.
- **Input:** `s3://ml-datasets/imagenet/train/` (train channel,
  1.2M JPEG objects).
- **Output:** `s3://ml-models/resnet/2026-08/`.
- **Checkpoint S3:** `s3://ml-checkpoints/resnet-spot/`.
- **Framework checkpoint path:** the PyTorch entry point saves
  checkpoints to `/opt/ml/checkpoints/checkpoint.pt` at the end of
  each epoch.
- **Execution role:** `arn:aws:iam::111122223333:role/sagemaker-exec`
  with `s3:GetObject` and `s3:PutObject` on all relevant buckets,
  `kms:Decrypt` on the volume KMS key, and `ecr:BatchGetImage`.
- **Service Quota:** `ml.p4de.24xlarge` quota is 4 (sufficient for
  1 instance).
- **Expected per-attempt training time:** ~24 hours.
- **Operator wants to budget for 3 spot interruptions** (retries).

## Symptom

The operator needs the exact CLI sequence to launch the job with
spot training and checkpointing so it survives interruptions and
resumes from the last epoch.
