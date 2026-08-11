---
name: operate-sagemaker-training-job
description: >-
  Slash command for the sagemaker-training-job-operator skill.
  Operates Amazon SageMaker training jobs end-to-end — job
  creation (algorithm spec, input data S3 channels, output S3,
  instance type, volume size, hyperparameters), spot training
  (SpotInstanceConfig with checkpointing S3), distributed
  training (multi-GPU, multi-instance, SageMaker Distributed
  Data Parallel and Model Parallel), warm pools (reuse
  provisioned instances across sequential jobs), automatic
  model tuning (HPO with warm starts), and model artifacts
  (register-model, model registry versioning). Covers SageMaker
  Training Compiler, P5 instances (H100), and training plan
  management. Runs deterministic pre-checks (instance quota,
  image existence, S3 input access, KMS, IAM role, VPC, warm
  pool availability), executes behind a CONFIRM gate, and
  emits READY | BLOCKED | COMPLETED with the exact CLI sequence
  and post-verification.
skill: sagemaker-training-job-operator
family: AI/ML
task_type: operate
verdict_shape: "READY | BLOCKED | COMPLETED"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:operate-sagemaker-training-job

Invoke the `sagemaker-training-job-operator` skill to plan or execute
a SageMaker training job operation.

Read the skill at
`skills/sagemaker-training-job-operator/SKILL.md` and follow its
procedure to plan and execute the operation.

## When to use

- Launch a single-instance training job (CPU or GPU).
- Launch spot training with checkpointing
  (`EnableManagedSpotTraining` + `CheckpointConfig`).
- Launch distributed training with SageMaker Distributed Data
  Parallel (`sagemaker_distributed_dataparallel_enabled`) or Model
  Parallel (`sagemaker_distributed_modelparallel_enabled`).
- Configure warm pools to reuse instances across sequential jobs.
- Launch a hyperparameter tuning (HPO) job with optional warm start.
- Register a trained model in the model registry
  (`create-model`, `create-model-package`).
- Resolve a `BLOCKED` training job (quota, image, S3, KMS, VPC,
  warm pool).
- Select the correct instance type (P5 / P5e H100, P4de A100, G5,
  Trn1) and Training Compiler configuration.

## Invocation

```
/aws:operate-sagemaker-training-job <job name / operation / symptom>
```

The skill will:

1. Capture the operation target (operation type, job name, region,
   algorithm spec, input/output S3, instance type, hyperparameters,
   execution role).
2. Run pre-flight: `iam simulate-principal-policy` on the role,
   `service-quotas get-service-quota` for the instance type,
   S3 accessibility, VPC configuration, warm pool availability.
3. Emit the launch CLI sequence with all flags populated (spot,
   distributed, warm pool, HPO as applicable).
4. Monitor `TrainingJobStatus` and `SecondaryStatus` via
   `describe-training-job` and `aws sagemaker wait
   training-job-completed-or-stopped`.
5. On `Completed`, verify `ModelArtifacts.S3ModelArtifacts` and
   optionally register the model in the model registry.
6. On `Failed`, read `FailureReason` and cross-reference CloudWatch
   logs.
7. Emit the standard VERDICT block.

## Output shape

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

## Pre-flight

The skill requires the operation type, job name, region, and the
training job configuration (algorithm spec, input/output S3,
instance type, execution role). If only a partial configuration is
provided, the skill runs `aws sagemaker list-training-jobs` to
surface existing jobs, or emits `BLOCKED` with the list of missing
inputs for a new launch.

## References

- Skill: `skills/sagemaker-training-job-operator/SKILL.md`
- Reference: `skills/sagemaker-training-job-operator/references/job-creation-procedures.md`
- Reference: `skills/sagemaker-training-job-operator/references/spot-and-distributed-training.md`
- AWS docs: https://docs.aws.amazon.com/sagemaker/latest/dg/how-it-works-training.html
