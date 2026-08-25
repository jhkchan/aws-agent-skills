# Advanced Patterns — SageMaker Training Job Operator

Expert-knowledge deep dives, heuristics, and recent-feature notes moved out of the SKILL.md body. Loaded on demand.


## Expert edge cases

These patterns represent genuine, non-obvious SageMaker training job
behaviours that a senior operator would catch but a generalist would
miss.

### P5 and Trn1 default to zero quota

`ml.p5.48xlarge` (8 × H100) and `ml.trn1.32xlarge` (32 × Trainium)
default to a Service Quota of zero. Launching one without a prior
quota request produces `Failed` with `ClientError: ... instances
could not be provisioned`. Always run
`aws service-quotas get-service-quota` for the instance type; if the
quota is zero, request an increase via the Service Quotas console
before launching. P5 and Trn1 increases may require AWS account-team
approval — plan weeks ahead.

### Spot interruption without checkpoint = full restart

`EnableManagedSpotTraining: true` without `CheckpointConfig` works
technically but is practically useless — each interruption restarts
from epoch 0. The entry point must save/load checkpoints at the
configured `LocalPath`; SageMaker handles the S3 sync automatically.
Set `MaxWaitTimeInSeconds` >> `MaxRuntimeInSeconds` to budget for
multiple interruptions.

### SMDDP `num_processes` is total GPUs, not instance count

For 4 × `ml.p5.48xlarge` (8 GPUs each), `num_processes` = 32, not 4.
Setting it to 4 underutilizes 7 of 8 GPUs per instance — the job
appears to run but trains 8x slower than expected. Cross-reference
CloudWatch logs for "World size" to confirm.

### Training Compiler requires specific framework versions

`EnableSageMakerTrainingCompiler: true` works only on supported
PyTorch / TensorFlow / HuggingFace images. An unsupported image
launches without compilation (silent), or fails with
`ClientError: ... training compiler error`. Always check the
[Training Compiler supported versions matrix](https://docs.aws.amazon.com/sagemaker/latest/dg/training-compiler-support.html).
Training Compiler is most beneficial on GPU instances (P4d, P4de, P5)
for transformer models.

### Warm pools bill while idle

A `WarmPoolConfig` with `KeepAlivePeriodInSeconds: 3600` keeps the
cluster alive for an hour after the source job completes — billed at
the full instance rate. For P5 (H100), this is significant. Always
clean up warm pools with `delete-warm-pool` when the work sequence
ends. Use warm pools only when sequential jobs share the same
instance type and image; otherwise the warm pool is wasted.

### `EnableNetworkIsolation` requires VPC endpoints for S3 and ECR

`--enable-network-isolation` blocks outbound internet. The job can
still reach S3 (input/output) and ECR (image pull) only via VPC
endpoints (S3 Gateway or Interface, ECR Interface, plus the ECR DKR
endpoint). Without these endpoints, an isolated job cannot pull the
image or read inputs — the failure is misleading
("image not found"). For private model registries (HuggingFace,
internal), without isolation + NAT, you also need a NAT gateway or
VPC endpoint to the registry.

### `VolumeKmsKeyId` and `OutputDataConfig.KmsKeyId` are separate

The volume KMS key (EBS attached to the instance) and the output KMS
key (model artifacts in S3) are separate. A role with `kms:Decrypt`
on the volume key but not the output key produces a failure during
the upload phase (`InProgress` / `Uploading` → `Failed`). The role
needs `kms:Decrypt` and `kms:GenerateDataKey` on both keys.

### `AlgorithmSpecification` `TrainingInputMode` choice matters

`File` mode downloads the dataset to EBS before training — fine for
small datasets, slow for large. `FastFile` streams via FUSE without
downloading — better for large datasets with small per-object
overhead. `Pipe` mode streams from Kinesis or augmented manifest.

### Training plan management (capacity reservation, 2025-2026)

For P5 / Trn1 capacity-constrained launches, a **training plan**
reserves instance capacity in advance. Create a plan via
`aws sagemaker create-training-plan`, then reference it from
`create-training-job` via `--training-plan-config`. The plan
guarantees capacity at the scheduled time — eliminating
`insufficient capacity` failures. Plans are billed at the reserved
rate regardless of whether the job runs.

## Expert heuristic — "Pre-check the execution role and the quota before anything else"

The single most common SageMaker training job failure is an
execution role missing a permission (S3, KMS, ECR) or an instance
quota being zero (P5, Trn1). These failures surface within seconds
of launch as `Failed` with a terse `FailureReason`. Always run
`iam simulate-principal-policy` and `service-quotas get-service-quota`
before launching.

Quick lookup table for common failure reasons:

| `FailureReason` substring | Root cause | Pre-check that catches it |
|---|---|---|
| `unauthorized S3 access` | Role missing S3 permission | `iam simulate-principal-policy` for `s3:GetObject` / `s3:PutObject` |
| `image not found` | Wrong ECR URI or role lacks `ecr:BatchGetImage` | `ecr describe-images` + `iam simulate-principal-policy` for `ecr:BatchGetImage` |
| `instances could not be provisioned` | Quota exhausted or AWS capacity | `service-quotas get-service-quota` |
| `CUDA error` or `out of memory` | Image/instance mismatch or batch too large | Cross-reference image to instance type; reduce batch size |
| `connection timed out` | VPC missing endpoint or NAT | `ec2 describe-vpc-endpoints` |
| `KMS access denied` | Role lacks KMS permission | `iam simulate-principal-policy` for `kms:Decrypt` |
| `training compiler error` | Unsupported framework/image version | Check Training Compiler supported versions matrix |

When in doubt, run `aws sagemaker describe-training-job` and read
the `FailureReason` verbatim — it usually names the specific
permission or capacity issue.

## Recent AWS features (2024-2026)

- **SageMaker P5 and P5e instances (H100, 2024-2025):**
  `ml.p5.48xlarge` (8 × H100 80GB) and `ml.p5e.48xlarge` (8 × H100
  141GB). Default quota is zero — request via Service Quotas.
- **SageMaker Training Compiler (GA, 2024-2025):** automatic GPU
  kernel optimization for transformer training. Enable via
  `EnableSageMakerTrainingCompiler: true` on supported PyTorch /
  TensorFlow / HuggingFace images. Most beneficial on P4d / P4de / P5.
- **Training plan management (2025-2026):** capacity reservations
  for P5 / Trn1. Create via `create-training-plan`, reference from
  `create-training-job` via `--training-plan-config`. Eliminates
  `insufficient capacity` failures for a reservation fee.
- **Warm pools GA (2024-2025):** `WarmPoolConfig` with
  `KeepAlivePeriodInSeconds` (max 3600). Reuses the cluster across
  sequential jobs with matching instance type and image.
- **SageMaker Distributed Data Parallel v2 (2024-2025):** improved
  all-reduce on P5 (H100 NVLink). Set via
  `sagemaker_distributed_dataparallel_enabled: true` and
  `num_processes` = total GPU count.
- **SageMaker Distributed Model Parallel (2024-2025):** pipeline +
  tensor parallel for models exceeding single-GPU memory. Configure
  via `sagemaker_distributed_modelparallel_enabled: true` with
  `pipeline_parallel_degree`, `tensor_parallel_degree`, `microbatches`.
- **Model registry approval workflows (enhanced 2024-2025):**
  `ModelApprovalStatus` gates deployment; integrates with
  EventBridge for auto-deployment on approval.
- **Automatic model tuning warm starts (enhanced 2024-2025):**
  `WarmStartType: IdenticalDataAndAlgorithm` (strict) and
  `TransferLearning` (permissive) carry tuning learnings.
- **`FastFile` mode GA (2024):** streams S3 objects via FUSE without
  downloading — useful for large datasets where `File` mode is slow.
