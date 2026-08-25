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
Full single-instance create-training-job CLI (algorithm spec, input channels, resource config, hyperparameters, VPC config, network isolation): [references/job-creation-procedures.md](references/job-creation-procedures.md).
Load on demand when emitting the launch command.

#### 2b. Spot training with checkpointing
Full spot-training CLI (CheckpointConfig S3Uri + LocalPath, managed spot, MaxWaitTime vs MaxRuntime budget): [references/job-creation-procedures.md](references/job-creation-procedures.md).
Load on demand when configuring spot training.

#### 2c. Distributed training (SMDDP)
Full SMDDP distributed CLI (sagemaker_distributed_dataparallel_enabled, num_processes, Training Compiler flag, SMDMP degrees): [references/job-creation-procedures.md](references/job-creation-procedures.md).
Load on demand when launching distributed training.

#### 2d. Warm pool (reuse across sequential jobs)
Full warm-pool source/target job pair CLI (KeepAlivePeriodInSeconds, WarmPoolConfig PoolName): [references/job-creation-procedures.md](references/job-creation-procedures.md).
Load on demand when reusing clusters across jobs.

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
Full create-hyper-parameter-tuning-job CLI (tuning job config, parameter ranges, early stopping, warm start): [references/job-creation-procedures.md](references/job-creation-procedures.md).
Load on demand when launching HPO.

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
The nine expert edge cases (P5/Trn1 zero quota, spot without checkpoint, num_processes semantics, Training Compiler versions, warm-pool idle billing, network-isolation endpoints, dual KMS keys, TrainingInputMode choice, training plans): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a job fails for a non-obvious reason.

## Expert heuristic — "Pre-check the execution role and the quota before anything else"
The full heuristic with the FailureReason lookup table (unauthorized S3, image not found, capacity, CUDA/OOM, connection timeout, KMS, compiler error): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when triaging a Failed job.

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
Recent AWS features 2024-2026 (P5/P5e, Training Compiler GA, training plans, warm pools GA, SMDDP v2, SMDMP, registry approval workflows, warm starts, FastFile): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when selecting instances or input modes.

## References

See `references/job-creation-procedures.md` for the full
per-operation CLI playbook (single-instance, spot, distributed,
warm pool, HPO, model registration) with worked examples, and
`references/spot-and-distributed-training.md` for the spot training
interruption model, SMDDP/SMDMP configuration, checkpoint patterns,
and Training Compiler integration.

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — expert edge cases, the pre-check-role-and-quota heuristic with the FailureReason lookup table, recent AWS features (2024-2026)
- [Job creation procedures](references/job-creation-procedures.md) — full per-operation CLI playbook: single-instance, spot, distributed (SMDDP), warm pool, HPO, model registration
- [Spot and distributed training](references/spot-and-distributed-training.md) — spot interruption model, SMDDP/SMDMP configuration, checkpoint patterns, Training Compiler integration

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
