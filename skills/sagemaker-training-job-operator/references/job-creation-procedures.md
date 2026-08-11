# Job creation procedures — SageMaker training

This reference expands the SKILL.md operation steps with the full
per-operation CLI playbook. Load when launching a specific operation
type in depth.

## Single-instance training (baseline)

```bash
aws sagemaker create-training-job \
  --training-job-name <name> \
  --algorithm-specification '{
    "TrainingImage": "<ecr-image-uri>",
    "TrainingInputMode": "File",
    "FrameworkVersion": "<version>"
  }' \
  --input-data-config '[
    {"ChannelName":"train","DataSource":{"S3DataSource":{"S3DataType":"S3Prefix","S3Uri":"s3://<bucket>/train/","S3DataDistributionType":"FullyReplicated"}}},
    {"ChannelName":"test","DataSource":{"S3DataSource":{"S3DataType":"S3Prefix","S3Uri":"s3://<bucket>/test/","S3DataDistributionType":"FullyReplicated"}}}
  ]' \
  --output-data-config '{"S3OutputPath":"s3://<output-bucket>/models/"}' \
  --resource-config '{"InstanceType":"ml.p5.48xlarge","InstanceCount":1,"VolumeSizeInGB":1024,"VolumeKmsKeyId":"arn:aws:kms:<region>:<account>:key/<id>"}' \
  --hyper-parameters '{
    "sagemaker_program":"train.py",
    "sagemaker_submit_directory":"s3://<bucket>/code/train.tar.gz",
    "epochs":50,
    "batch_size":64,
    "learning_rate":0.001
  }' \
  --role-arn <execution-role-arn> \
  --stop-condition '{"MaxRuntimeInSeconds":86400}' \
  --vpc-config '{"Subnets":["subnet-xxx"],"SecurityGroupIds":["sg-xxx"]}' \
  --enable-network-isolation
```

### Input modes

| `TrainingInputMode` | Behaviour | When to use |
|---|---|---|
| `File` | Downloads the full dataset to the EBS volume before training starts | Small datasets (< instance volume); simple workflows |
| `FastFile` | Streams objects from S3 via FUSE without downloading | Large datasets where `File` is too slow; small per-object overhead |
| `Pipe` | Streams from Kinesis or augmented manifest | Specific input formats (recordIO-protobuf, Pipe-mode channels) |

### Input data distribution

| `S3DataDistributionType` | Behaviour | When to use |
|---|---|---|
| `FullyReplicated` (default) | Full dataset copied to every instance | Single-instance training; small datasets |
| `ShardedByS3Key` | Each instance receives a shard based on S3 key hash | Distributed training (SMDDP); large datasets |

## Spot training with checkpointing

```bash
aws sagemaker create-training-job \
  --training-job-name <name> \
  --algorithm-specification '...' \
  --input-data-config '...' \
  --output-data-config '...' \
  --resource-config '{"InstanceType":"ml.p4de.24xlarge","InstanceCount":1,"VolumeSizeInGB":1024}' \
  --hyper-parameters '...' \
  --role-arn <execution-role-arn> \
  --checkpoint-config '{
    "S3Uri":"s3://<checkpoint-bucket>/checkpoints/",
    "LocalPath":"/opt/ml/checkpoints"
  }' \
  --enable-managed-spot-training \
  --checkpoint-local-path /opt/ml/checkpoints \
  --spot-timeout-in-seconds 300 \
  --max-wait-time-in-seconds 86400 \
  --max-runtime-in-seconds 7200
```

### Spot training key parameters

| Parameter | Meaning | Constraint |
|---|---|---|
| `EnableManagedSpotTraining` | Enables spot instances | Must be paired with `CheckpointConfig` for useful recovery |
| `CheckpointConfig.S3Uri` | S3 prefix for checkpoint sync | Must be in the same region as the job |
| `CheckpointConfig.LocalPath` | Local path the framework writes checkpoints to | Must match the framework's save path (e.g., `/opt/ml/checkpoints`) |
| `MaxWaitTimeInSeconds` | Wall-clock budget including interruptions + retries | Must be >= `MaxRuntimeInSeconds` |
| `MaxRuntimeInSeconds` | Per-attempt training time budget | Single training attempt budget |

### Framework checkpoint pattern (PyTorch)

```python
# At the start of each epoch, attempt to load a checkpoint:
import os
checkpoint_dir = "/opt/ml/checkpoints"
os.makedirs(checkpoint_dir, exist_ok=True)
checkpoint_path = os.path.join(checkpoint_dir, "checkpoint.pt")

start_epoch = 0
if os.path.exists(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    start_epoch = checkpoint["epoch"] + 1

# At the end of each epoch, save a checkpoint:
for epoch in range(start_epoch, num_epochs):
    train_one_epoch(model, ...)
    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
    }, checkpoint_path)
```

SageMaker syncs `/opt/ml/checkpoints` to S3 automatically. On spot
interruption, the next launch restores from S3.

## Distributed training (SMDDP)

```bash
aws sagemaker create-training-job \
  --training-job-name <name> \
  --algorithm-specification '{
    "TrainingImage": "<pytorch-gpu-image>",
    "TrainingInputMode": "FastFile",
    "EnableSageMakerTrainingCompiler": true
  }' \
  --resource-config '{"InstanceType":"ml.p5.48xlarge","InstanceCount":4,"VolumeSizeInGB":2048}' \
  --hyper-parameters '{
    "sagemaker_program":"train_ddp.py",
    "sagemaker_submit_directory":"s3://<bucket>/code/train.tar.gz",
    "sagemaker_distributed_dataparallel_enabled":true,
    "sagemaker_distributed_dataparallel_num_processes":32,
    "batch_size":256
  }' \
  --role-arn <execution-role-arn> \
  --input-data-config '[{"ChannelName":"train","DataSource":{"S3DataSource":{"S3DataType":"S3Prefix","S3Uri":"s3://<bucket>/train/","S3DataDistributionType":"ShardedByS3Key"}}}]' \
  --output-data-config '...' \
  --enable-managed-spot-training \
  --checkpoint-config '...'
```

### SMDDP `num_processes` cheat sheet

| Instance type | GPUs per instance | Instance count | `num_processes` |
|---|---|---|---|
| `ml.p3.16xlarge` | 8 | 1 | 8 |
| `ml.p3.16xlarge` | 8 | 4 | 32 |
| `ml.p4d.24xlarge` | 8 | 1 | 8 |
| `ml.p4d.24xlarge` | 8 | 4 | 32 |
| `ml.p4de.24xlarge` | 8 | 1 | 8 |
| `ml.p4de.24xlarge` | 8 | 8 | 64 |
| `ml.p5.48xlarge` | 8 | 1 | 8 |
| `ml.p5.48xlarge` | 8 | 4 | 32 |
| `ml.p5.48xlarge` | 8 | 8 | 64 |
| `ml.g5.48xlarge` | 8 | 1 | 8 |

### SMDMP (model parallel) configuration

```bash
--hyper-parameters '{
  "sagemaker_distributed_modelparallel_enabled": true,
  "sagemaker_mp_parameters": "pipeline_parallel_degree=2;tensor_parallel_degree=4;microbatches=4",
  ...
}'
```

| Parameter | Meaning |
|---|---|
| `pipeline_parallel_degree` | Number of pipeline stages (model split across this many devices) |
| `tensor_parallel_degree` | Number of devices for tensor parallelism (within each pipeline stage) |
| `microbatches` | Number of microbatches for pipeline scheduling |

The product of `pipeline_parallel_degree` × `tensor_parallel_degree`
must divide evenly into the total GPU count. For 4 × `ml.p5.48xlarge`
(32 GPUs), valid configs include: pp=2, tp=4 (8); pp=4, tp=2 (8);
pp=2, tp=8 (16); pp=4, tp=8 (32).

## Warm pools

```bash
# First (source) job — establishes the warm pool:
aws sagemaker create-training-job \
  --training-job-name <name>-source \
  ... \
  --resource-config '{"InstanceType":"ml.p5.48xlarge","InstanceCount":1,"VolumeSizeInGB":1024,"KeepAlivePeriodInSeconds":1800}'

# Subsequent (target) job — reuses the warm pool:
aws sagemaker create-training-job \
  --training-job-name <name>-followup \
  ... \
  --resource-config '{"InstanceType":"ml.p5.48xlarge","InstanceCount":1,"VolumeSizeInGB":1024,"KeepAlivePeriodInSeconds":1800}' \
  --warm-pool-config '{"PoolName":"<source-job-name>"}'

# List warm pools:
aws sagemaker list-warm-pools \
  --query 'WarmPoolResources[].{id:WarmPoolId,status:Status,job:LastUpdatedJobName,instance:ResourceConfig.InstanceType}'

# Delete a warm pool (stop billing):
aws sagemaker delete-warm-pool --warm-pool-id <id>
```

The target job must match the source's instance type, instance count,
and image — otherwise it cold-starts.

## HPO (hyperparameter tuning)

```bash
aws sagemaker create-hyper-parameter-tuning-job \
  --hyper-parameter-tuning-job-name <name> \
  --hyper-parameter-tuning-job-config '{
    "Strategy":"Bayesian",
    "HyperParameterTuningJobObjective":{"Type":"Maximize","MetricName":"validation:accuracy"},
    "ResourceLimits":{"MaxNumberOfTrainingJobs":50,"MaxParallelTrainingJobs":4},
    "ParameterRanges":{
      "ContinuousParameterRanges":[{"Name":"learning_rate","MinValue":"0.0001","MaxValue":"0.1","ScalingType":"Logarithmic"}],
      "IntegerParameterRanges":[{"Name":"batch_size","MinValue":"32","MaxValue":"256","ScalingType":"Auto"}]
    },
    "TrainingJobEarlyStoppingType":"Auto"
  }' \
  --training-job-definition '{
    "AlgorithmSpecification":{"TrainingImage":"<image>","TrainingInputMode":"File","MetricDefinitions":[{"Name":"validation:accuracy","Regex":"val_acc: ([0-9\\.]+)"}]},
    "RoleArn":"<execution-role-arn>",
    "InputDataConfig":[...],
    "OutputDataConfig":{"S3OutputPath":"s3://<output>/hpo/"},
    "ResourceConfig":{"InstanceType":"ml.p5.48xlarge","InstanceCount":1,"VolumeSizeInGB":1024},
    "StaticHyperParameters":{"epochs":20},
    "StoppingCondition":{"MaxRuntimeInSeconds":3600}
  }'

# Warm start:
aws sagemaker create-hyper-parameter-tuning-job \
  --hyper-parameter-tuning-job-name <name>-warm \
  --warm-start-config '{
    "ParentHyperParameterTuningJobs":[{"HyperParameterTuningJobName":"<previous-tuning-job>"}],
    "WarmStartType":"IdenticalDataAndAlgorithm"
  }' \
  --hyper-parameter-tuning-job-config '...' \
  --training-job-definition '...'

# Monitor:
aws sagemaker describe-hyper-parameter-tuning-job \
  --hyper-parameter-tuning-job-name <name> \
  --query '{status:HyperParameterTuningJobStatus,best:BestTrainingJob,progress:TrainingJobStatusCounters}'

# Stop:
aws sagemaker stop-hyper-parameter-tuning-job \
  --hyper-parameter-tuning-job-name <name>
```

## Model registration

```bash
# 1. Create the model (links the artifact to an image for inference):
aws sagemaker create-model \
  --model-name <name>-model \
  --primary-container '{
    "Image":"<inference-image-uri>",
    "ModelDataUrl":"s3://<output-bucket>/models/<name>/output/model.tar.gz"
  }' \
  --execution-role-arn <execution-role-arn> \
  --vpc-config '{"Subnets":[...],"SecurityGroupIds":[...]}' \
  --enable-network-isolation

# 2. Create or use an existing model package group:
aws sagemaker create-model-package-group \
  --model-package-group-name <group-name> \
  --model-package-group-description "Production candidate models"

# 3. Register the model as a versioned package:
aws sagemaker create-model-package \
  --model-package-name <name>-v1 \
  --model-package-group-name <group-name> \
  --inference-specification '{
    "Containers":[{"Image":"<inference-image-uri>","ModelDataUrl":"s3://<output>/models/<name>/output/model.tar.gz"}],
    "SupportedTransformInstanceTypes":["ml.m5.4xlarge"],
    "SupportedRealtimeInferenceInstanceTypes":["ml.m5.xlarge","ml.g5.xlarge"]
  }' \
  --model-metrics '{
    "ModelQuality":{"Statistics":{"ContentType":"application/json","S3Uri":"s3://<metrics>/quality.json"}}
  }' \
  --approval-status PendingManualApproval

# 4. Approve for deployment:
aws sagemaker update-model-package \
  --model-package-arn <arn> \
  --model-approval-status Approved
```

## Monitoring and lifecycle

```bash
# Watch training job status:
aws sagemaker describe-training-job \
  --training-job-name <name> \
  --query '{status:TrainingJobStatus,secondary:SecondaryStatus,reason:FailureReason,elapsed:TrainingTimeInSeconds,billable:BillableTimeInSeconds,artifact:ModelArtifacts.S3ModelArtifacts}'

# Stream CloudWatch logs (live tail):
aws logs tail /aws/sagemaker/TrainingJobs --log-stream-name-prefix <name> --follow

# Block until completion or failure:
aws sagemaker wait training-job-completed-or-stopped \
  --training-job-name <name>

# Stop a running job:
aws sagemaker stop-training-job --training-job-name <name>

# List recent jobs:
aws sagemaker list-training-jobs --status-equals InProgress \
  --query 'TrainingJobSummaries[].{name:TrainingJobName,status:TrainingJobStatus,instance:ResourceConfig.InstanceType,created:CreationTime}'
```

## Pre-flight commands

```bash
# Execution role check:
aws iam simulate-principal-policy \
  --policy-source-arn <execution-role-arn> \
  --action-names s3:GetObject s3:PutObject kms:Decrypt kms:GenerateDataKey ecr:BatchGetImage \
  --resource-arns '["arn:aws:s3:::<input-bucket>/*","arn:aws:s3:::<output-bucket>/*","arn:aws:kms:<region>:<account>:key/<key-id>","arn:aws:ecr:<region>:<account>:repository/<repo>"]' \
  --query 'Results[].{action:EvalActionName,decision:EvalDecision}'

# Instance quota:
aws service-quotas get-service-quota \
  --service-code sagemaker \
  --quota-code L-<quota-code-for-instance>

# S3 input accessibility:
aws s3api list-objects-v2 --bucket <input-bucket> --prefix <input-prefix> --max-items 1

# VPC:
aws ec2 describe-subnets --subnet-ids <subnet-ids>
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc-id>

# Warm pool:
aws sagemaker list-warm-pools \
  --query 'WarmPoolResources[?ResourceConfig.InstanceType==`<instance-type>`]'
```
