---
name: sagemaker-training-job-operator
description: Operates Amazon SageMaker training jobs end-to-end — job creation (algorithm spec, input data S3 channels, output S3, instance type, volume size, hyperparameters), spot training (SpotInstanceConfig with checkpointing S3), distributed training (multi-GPU, multi-instance, SageMaker Distributed Data Parallel and Model Parallel), warm pools (reuse provisioned instances), automatic model tuning (HPO with warm starts), and model artifacts (register-model, model registry versioning). Covers SageMaker Training Compiler, P5 instances (H100), and training plan management. Runs deterministic pre-checks (instance quota, image existence, S3 input access, KMS, IAM role, VPC, warm pool availability), executes behind a CONFIRM gate, and emits READY | BLOCKED | COMPLETED with the exact CLI sequence and post-verification. Use when launching a training job, configuring spot/distributed training, setting up HPO, registering a model, or resolving a BLOCKED training job.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline plan classification works on a supplied job configuration. Live-account operations use aws sagemaker create-training-job, describe-training-job, stop-training-job, create-hyper-parameter-tuning-job, describe-hyper-parameter-tuning-job, create-model, create-model-package, describe-model-package-group, update-training-job (warm pools), aws service-quotas get-service-quota, and aws ec2 describe-instances...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Launching or operating a SageMaker training job (single-instance, spot, distributed, or warm-pool), configuring SageMaker Distributed Data Parallel or Model Parallel for multi-GPU / multi-instance training, setting up checkpoint S3 for spot recovery, launching an automatic model tuning (HPO) job with warm starts, registering a trained model in the model registry (register-model, create-model-package), resolving a BLOCKED training job (instance quota, image access, S3 permissions, VPC misconfiguration, warm pool capacity), or selecting the correct instance type (P5 / P5e H100, P4de A100, G5, Trn1) and Training Compiler configuration.
  when_not_to_use: SageMaker endpoint deployment or real-time inference (use the sagemaker-endpoint-deployer skill), SageMaker Studio or domain setup (use the sagemaker-studio operator), SageMaker audit and security posture (use the sagemaker-endpoint-auditor), or non-SageMaker training (EC2-based training, ECS, EKS).
  activation_triggers: SageMaker training job, create-training-job, spot training, SpotInstanceConfig, checkpoint S3, distributed training, SageMaker Distributed Data Parallel, SageMaker Distributed Model Parallel, warm pool, hyperparameter tuning, automatic model tuning, HPO, register-model, model registry, Training Compiler, P5 instance, H100 training, training plan, SageMaker training BLOCKED, training job Failed
  invocation_schema: 'Input: either (a) a training job configuration with the algorithm spec, input/output S3, instance type, hyperparameters, and optional spot/distributed/warm-pool/HPO settings, OR (b) a job-name + operation for live-account execution (launch, describe, stop, register-model). Output: a deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: SageMaker, training job, spot training, SpotInstanceConfig, checkpointing, distributed training, SageMaker Distributed Data Parallel, SageMaker Distributed Model Parallel, warm pools, hyperparameter optimization, HPO, automatic model tuning, model registry, register-model, Training Compiler, P5 instances, H100, training plan, capacity reservation, algorithm spec
  tags: sagemaker, ai-ml, operate, training, distributed-training, hpo, model-registry
---

# SageMaker Training Job Operator

## Activation

Activate this skill when the user reports a SageMaker training job
operation. Trigger phrases: "SageMaker training job",
"create-training-job", "spot training", "SpotInstanceConfig",
"checkpoint S3", "distributed training", "SageMaker Distributed Data
Parallel", "SageMaker Distributed Model Parallel", "warm pool",
"hyperparameter tuning", "automatic model tuning", "HPO",
"register-model", "model registry", "Training Compiler",
"P5 instance", "H100 training", "training plan", "SageMaker training
BLOCKED", "training job Failed".

## Mindset

**One-line takeaway:** a SageMaker training job is a container that
runs on a managed EC2 instance, reads input from S3, writes model
artifacts to S3, and emits CloudWatch logs — the operator's job is to
ensure the configuration is internally consistent (image matches
instance type, input channels are reachable, the execution role can
read/write S3 and KMS, the VPC has the right endpoints, and spot /
distributed / warm-pool settings are coherent) before launching, and
to monitor `SecondaryStatus` + `AlgorithmSpecification` until
`Completed`.

Five SageMaker realities shape every operation:

- **The execution role is the most common failure point.** SageMaker
  assumes the role you provide to read inputs from S3, write outputs
  to S3, pull the container image (if private), encrypt/decrypt with
  KMS, and (for VPC jobs) create ENIs. A missing `s3:GetObject` on
  the input bucket, `s3:PutObject` on the output bucket, or
  `kms:Decrypt` on the volume KMS key produces a `Failed` job within
  seconds. Always run pre-checks on the role before launching.

- **Instance type dictates image and framework compatibility.** A
  GPU image (e.g., the PyTorch GPU training container) requires a
  GPU instance (`ml.p3.*`, `ml.p4d.*`, `ml.p4de.*`, `ml.p5.*`,
  `ml.g4dn.*`, `ml.g5.*`). A CPU image requires a CPU instance
  (`ml.m5.*`, `ml.c5.*`, `ml.r5.*`). AWS Trainium (`ml.trn1.*`)
  requires the Neuron container. Mismatch produces a `Failed` job
  immediately. P5 (H100) and Trn1 (Trainium) also require Service
  Quota approval — the default quota is zero.

- **Spot training requires checkpointing to be useful.** Spot
  instances can be interrupted with 2 minutes' notice. Without
  checkpointing to S3, each interruption restarts the job from
  scratch. Configure both `EnableManagedSpotTraining: true` and
  `CheckpointConfig` (S3 URI + local path) — the framework
  (PyTorch / TensorFlow) must also load/save checkpoints at the
  configured path.

- **Distributed training configuration must match instance
  topology.** SageMaker Distributed Data Parallel (SMDDP) requires
  multiple GPUs across one or more instances.
  `smdistributed:dataparallel` is a `HyperParameters` entry, not a
  top-level field. SageMaker Distributed Model Parallel (SMDMP)
  requires `smdistributed:modelparallel` with explicit
  `pipeline_parallel_degree`, `tensor_parallel_degree`, and
  `microbatches`. The framework entry point must call SMDDP / SMDMP
  primitives correctly — misconfiguration produces a silent
  performance regression (training runs but uses only one GPU).

- **Warm pools persist the compute cluster between jobs.** A
  `WarmPoolConfig` keeps the cluster alive for a configurable
  `MaxIdleSeconds` (max 3600 seconds) after the previous job
  completes, so the next job starts in seconds rather than minutes.
  The next job must request the same instance type and image as the
  warm pool's source job — otherwise it falls back to a cold start.
  Warm pools are charged at standard instance rates while idle; they
  count against the warm-pool Service Quota (separate from
  training-job quota).

## Quick reference — operation to verdict

| Operation | Trigger condition | Verdict |
|---|---|---|
| **Launch training job** | All pre-checks passed; awaiting CONFIRM gate | `READY` |
| **Launch blocked** | Instance quota exhausted, image not found, S3 input inaccessible, role missing permissions, VPC misconfigured, warm pool capacity unavailable | `BLOCKED` |
| **Job in progress** | `TrainingJobStatus: InProgress`, `SecondaryStatus` reports training | `COMPLETED` once `TrainingJobStatus: Completed`; `BLOCKED` if `Failed` |
| **Job completed** | `TrainingJobStatus: Completed`, `ModelArtifacts.S3ModelArtifacts` populated, `TrainingTimeInSeconds` set | `COMPLETED` with artifact S3 path |
| **Job failed** | `TrainingJobStatus: Failed`, `FailureReason` populated | `BLOCKED` with the failure cause from `FailureReason` and CloudWatch logs |
| **Stop job** | `TrainingJobStatus: InProgress`, operator requests stop | `COMPLETED` once `TrainingJobStatus: Stopped` |
| **Register model** | Job `Completed`, operator requests model registry version | `READY` to `create-model-package` after pre-checks |
| **HPO launch** | Tuning config valid, base job pre-checks pass, warm start config (if any) valid | `READY` |
| **Warm pool reuse** | Source job `Completed`, target job instance type + image match, idle time < `MaxIdleSeconds` | `READY` (warm start) — otherwise cold start |

**Pre-check priority order (apply in this sequence, all must pass
for READY):**

1. **Execution role** — `iam simulate-principal-policy` for
   `s3:GetObject` on input, `s3:PutObject` on output, `kms:Decrypt`
   on KMS key, `ecr:BatchGetImage` if private image, plus the
   SageMaker-managed `AmazonSageMakerFullAccess` baseline.
2. **Instance quota** — `service-quotas get-service-quota` for
   `ml.<instance-type>` (P5, Trn1 default to zero — request an
   increase first).
3. **Image + instance compatibility** — GPU image requires GPU
   instance; Trainium image requires Trn1; Training Compiler
   requires a supported image and framework version.
4. **S3 input/output accessibility** — the role can read input, the
   input channels point at valid S3 prefixes, the output bucket
   exists and accepts writes.
5. **VPC configuration** (if specified) — subnets exist, security
   groups allow S3 (VPC endpoint or NAT) and ECR (VPC endpoint or
   NAT), KMS endpoint if KMS is used.
6. **Warm pool availability** (if `WarmPoolConfig` specified) — the
   source job's instance type and image match; the warm pool has
   not been reaped by `MaxIdleSeconds`.

## Quick navigation

- **Step 0** — Capture the operation target (job name, region,
  operation type, configuration).
- **Step 1** — Run pre-flight (role, quota, image, S3, VPC, warm
  pool).
- **Step 2** — Launch training job (single-instance, spot,
  distributed, warm pool).
- **Step 3** — Monitor `TrainingJobStatus` and `SecondaryStatus`
  until `Completed` or `Failed`.
- **Step 4** — Handle interruptions (spot, hard failure, log-driven
  debugging).
- **Step 5** — Launch HPO (hyperparameter tuning) with optional
  warm start.
- **Step 6** — Register the model artifact in the model registry
  (create-model, create-model-package).
- **Step 7** — Decide VERDICT (READY / BLOCKED / COMPLETED).
- **Step 8** — Post-completion cleanup (delete warm pool, log
  retention).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <launch-training-job | launch-spot | launch-distributed | launch-hpo | stop | register-model | describe | warm-pool>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <job-name, instance-type, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command — aws sagemaker wait training-job-completed-or-stopped>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
MODEL_ARTIFACT: <S3 URI of model.tar.gz, or N/A if not completed>
LOG_GROUP: <CloudWatch log group /aws/sagemaker/TrainingJobs>
CONFIRM: Before executing any state-changing CLI, emit and await
  operator approval: "CONFIRM: About to <operation> on <job> in
  <region>. Proceed? (yes/no)"
```

Do NOT omit any field. If a field is not applicable, write `N/A`
with a one-line reason.

## Process — Operation execution plan (apply in order)

### Step 0: Capture the operation target

Gather these inputs. Each downstream step branches on which is
present.

| Signal | Source | Why required |
|---|---|---|
| **Operation type** | User-provided | launch / stop / describe / register-model / launch-hpo |
| **Job name + region** | User-provided | All SageMaker calls need this; the name must be unique in the account-region |
| **Algorithm spec (image or algorithm ARN)** | User-provided | Drives the container that runs |
| **Input data config (S3 channels)** | User-provided | Each channel (train, test, validation) is an S3 prefix |
| **Output data config (S3)** | User-provided | Where model.tar.gz is written |
| **Instance type + volume size** | User-provided | Drives GPU/CPU image compatibility and quota check |
| **Hyperparameters** | User-provided | Framework entry point, batch size, learning rate, distributed config |
| **Execution role ARN** | User-provided | SageMaker assumes this role; must have S3/KMS/ECR permissions |
| **Optional: spot, distributed, warm pool, HPO** | User-provided | Each adds additional pre-checks |

If the user has not provided the job name or operation, emit
`VERDICT: BLOCKED` with the list of missing inputs and the discovery
command (`aws sagemaker list-training-jobs --status-equals InProgress`
or `Completed`).

### Step 1: Pre-flight (role, quota, image, S3, VPC, warm pool)

Run these checks before launch (skip for offline plan audit). The
canonical CLI sequence is in `references/diagnostic-commands.md` of
the references folder.

1. **Execution role** — `iam simulate-principal-policy` for
   `s3:GetObject` on input, `s3:PutObject` on output, `kms:Decrypt`
   on KMS key, `ecr:BatchGetImage` if private image.
2. **Instance quota** — `service-quotas get-service-quota` for the
   instance type. P5 / Trn1 default to zero — request an increase.
3. **S3 input/output** — `s3api list-objects-v2` on input prefix;
   verify output bucket accepts writes.
4. **VPC** — `ec2 describe-subnets` + `describe-vpc-endpoints`;
   confirm S3 / ECR endpoints or NAT gateway.
5. **Warm pool** — `sagemaker list-warm-pools` filtered by instance
   type; confirm `Status: Available` and source job matches.

**Pre-check failure → BLOCKED reasons:**

| Failure | Reason | Fix |
|---|---|---|
| `EvalDecision: implicitDeny` on `s3:GetObject` | Role cannot read input bucket | Attach an inline or managed policy granting `s3:GetObject` on `arn:aws:s3:::<input-bucket>/*` |
| `EvalDecision: implicitDeny` on `s3:PutObject` | Role cannot write output bucket | Attach `s3:PutObject` on `arn:aws:s3:::<output-bucket>/*` |
| `EvalDecision: implicitDeny` on `kms:Decrypt` | Role cannot use the volume/output KMS key | Attach `kms:Decrypt` and `kms:GenerateDataKey` on the KMS key ARN |
| Service Quota value `0` for P5 / Trn1 | Default quota is zero | Request a quota increase via the Service Quotas console; P5 / Trn1 may also require AWS approval |
| `NoSuchBucket` on input | Input bucket does not exist or is in another account without cross-account access | Confirm bucket name; add bucket policy granting the role read access |
| `VpcEndpoint State pending` | VPC endpoint not yet available | Wait for `available`; or use NAT gateway as fallback |
| `WarmPoolResources[]` empty for instance type | No warm pool of matching instance type / image exists | Either cold-start, or launch a warm-up job first |

### Step 2: Launch training job

#### 2a. Single-instance training

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

#### 2b. Spot training with checkpointing

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

The training entry point must save and load checkpoints at
`/opt/ml/checkpoints` (the `LocalPath`). On interruption, SageMaker
restores from the S3 checkpoint on the next launch. Set
`MaxWaitTimeInSeconds` >= `MaxRuntimeInSeconds` — `MaxWaitTime` is
the wall-clock budget (includes interruptions + retries), not just
training time.

#### 2c. Distributed training (SMDDP)

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
  --input-data-config '...' \
  --output-data-config '...' \
  --enable-managed-spot-training \
  --checkpoint-config '...'
```

SMDDP uses `sagemaker_distributed_dataparallel_enabled` and
`num_processes` (= total GPUs across all instances). On
`ml.p5.48xlarge` (8 GPUs each) × 4 instances, `num_processes=32`.
The entry point must use `smdistributed.dataparallel` PyTorch /
TensorFlow primitives.

For SMDMP (model parallel), use:
`"sagemaker_distributed_model_parallel_enabled":true` with
`pipeline_parallel_degree`, `tensor_parallel_degree`, and
`microbatches`.

#### 2d. Warm pool (reuse across sequential jobs)

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
```

`KeepAlivePeriodInSeconds` (max 3600) sets the idle lifetime after
the source job completes. The target job must match the source's
instance type, instance count, and image — otherwise it cold-starts.

### Step 3: Monitor job status

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
```

**Status transitions:**

- `InProgress` / `Starting` → cluster provisioning
- `InProgress` / `Downloading` → input data download (or FastFile mode streaming)
- `InProgress` / `Training` → training loop
- `InProgress` / `Uploading` → model artifacts upload to S3
- `Completed` → `ModelArtifacts.S3ModelArtifacts` populated
- `Failed` → `FailureReason` populated (read it verbatim; cross-reference CloudWatch logs)
- `Stopped` → operator-initiated stop completed
- `Stopping` → stop requested, in progress

### Step 4: Handle interruptions and failures

| Symptom | Cause | Resolution |
|---|---|---|
| `TrainingJobStatus: Failed`, `FailureReason: ClientError: ... insufficient capacity` | AWS could not provision the instance type (common for P5, Trn1) | Retry; consider a training plan (capacity reservation) or fall back to P4de |
| `Failed`, `FailureReason: ... unauthorized S3 access` | Execution role missing `s3:GetObject` on input | Attach the policy; relaunch |
| `Failed`, `FailureReason: ... image not found` | ECR image URI wrong, or role lacks `ecr:BatchGetImage` | Verify the image URI; attach the policy |
| `Failed`, `FailureReason: ... CUDA error` | CPU image on GPU instance, or GPU image on CPU instance | Match the image to the instance type |
| `Failed`, `FailureReason: ... out of memory` | Batch size too large for GPU memory; or `VolumeSizeInGB` too small for dataset | Reduce batch size; increase volume size |
| `Interrupted` (spot training) | Spot capacity reclaimed | Ensure `CheckpointConfig` is set; SageMaker auto-relaunches and resumes from checkpoint |
| `Failed`, `FailureReason: ... connection timed out` | VPC missing S3 endpoint or NAT | Add S3 VPC endpoint (Gateway type) or NAT gateway; verify security group allows outbound HTTPS |
| `Failed`, `FailureReason: ... training compiler error` | Framework / image version not supported by Training Compiler | Check the supported versions matrix; fall back to non-compiler image |

### Step 5: Launch HPO (hyperparameter tuning)

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
  --training-job-definition '{...}'  # AlgorithmSpecification, RoleArn, InputDataConfig, OutputDataConfig, ResourceConfig, StaticHyperParameters, StoppingCondition

# Warm start (carry learnings from a previous tuning job):
aws sagemaker create-hyper-parameter-tuning-job \
  --hyper-parameter-tuning-job-name <name>-warm \
  --warm-start-config '{"ParentHyperParameterTuningJobs":[{"HyperParameterTuningJobName":"<previous>"}],"WarmStartType":"IdenticalDataAndAlgorithm"}' \
  --hyper-parameter-tuning-job-config '...' --training-job-definition '...'
```

Monitor via `describe-hyper-parameter-tuning-job`; the best training
job is reported in `BestTrainingJob`. The full HPO CLI script is in
`references/job-creation-procedures.md`.

### Step 6: Register the model in the model registry

After the training job `Completed`, the registration flow is:
(1) `create-model` linking the artifact to an inference image;
(2) `create-model-package-group` (one-time per model lineage);
(3) `create-model-package` with `InferenceSpecification`,
    `ModelMetrics`, and `--approval-status PendingManualApproval`;
(4) `update-model-package --model-approval-status Approved` once the
    model passes review.

The full CLI script is in `references/job-creation-procedures.md`.
The model registry enables versioning, approval workflows, and
downstream deployment via the endpoint deployer skill.

### Step 7: Decide — READY vs BLOCKED vs COMPLETED

- **READY.** All pre-checks passed; the operation plan is complete
  and awaiting the CONFIRM gate. Output the exact CLI sequence.
- **BLOCKED.** One or more pre-checks failed (role, quota, image,
  S3, VPC, warm pool) OR a launched job entered `Failed` with a
  `FailureReason`. Output the specific blocker and the fix.
- **COMPLETED.** A launched job entered `Completed` with model
  artifacts populated, or a stop job entered `Stopped`, or a model
  package was registered successfully. Output the verification.

### Step 8: Post-completion cleanup

| Cleanup action | When | How |
|---|---|---|
| Delete warm pool | After the final job in a sequence | `aws sagemaker delete-warm-pool --warm-pool-id <id>` (warm pools are billed while idle) |
| Adjust log retention | After job completes | `aws logs put-retention-policy --log-group-name /aws/sagemaker/TrainingJobs --retention-in-days 30` |
| Delete failed jobs' artifacts | Periodically | `aws s3 rm s3://<output-bucket>/models/<failed-job>/ --recursive` |
| Release Training Plan | If a training plan was reserved | `aws sagemaker delete-training-plan --training-plan-name <name>` |

## Output format

```text
OPERATION: <launch-training-job | launch-spot | launch-distributed | launch-hpo | stop | register-model | describe | warm-pool>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <job-name, instance-type, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command>
  2. <wait command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
MODEL_ARTIFACT: <S3 URI of model.tar.gz, or N/A>
LOG_GROUP: /aws/sagemaker/TrainingJobs
```

### Worked example — launch distributed P5 training with SMDDP

See `examples/README.md` for a full worked example: a 4 ×
`ml.p5.48xlarge` (32-GPU) SMDDP launch with Training Compiler, VPC
isolation, and warm-pool handoff. The contract below applies.

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

## Anti-Patterns — NEVER

- **NEVER** launch a training job without first running
  `iam simulate-principal-policy` on the execution role for S3,
  KMS, and ECR permissions. Most `Failed` jobs are role-permission
  failures that surface within seconds.
- **NEVER** launch a P5 or Trn1 job without first checking the
  Service Quota. Both default to zero and require an increase
  request before launch.
- **NEVER** enable `EnableManagedSpotTraining` without
  `CheckpointConfig`. Without checkpointing, each spot interruption
  restarts from scratch.
- **NEVER** set `sagemaker_distributed_dataparallel_num_processes`
  to the instance count. It is the total GPU count across all
  instances (e.g., 32 for 4 × ml.p5.48xlarge).
- **NEVER** use `FullyReplicated` for SMDDP at scale. Use
  `ShardedByS3Key` so each instance receives a shard.
- **NEVER** leave a warm pool running after the work sequence ends.
  Warm pools bill at full instance rate while idle; call
  `delete-warm-pool` when done.
- **NEVER** mix a GPU image with a CPU instance (or vice versa).
  The job fails immediately with a CUDA error.
- **NEVER** use `--enable-network-isolation` without confirming S3
  and ECR VPC endpoints exist in the job's VPC. The job cannot pull
  the image or read inputs without them.
- **NEVER** assume `MaxRuntimeInSeconds` is the same as
  `MaxWaitTimeInSeconds` for spot jobs. `MaxWaitTime` is the
  wall-clock budget including interruptions; set it >> `MaxRuntime`.
- **NEVER** declare `COMPLETED` for a job without verifying
  `ModelArtifacts.S3ModelArtifacts` is populated and the S3 object
  exists. A `Completed` status without an artifact indicates a
  custom output configuration issue.
- **NEVER** register a model in the model registry without
  specifying `ModelApprovalStatus` (default `PendingManualApproval`
  is correct for safety, but the operator must know the model is
  not auto-deployable until approved).
- **NEVER** use `WarmStartType: IdenticalDataAndAlgorithm` when the
  dataset or algorithm has changed. Use `TransferLearning` instead.
- **NEVER** launch an HPO job without `TrainingJobEarlyStoppingType:
  Auto`. Without early stopping, weak candidates run to
  `MaxRuntimeInSeconds`, wasting budget.

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

## References

See `references/job-creation-procedures.md` for the full
per-operation CLI playbook (single-instance, spot, distributed,
warm pool, HPO, model registration) with worked examples, and
`references/spot-and-distributed-training.md` for the spot training
interruption model, SMDDP/SMDMP configuration, checkpoint patterns,
and Training Compiler integration.

## Domain

AWS CloudOps / AI-ML — Model Training Operations.

## AWS documentation

- **SageMaker training jobs** — https://docs.aws.amazon.com/sagemaker/latest/dg/how-it-works-training.html
- **Managed spot training** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-managed-spot-training.html
- **SageMaker Distributed Training** — https://docs.aws.amazon.com/sagemaker/latest/dg/distributed-training.html
- **Warm pools** — https://docs.aws.amazon.com/sagemaker/latest/dg/warm-pools.html
- **Automatic model tuning** — https://docs.aws.amazon.com/sagemaker/latest/dg/automatic-model-tuning.html
- **Model registry** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html
- **Training Compiler** — https://docs.aws.amazon.com/sagemaker/latest/dg/training-compiler.html
- **SageMaker P5 instances** — https://docs.aws.amazon.com/sagemaker/latest/dg/train-p5.html
- **Training plans** — https://docs.aws.amazon.com/sagemaker/latest/dg/training-plans.html
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/sagemaker/
