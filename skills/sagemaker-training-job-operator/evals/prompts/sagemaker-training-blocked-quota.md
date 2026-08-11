# Eval prompt: sagemaker-training-blocked-quota

Plan the launch of a SageMaker training job on P5 and identify any
blockers. Walk the pre-flight checks and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
MODEL_ARTIFACT, LOG_GROUP, CONFIRM).

## Scenario

An operator wants to launch a training job
`llama-finetune-2026-08` in `us-east-1` on `ml.p5.48xlarge` (1
instance, 8 H100 GPUs) to fine-tune a Llama model.

## Known facts

- **Execution role:** `arn:aws:iam::111122223333:role/sagemaker-exec`
  with `s3:GetObject`, `s3:PutObject`, `kms:Decrypt`,
  `ecr:BatchGetImage` — all required permissions are present.
- **Service Quota:** `aws service-quotas get-service-quota` for
  `ml.p5.48xlarge` returns `Value: 0`, `Adjustable: true`.
- **The operator has not requested a quota increase.**
- **ECR image:** exists and accessible.
- **Input data:** `s3://ml-datasets/llama/` reachable.
- **Output:** `s3://ml-models/llama/2026-08/`.

## Symptom

The operator is asking why the job cannot launch right now and what
to do about it.
