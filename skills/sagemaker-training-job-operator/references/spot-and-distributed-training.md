# Spot and distributed training — deep reference

This reference expands the SKILL.md spot training and distributed
training sections with the interruption model, SMDDP / SMDMP
configuration, checkpoint patterns, and Training Compiler
integration. Load when configuring spot or distributed training.

## Spot training interruption model

### How SageMaker spot training works

1. SageMaker requests spot capacity for the configured instance type.
2. When spot is available, the job starts (`TrainingJobStatus:
   InProgress`, `SecondaryStatus: Training`).
3. If AWS reclaims the capacity, SageMaker receives a 2-minute
   interruption notice.
4. SageMaker stops the training container; the framework's
   checkpoint at `/opt/ml/checkpoints` is synced to S3.
5. SageMaker attempts to re-acquire spot capacity (within
   `MaxWaitTimeInSeconds`).
6. When capacity returns, SageMaker relaunches the job; the
   framework loads the checkpoint from S3 and resumes.

### Key timing parameters

| Parameter | Default | Effect |
|---|---|---|
| `MaxRuntimeInSeconds` | Required | Per-attempt training budget (single training cycle) |
| `MaxWaitTimeInSeconds` | Required for spot | Wall-clock budget including interruptions + retries; must be >= `MaxRuntimeInSeconds` |
| `CheckpointConfig.LocalPath` | Required for spot | Framework checkpoint path; SageMaker syncs this to S3 |
| `SpotTimeoutInSeconds` (create via API) | 300 | Grace period for the framework to save state before container stop |

### Spot training failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Job runs but never resumes after interruption | `CheckpointConfig` missing or `LocalPath` does not match framework save path | Set `CheckpointConfig`; verify framework saves to `LocalPath` |
| Job restarts from epoch 0 every time | Framework does not load checkpoint at start | Add `torch.load(checkpoint_path)` at the start of training |
| `MaxWaitTimeInSeconds` exceeded | Capacity did not return within the wall-clock budget | Increase `MaxWaitTimeInSeconds`; consider on-demand fallback |
| Spot capacity never available | Instance type has limited spot pool | Use `ml.p4de.24xlarge` (more spot availability) or on-demand |

### Spot training cost savings

Spot training typically saves 70-90% versus on-demand. The actual
savings depend on the interruption frequency and the checkpoint
restore time. For jobs that checkpoint every epoch, the effective
cost is:

```
effective_cost = (training_hours + interruption_overhead) * spot_rate
```

Where `interruption_overhead` is the time spent re-running epochs
since the last checkpoint. Frequent checkpointing (every N steps,
not just every epoch) minimizes this overhead for long epochs.

## Distributed training — SMDDP

### When to use SMDDP

- Model fits in single-GPU memory but training is too slow.
- Multi-instance / multi-GPU training with data parallelism.
- Recommended for transformer and CV models on P4d / P4de / P5.

### SMDDP configuration

| Hyperparameter | Meaning | Example |
|---|---|---|
| `sagemaker_distributed_dataparallel_enabled` | Enable SMDDP | `true` |
| `sagemaker_distributed_dataparallel_num_processes` | Total GPU count across all instances | `32` for 4 × `ml.p5.48xlarge` |
| `sagemaker_distributed_dataparallel_num_processes_per_host` | GPUs per instance | `8` for `ml.p5.48xlarge` (auto-detected if omitted) |
| `sagemaker_distributed_dataparallel_custom_mpi_options` | Additional MPI flags | `"-XNCCL_DEBUG=WARN"` |

### Framework integration (PyTorch)

```python
import smdistributed.dataparallel.torch.torch_smddp  # Import before use
import torch.distributed as dist

# SMDDP initializes the process group automatically:
dist.init_process_group("smddp")

# Use SMDDP's DistributedDataParallel wrapper:
from torch.nn.parallel import DistributedDataParallel
model = DistributedDataParallel(model, device_ids=[local_rank])

# Standard PyTorch training loop:
for batch in dataloader:
    loss = model(batch)
    loss.backward()
    optimizer.step()
```

SMDDP provides optimized all-reduce for AWS instance topologies
(NVLink within instance, EFA across instances). On P5, SMDDP v2
uses H100 NVLink for near-linear scaling.

### Common SMDDP misconfigurations

| Misconfiguration | Symptom | Fix |
|---|---|---|
| `num_processes` set to instance count (e.g., 4) | Only 1 GPU per instance used; training 8x slower | Set `num_processes` to total GPU count (e.g., 32 for 4 × P5) |
| `FullyReplicated` data distribution | Each instance trains on full dataset | Use `ShardedByS3Key` |
| Framework not calling `torch_smddp` import | Silent fallback to native DDP | Import `smdistributed.dataparallel.torch.torch_smddp` before any torch.distributed use |
| Missing `EnableSageMakerTrainingCompiler` on transformer model | 20-50% slower training | Enable Training Compiler on supported images |

## Distributed training — SMDMP

### When to use SMDMP

- Model exceeds single-GPU memory (e.g., 70B+ parameter models on
  P5 / P4de).
- Pipeline parallelism + tensor parallelism needed.
- Recommended for large language models that do not fit on one GPU.

### SMDMP configuration

```bash
--hyper-parameters '{
  "sagemaker_distributed_modelparallel_enabled": true,
  "sagemaker_mp_parameters": "pipeline_parallel_degree=2;tensor_parallel_degree=4;microbatches=4",
  ...
}'
```

| Parameter | Meaning |
|---|---|
| `pipeline_parallel_degree` | Number of pipeline stages |
| `tensor_parallel_degree` | Number of devices for tensor parallelism within each pipeline stage |
| `microbatches` | Number of microbatches for pipeline scheduling |

The product of `pipeline_parallel_degree` × `tensor_parallel_degree`
must divide evenly into the total GPU count.

### SMDMP configuration matrix (4 × ml.p5.48xlarge = 32 GPUs)

| `pipeline_parallel_degree` | `tensor_parallel_degree` | Total devices used | Remaining for data parallel |
|---|---|---|---|
| 2 | 4 | 8 | 4 (data parallel degree) |
| 4 | 2 | 8 | 4 |
| 2 | 8 | 16 | 2 |
| 4 | 8 | 32 | 1 |
| 8 | 4 | 32 | 1 |

### Framework integration (PyTorch)

SMDMP requires using the `smdistributed.modelparallel` library to
partition the model. See the AWS docs for the full integration
pattern; the key primitives are `smp.partition`, `smp.DistributedModel`,
and `smp.step`.

## Training Compiler

### What Training Compiler does

Training Compiler is an automatic compilation pass that optimizes
GPU kernels for transformer models. It fuses operations, optimizes
memory layout, and reduces kernel launch overhead. Typical speedup:
20-50% on transformer training (BERT, GPT, T5).

### When to enable

| Use case | Enable Training Compiler? |
|---|---|
| Transformer model on P4d / P4de / P5 | Yes — significant speedup |
| Non-transformer model (CNN, RNN) | No — minimal benefit |
| Trainium (Trn1) | No — Trainium uses its own compiler (Neuron) |
| Unsupported framework version | No — fallback or failure |

### Supported versions matrix (2025-2026)

Check the [Training Compiler supported versions matrix](https://docs.aws.amazon.com/sagemaker/latest/dg/training-compiler-support.html)
for the current list. As of 2026, supported combinations include:
- PyTorch 2.0 - 2.3 (GPU images)
- TensorFlow 2.11 - 2.15 (GPU images)
- HuggingFace Transformers 4.30+ (on PyTorch GPU images)

### Configuration

```bash
--algorithm-specification '{
  "TrainingImage": "<pytorch-gpu-image>",
  "TrainingInputMode": "FastFile",
  "EnableSageMakerTrainingCompiler": true
}'
```

### Training Compiler failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `ClientError: ... training compiler error` | Unsupported framework / image version | Check the supported versions matrix; use a non-compiler image |
| Job launches but Training Compiler does not appear active | Image supports compiler but model architecture is not supported | Check CloudWatch logs for "Training Compiler enabled" vs "skipped" |
| OOM with Training Compiler | Compiler's memory optimization expects a specific model structure | Reduce batch size; verify model follows the expected transformer structure |

## EFA and network configuration

For multi-instance distributed training, EFA (Elastic Fabric Adapter)
is critical for high-throughput, low-latency inter-instance
communication. P4d, P4de, and P5 instances include EFA devices.

```bash
# Verify EFA is available on the instance:
aws ec2 describe-instance-types --instance-types ml.p5.48xlarge \
  --query 'InstanceTypes[0].NetworkInfo.EfaSupported'

# Security group must allow all inbound/outbound between instances
# (SageMaker manages the EFA security group automatically when
# VpcConfig is specified).
```

On P5, EFA v2 (400 Gbps) is included. SageMaker automatically
configures the EFA devices when `VpcConfig` is specified for a
distributed training job.

## Checkpoint patterns for spot + distributed

For distributed training with spot, each rank should checkpoint
independently. On resume, SMDDP restores the process group and each
rank loads its own checkpoint.

```python
# Each rank saves its own state:
checkpoint_path = f"/opt/ml/checkpoints/rank_{dist.get_rank()}/checkpoint.pt"
torch.save({
    "epoch": epoch,
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
    "rng_state": torch.get_rng_state(),
}, checkpoint_path)

# On resume, each rank loads its own checkpoint:
if os.path.exists(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    torch.set_rng_state(checkpoint["rng_state"])
    start_epoch = checkpoint["epoch"] + 1
```

This pattern ensures that spot interruptions during distributed
training do not require all ranks to restart from scratch — each
rank resumes from its own last checkpoint.
