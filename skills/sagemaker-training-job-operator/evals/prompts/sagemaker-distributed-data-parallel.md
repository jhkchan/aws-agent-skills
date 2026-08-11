# Eval prompt: sagemaker-distributed-data-parallel

Plan the launch of a distributed SageMaker training job using SMDDP
on P5 instances. Walk the pre-flight checks and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, MODEL_ARTIFACT, LOG_GROUP, CONFIRM).

## Scenario

An operator wants to pretrain BERT-large using SageMaker Distributed
Data Parallel (SMDDP) on 4 × `ml.p5.48xlarge` instances (32 GPUs
total) in `us-east-1`, with Training Compiler enabled.

## Known facts

- **Algorithm:** PyTorch BERT pretraining script at
  `s3://ml-code/bert/train_ddp.tar.gz`, entry point `train_ddp.py`.
- **Framework image:**
  `763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.3.0-gpu-py311-cu121-ubuntu22.04-sagemaker`.
- **Input:** `s3://ml-datasets/bert/train/` (12M objects).
- **Output:** `s3://ml-models/bert/2026-08/`.
- **Execution role:** `arn:aws:iam::111122223333:role/sagemaker-exec`
  with `s3:GetObject`, `s3:PutObject`, `kms:Decrypt`,
  `ecr:BatchGetImage`.
- **Service Quota:** `ml.p5.48xlarge` quota is 8 (sufficient for 4
  instances × 8 GPUs = 32 GPUs).
- **VPC:** subnets `subnet-aaa`, `subnet-bbb`, `subnet-ccc`;
  security group `sg-yyy`; S3 VPC endpoint `vpce-xxx` available.
- **Training Compiler:** enabled on the supported PyTorch image.

## Symptom

The operator wants the exact `create-training-job` CLI sequence
with `num_processes` set correctly and input distributed via
`ShardedByS3Key`.
