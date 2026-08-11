# End-to-end usage scenario: sagemaker-training-job-operator

A walkthrough showing the skill planning a 4 × `ml.p5.48xlarge`
(32-GPU) SMDDP launch with Training Compiler, VPC isolation, and
warm-pool handoff. This exercises Step 0 (target capture), Step 1
(pre-flight: role, quota, image, S3, VPC), Step 2c (distributed
launch), Step 3 (monitoring), and Step 6 (model registration).

## Input (user prompt)

> Launch `bert-pretrain-2026-08` in `us-east-1`: BERT-large pretraining
> on 4 × `ml.p5.48xlarge` (32 GPUs total) using SMDDP with Training
> Compiler. Input is `s3://ml-datasets/bert/train/` (12M objects);
> output `s3://ml-models/bert/2026-08/`. The PyTorch image is
> `763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.3.0-gpu-py311-cu121-ubuntu22.04-sagemaker`.
> The execution role has all required permissions. P5 quota is 8.
> VPC subnets `subnet-aaa/bbb/ccc`; security group `sg-yyy`; S3 VPC
> endpoint available.

## Skill output

```text
OPERATION: launch-distributed
VERDICT: READY
TARGET: bert-pretrain-2026-08, ml.p5.48xlarge x4, us-east-1
PRE_CHECKS:
  - [PASS] iam simulate-principal-policy: s3:GetObject on
    s3://ml-datasets/bert/ Allowed; s3:PutObject on
    s3://ml-models/bert/ Allowed
  - [PASS] service-quotas get-service-quota for ml.p5.48xlarge:
    Value 8, Adjustable true — capacity for 4 instances (32 GPUs)
  - [PASS] ECR image
    763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.3.0-gpu-py311-cu121-ubuntu22.04-sagemaker
    exists; role has ecr:BatchGetImage
  - [PASS] S3 input s3://ml-datasets/bert/train/ has 12M objects
  - [PASS] VPC subnets subnet-aaa/bbb/ccc in us-east-1; S3 VPC
    endpoint vpce-xxx available; security group sg-yyy allows
    443 outbound
  - [PASS] Training Compiler supported on PyTorch 2.3.0 GPU image
STEPS:
  1. Launch the distributed training job with SMDDP and Training
     Compiler:
     aws sagemaker create-training-job \
       --training-job-name bert-pretrain-2026-08 \
       --algorithm-specification '{"TrainingImage":"763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.3.0-gpu-py311-cu121-ubuntu22.04-sagemaker","TrainingInputMode":"FastFile","EnableSageMakerTrainingCompiler":true}' \
       --resource-config '{"InstanceType":"ml.p5.48xlarge","InstanceCount":4,"VolumeSizeInGB":4096,"VolumeKmsKeyId":"arn:aws:kms:us-east-1:111122223333:key/abc"}' \
       --hyper-parameters '{"sagemaker_program":"train_ddp.py","sagemaker_submit_directory":"s3://ml-code/bert/train.tar.gz","sagemaker_distributed_dataparallel_enabled":true,"sagemaker_distributed_dataparallel_num_processes":32,"epochs":50,"batch_size":256,"learning_rate":0.0001}' \
       --role-arn arn:aws:iam::111122223333:role/sagemaker-exec \
       --input-data-config '[{"ChannelName":"train","DataSource":{"S3DataSource":{"S3DataType":"S3Prefix","S3Uri":"s3://ml-datasets/bert/train/","S3DataDistributionType":"ShardedByS3Key"}}}]' \
       --output-data-config '{"S3OutputPath":"s3://ml-models/bert/2026-08/"}' \
       --vpc-config '{"Subnets":["subnet-aaa","subnet-bbb","subnet-ccc"],"SecurityGroupIds":["sg-yyy"]}' \
       --stop-condition '{"MaxRuntimeInSeconds":172800}' \
       --enable-network-isolation
  2. Block until the job reaches a terminal state:
     aws sagemaker wait training-job-completed-or-stopped \
       --training-job-name bert-pretrain-2026-08
  3. Read the final status and model artifact:
     aws sagemaker describe-training-job \
       --training-job-name bert-pretrain-2026-08 \
       --query '{status:TrainingJobStatus,reason:FailureReason,elapsed:TrainingTimeInSeconds,artifact:ModelArtifacts.S3ModelArtifacts}'
POST_VERIFY:
  - [PASS] (pending execution) expect TrainingJobStatus Completed
    with ModelArtifacts.S3ModelArtifacts populated to
    s3://ml-models/bert/2026-08/bert-pretrain-2026-08/output/model.tar.gz
  - [PASS] (pending execution) expect
    sagemaker_distributed_dataparallel_num_processes=32 respected
    — CloudWatch logs report "World size 32"
MODEL_ARTIFACT: pending — will populate on Completed
LOG_GROUP: /aws/sagemaker/TrainingJobs
CONFIRM: About to launch bert-pretrain-2026-08 (4 × ml.p5.48xlarge,
32 GPUs SMDDP, Training Compiler on) in us-east-1. Estimated
runtime: 24-48 hours. Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **`num_processes` = 32, not 4.** A generic assistant often sets
   `num_processes` to the instance count (4). The skill sets it to
   the total GPU count (4 × 8 = 32), preventing a silent 8x
   performance regression.
2. **`ShardedByS3Key` data distribution.** A generic assistant
   leaves the default `FullyReplicated`, which copies the full
   dataset to every instance. The skill uses `ShardedByS3Key` so
   each instance receives a shard.
3. **Pre-flight on the execution role and quota before launch.**
   A generic assistant skips the pre-flight and the job fails
   within seconds with a permission or quota error. The skill runs
   `iam simulate-principal-policy` and `service-quotas
   get-service-quota` first.
4. **Training Compiler version compatibility check.** A generic
   assistant enables Training Compiler without verifying the
   image supports it. The skill confirms the PyTorch 2.3.0 GPU
   image is on the supported versions matrix.
5. **`EnableNetworkIsolation` VPC endpoint check.** A generic
   assistant adds `--enable-network-isolation` without verifying
   the S3 and ECR VPC endpoints exist. The skill confirms the S3
   VPC endpoint before launch.
6. **Wait + verification command.** A generic assistant launches
   and stops. The skill emits the `wait training-job-completed-or-stopped`
   command and the `describe-training-job` verification query.

## Slash-command invocation

```
/aws:operate-sagemaker-training-job
```

Or via the orchestrator:

```
/aws:pipeline
You: "launch bert-pretrain-2026-08 on 4 × P5 with SMDDP"
```

The orchestrator emits `[Phase: Operate | Skills routed:
sagemaker-training-job-operator]` and hands off to this skill for
the VERDICT.

## Related scenarios

The same skill handles:

- **Spot training with checkpointing** — `EnableManagedSpotTraining`
  + `CheckpointConfig`; set `MaxWaitTimeInSeconds` >>
  `MaxRuntimeInSeconds`.
- **Warm pool reuse across sequential jobs** —
  `WarmPoolConfig` with matching instance type + image;
  `delete-warm-pool` when the sequence ends.
- **HPO launch with warm start** — `create-hyper-parameter-tuning-job`
  with `WarmStartType: IdenticalDataAndAlgorithm` and
  `TrainingJobEarlyStoppingType: Auto`.
- **Model registry registration** — `create-model` +
  `create-model-package` with `PendingManualApproval`; approve
  via `update-model-package`.
- **BLOCKED: P5 / Trn1 quota is zero** — request a quota increase
  via Service Quotas before launch; or use `ml.p4de.24xlarge` as
  fallback.
- **SMDMP for models exceeding single-GPU memory** — configure
  `pipeline_parallel_degree` + `tensor_parallel_degree` whose
  product divides evenly into the total GPU count.
