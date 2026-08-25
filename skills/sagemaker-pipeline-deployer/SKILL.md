---
name: sagemaker-pipeline-deployer
description: 'Defines Amazon SageMaker Pipelines for ML workflows with production defaults: step collection (ProcessingStep with sklearn/Spark container, TrainingStep with built-in or custom algorithm, TuningStep for hyperparameter optimization, CreateModelStep registering model artifacts, ConditionStep branching on metrics, TransformStep for batch inference, RegisterModelStep integrating with the Model Registry), StartPipelineExecution, parameter passing between steps via Properties, caching configuration (per-step cache key), parallelism configuration (ParallelismConfiguration), Pipeline as Code (SageMaker Python SDK vs JSON definition), and EventBridge-driven automated triggers. Emits a READY_TO_DEPLOY. Triggers: create sagemaker pipeline, sagemaker pipeline steps, sagemaker pipeline caching, sagemaker tuning step, sagemaker model register step, sagemaker condition step, sagemaker transform step, start pipeline execution, sagemaker pipeline parallelism, sagemaker pipeline eventbridge, sagemaker pipeline as code.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with sagemaker access and an IAM execution role that can be passed to underlying jobs. Works with SageMaker Python SDK (sagemaker.Pipeline / sagemaker.workflow steps), Terraform aws_sagemaker_pipeline / aws_sagemaker_pipeline_definition resources, and CloudFormation AWS::SageMaker::Pipeline templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, sagemaker, sagemaker-pipeline, cloudops, deploy, ml, mlops, model-registry, eventbridge, caching, dag
  dependencies: aws-orchestrator
  keywords: aws, sagemaker, pipeline, dag, cloudops, deploy, ml, processing step, training step, tuning step, hyperparameter optimization, condition step, transform step, model register step, model registry, caching, parallelism, eventbridge
  when_to_use: Invoke when the user wants to build or update an Amazon SageMaker Pipeline (the workflow orchestration service for ML), compose step collections (Processing, Training, Tuning, CreateModel, Condition, Transform, RegisterModel), wire parameters between steps via Properties, configure per-step caching or pipeline-wide parallelism, drive executions from EventBridge, or gate production deployment via the Model Registry approval workflow. Do NOT invoke for SageMaker Studio operations, single TrainingJob/TransformJob without a pipeline (use sagemaker-training-job-operator), real-time Endpoint deployment (use sagemaker-endpoint-deployer), or non-SageMaker orchestrators (Step Functions, Airflow).
---

# SageMaker Pipeline Deployer

An AWS CloudOps agent skill that defines Amazon SageMaker Pipelines with
correct defaults: the DAG model (steps as dependency-based execution),
the step collection (Processing, Training, Tuning, CreateModel,
Condition, Transform, RegisterModel), parameter passing via Properties,
per-step caching, parallelism configuration, Pipeline as Code, and
EventBridge-driven triggers. Emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create SageMaker Pipeline, SageMaker Pipeline steps, caching, Tuning
Step, Model Register Step, Condition Step, Transform Step,
StartPipelineExecution, Pipeline parallelism, Pipeline EventBridge,
Pipeline as Code.

## STRICT output contract

When this skill is invoked with a SageMaker Pipeline definition request
(create a pipeline, add steps, configure caching, drive execution from
EventBridge, branch on metrics, register a model version, or wire up a
partial pipeline), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `PIPELINE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface with prose, headings, or
disclaimers — emit the block as the first lines of the response. This
contract is what assertion-based evals and downstream provisioning
pipelines rely on; deviating from the literal labels breaks automation
silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Steps 1-3 | Core: DAG model, Pipeline as Code, parameter/property passing |
| Steps 4-10 | Step collection (Processing, Training, Tuning, CreateModel, Condition, Transform, RegisterModel) |
| Steps 11-13 | Caching, ParallelismConfiguration, EventBridge triggers |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/pipeline-steps-and-dag.md | Step + DAG detail |
| references/registry-and-caching.md | Registry + caching detail |

## Mindset

**One-line takeaway:** A SageMaker Pipeline is a DAG of steps. Steps
depend on each other via property references. Caching skips steps whose
inputs are unchanged, reducing cost. The Model Registry gates production
deployment via an approval workflow (`PendingManualApproval`).

Three misconceptions dominate SageMaker Pipeline misdesign:

- **"Steps run sequentially in declaration order."** They do NOT. Steps
  run as a DAG. Order is determined by dependencies declared via
  `DependsOn` or implicit dependencies from property references
  (`step.properties.<output>`). Two unrelated steps run in parallel (up
  to `ParallelismConfiguration`). A common bug is wiring a step that
  looks sequential but fires before its dependency because no property
  reference was declared.

- **"Caching means re-running the pipeline is free."** It does not.
  Caching reuses step outputs ONLY when the cache key is unchanged. The
  key is the step type plus arguments (input S3 URIs, instance
  type/count, algorithm image, hyperparameters). Cache misses re-run
  the step and re-bill.

- **"RegisterModel deploys the model."** It does NOT. `RegisterModel`
  creates a versioned entry in the Model Registry in
  `PendingManualApproval` status. Deployment to an endpoint is a
  SEPARATE action — a downstream CI/CD job calls
  `describe-model-package` on an Approved version, then `create-model`
  + `create-endpoint-config` + `create-endpoint`. Skipping the approval
  workflow loses the registry's safety guarantee.

## Configuration dependency graph (novel heuristic)
The full dependency table (execution-role PassRole trap, parameter immutability, per-step hard dependencies, cross-dependency gotchas): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand before wiring steps, parameters, or triggers.

## Expert heuristic: steps are a DAG, not a sequence
The DAG execution-plan diagram and the key implication (the steps list is a node collection, not a script): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when steps fire in the wrong order.

## Expert heuristic: caching reduces cost for unchanged steps
The cache-key formula (image digest vs tag, S3 input ETags) and invalidation gotchas: [references/registry-and-caching.md](references/registry-and-caching.md).
Load on demand when caching re-runs steps unexpectedly.

## Expert heuristic: model registry gates production deployment
The registry-driven deployment flow (PendingManualApproval -> review -> Approved -> CI/CD deploy): [references/registry-and-caching.md](references/registry-and-caching.md).
Load on demand when wiring approval gates.

## Prerequisites (verify before provisioning)

If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Pipeline execution role exists | Underlying jobs need a role | `aws iam get-role --role-name <role>` |
| Execution role trusts SageMaker | SageMaker must assume it | Trust policy includes `sagemaker.amazonaws.com` |
| `iam:PassRole` on child-job roles | Pipeline passes roles to jobs it launches | Check policy attached to execution role |
| S3 bucket for artifacts | Inputs/outputs need a home | `aws s3api head-bucket --bucket <bucket>` |
| ECR image (if custom algorithm) | Custom training/processing image | `aws ecr describe-images --repository-name <repo>` |
| Algorithm spec (if built-in) | Built-in algorithm URI | Confirm available in your region |
| Model Package Group (if RegisterModel) | Versions live in a group | `aws sagemaker describe-model-package-group` |
| EventBridge rule (if automated triggers) | Trigger needs a rule + target | `aws events describe-rule --name <rule>` |
| Account quotas for child jobs | Tuning/parallel steps spawn many jobs | `aws service-quotas get-service-quota --service-code sagemaker` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — DAG model and step dependencies

A pipeline is a DAG. Dependencies are declared two ways:

1. **Implicit via property reference.** Downstream step reads
   `upstream_step.properties.<output>` → SageMaker adds an edge.
2. **Explicit via `DependsOn=[upstream_step]`.** Use when no property
   flows but execution order must be enforced.

```python
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.inputs import TrainingInput

preprocess = ProcessingStep(name="Preprocess", ...)
train = TrainingStep(
    name="Train",
    inputs=[TrainingInput(
        s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri
    )],
)
# Edge: Train depends on Preprocess (implicit, via property ref)
pipeline = Pipeline(name="my-pipeline", parameters=[...],
                    steps=[preprocess, train])  # list order ≠ execution order
```

A cycle in the declared edges is rejected at `pipeline.upsert()` with a
`ValidationException`.

## Step 2 — Pipeline as Code (SageMaker Python SDK vs JSON definition)

| Path | When to use | Tooling |
|---|---|---|
| SageMaker Python SDK (`sagemaker.workflow`) | Default; type-safe; integrates with estimators/processors | `sagemaker.Pipeline(...).upsert()` then `start()` |
| JSON definition | Generated artifacts; Terraform; CI/CD templates | `aws sagemaker update-pipeline --pipeline-definition <file>` |

The Python SDK is the recommended authoring path. The JSON definition
is the wire format the API accepts. The SDK compiles to JSON on
`upsert()`:

```python
pipeline = Pipeline(
    name="training-pipeline",
    parameters=[processing_instance_type, training_instance_type, ...],
    steps=[preprocess, train, evaluate, condition_step, register],
    sagemaker_session=sess,
)
pipeline.upsert()                # creates or updates; emits JSON
json_def = pipeline.definition() # the JSON wire format
```

**Terraform** can manage the pipeline via `aws_sagemaker_pipeline`
(with `pipeline_definition` inline) or
`aws_sagemaker_pipeline_definition`. Terraform-managed pipelines must
NOT also be upserted from the SDK — the two will fight over the
definition.

## Step 3 — Parameter and property passing between steps

**Parameters** are pipeline-scoped inputs, declared once and overridable
at `StartPipelineExecution`:

```python
from sagemaker.workflow.parameters import ParameterString, ParameterInteger, ParameterFloat

processing_instance_type = ParameterString(name="ProcessingInstanceType", default_value="ml.m5.xlarge")
training_instance_count  = ParameterInteger(name="TrainingInstanceCount", default_value=1)
approval_threshold       = ParameterFloat(name="ApprovalThreshold", default_value=0.9)
```

**Properties** are step outputs downstream steps read:

| Step type | Property | Example use |
|---|---|---|
| ProcessingStep | `ProcessingOutputConfig.Outputs['<name>'].S3Output.S3Uri` | Preprocessed data → Training |
| TrainingStep | `ModelArtifacts.S3ModelArtifacts` | Model artifact → CreateModel/RegisterModel |
| TuningStep | `best_tuning_job_name`, `top_model_s3_uri()` | Best tuned model → CreateModel |
| TransformStep | `TransformOutput.S3OutputPath` | Batch predictions → register/condition |

**JsonGet** extracts a scalar from a JSON property file produced by a
prior step — the canonical way to read an evaluation metric for
ConditionStep:

```python
from sagemaker.workflow.functions import JsonGet

accuracy = JsonGet(
    step_name=evaluate_step.name,
    property_file=evaluation_report,   # PropertyFile pointing to evaluation.json
    json_path="metrics.accuracy.value",
)
```

## Step 4 — ProcessingStep (sklearn / Spark container)
Full ProcessingStep recipe (SKLearnProcessor inputs/outputs, Spark variant, EMRStep): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when authoring this step type.

## Step 5 — TrainingStep (built-in or custom algorithm)
Full TrainingStep recipe (Estimator with built-in xgboost image, channels from Processing properties, custom-ECR contract): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when authoring this step type.

## Step 6 — TuningStep (hyperparameter optimization)
Full TuningStep recipe (HyperparameterTuner ranges, objective, get_top_model_s3_uri, cost warning): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when authoring this step type.

## Step 7 — CreateModelStep (model artifact)
Full CreateModelStep recipe (Model object, ModelInputs, image-match note): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when authoring this step type.

## Step 8 — ConditionStep (branching based on metrics)
Full ConditionStep recipe (ConditionGreaterThanOrEqualTo on JsonGet, if_steps/else_steps with FailStep): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when authoring this step type.

## Step 9 — TransformStep (batch inference)
Full TransformStep recipe (Transformer wired to CreateModelStep property, batch gotcha): [references/pipeline-steps-and-dag.md](references/pipeline-steps-and-dag.md).
Load on demand when authoring this step type.

## Step 10 — RegisterModelStep (Model Registry integration)

```python
from sagemaker.workflow.step_collections import RegisterModel

register = RegisterModel(
    name="RegisterModel", estimator=estimator,
    model_data=train.properties.ModelArtifacts.S3ModelArtifacts,
    content_types=["application/json"], response_types=["application/json"],
    inference_instances=["ml.m5.large", "ml.t2.medium"],
    transform_instances=["ml.m5.large"],
    model_package_group_name="xgb-classifier-group",
    approval_status="PendingManualApproval",   # the gate
    model_metrics=model_metrics,
)
```

**Approval workflow (separate from register):**

```bash
# Approve a version (manual or CI/CD after review)
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:...:model-package/xgb-classifier-group/12 \
  --model-approval-status Approved

# CI/CD discovers Approved versions and deploys
aws sagemaker list-model-packages \
  --model-package-group-name xgb-classifier-group --approval-status Approved \
  --sort-by CreationTime --sort-order Descending
```

## Step 11 — Caching configuration

```python
pipeline = Pipeline(
    name="training-pipeline", parameters=[...], steps=[...],
    enable_caching=True,
    cache_execution_config={"Enabled": True, "MaxCacheWindowSize": "P30D"},
)
```

**Cache invalidation:** changing any step argument invalidates the cache
for that step only. Upstream invalidations propagate downstream (an
upstream re-run changes the S3 ETag of its output, which is part of the
downstream cache key). For iterative dev cycles, caching can cut cost
5-10x by skipping unchanged preprocessing.

## Step 12 — Parallelism configuration

`ParallelismConfiguration` caps concurrent step executions per pipeline
execution. Default is 1 (sequential).

```bash
aws sagemaker start-pipeline-execution \
  --pipeline-name training-pipeline \
  --parallelism-configuration MaxParallelExecutionSteps=5
```

**Quota gotcha:** account-level quotas (max concurrent TrainingJobs,
TransformJobs) cap total concurrency across ALL pipeline executions. If
the quota is 10 and two pipelines each set parallelism=8, only 10 jobs
run at any instant — the rest queue. Check with `service-quotas`.

## Step 13 — StartPipelineExecution + EventBridge triggers

```bash
# Manual start
aws sagemaker start-pipeline-execution \
  --pipeline-name training-pipeline \
  --pipeline-parameters Name="TrainingInstanceType",Value="ml.m5.2xlarge" \
  --parallelism-configuration MaxParallelExecutionSteps=3

# EventBridge-driven start (S3 PUT on new training data)
aws events put-rule \
  --name sagemaker-pipeline-on-new-data \
  --event-pattern '{
    "source": ["aws.s3"], "detail-type": ["Object Created"],
    "detail": {"bucket": {"name": ["my-ml-bucket"]}, "object": {"key": [{"prefix": "raw/"}]}}
  }'

aws events put-targets \
  --rule sagemaker-pipeline-on-new-data \
  --targets '[{"Id":"start-pipeline","Arn":"arn:aws:sagemaker:us-east-1:123456789012:pipeline/training-pipeline","RoleArn":"arn:aws:iam::123456789012:role/EventBridgeSageMakerInvoke"}]'
```

**Schedule trigger (cron):** `--schedule-expression "cron(0 2 * * ? *)"`.
**CodeCommit trigger:** EventBridge on `codecommit` reference updates, or
wire CodePipeline upstream. The invoke role must trust
`events.amazonaws.com` and allow `sagemaker:StartPipelineExecution`.

## Step 14 — Recent features
Recent AWS features 2023-2026 (pipeline_definition_config, FailStep, EMRStep, richer ModelMetrics, cache-key ETag improvements, InfrastructureConfig): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing step types or VPC config.

## NEVER do these things

1. **NEVER assume the steps list order is the execution order.** Steps
   run as a DAG. Wire dependencies via property references or
   `DependsOn`. Two unrelated steps may run in parallel.

2. **NEVER skip the execution-role `iam:PassRole` check.** The pipeline
   role must pass child-job roles to TrainingJobs and ProcessingJobs.
   Without it, execution fails on the first job launch.

3. **NEVER assume caching means re-runs are free.** Caching is per-step,
   keyed on arguments and S3 input ETags. Pin image references to
   digests (not `:latest` tags) to avoid stale-step bugs.

4. **NEVER assume RegisterModel deploys the model.** It creates a
   registry version in `PendingManualApproval`. Deployment happens
   after `UpdateModelPackage(ApprovalStatus=Approved)` via downstream
   CI/CD. Auto-approving defeats the gate.

5. **NEVER reference a step property from a branch that didn't run.**
   If CreateModelStep is in `if_steps`, TransformStep must be too.

6. **NEVER set `ParallelismConfiguration` above account quotas.**
   Account quotas cap total concurrent jobs across all pipelines.
   Excess steps queue silently — verify quotas first.

7. **NEVER mix Terraform-managed and SDK-upserted pipelines.** Pick
   one — `terraform apply` and `pipeline.upsert()` fighting over the
   definition produces drift and surprises.

8. **NEVER use image tags like `:latest` for cache-sensitive steps.**
   Use immutable tags (`:v1.4.2`) or digests (`@sha256:...`).

9. **NEVER forget the JsonGet property file when branching on metrics.**
   ConditionStep reads metrics via `JsonGet` from a `PropertyFile`
   pointing to JSON the prior step wrote. Without it, the condition
   errors.

10. **NEVER rely on EventBridge triggers without an invoke role.** The
    target needs `events.amazonaws.com` permission to call
    `sagemaker:StartPipelineExecution` via a role. Missing role = silent
    no-op trigger.

## Output format

```text
PIPELINE: <pipeline-name> (<pipeline-arn if known>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Execution role: <role-arn> (trusts sagemaker.amazonaws.com, iam:PassRole for child roles)
  [✓|✗] Pipeline parameters: <name=list>
  [✓|✗] Steps DAG: <step=list> (edges via property refs / DependsOn)
  [✓|✗] ProcessingStep: <name> (sklearn|spark|custom, instance=<type>)
  [✓|✗] TrainingStep: <name> (built-in|custom-ecr, instance=<type>x<count>)
  [✓|✗] TuningStep: <name> (max_jobs=<n>, max_parallel=<n>) | Not used
  [✓|✗] CreateModelStep: <name> (model_data via property ref)
  [✓|✗] ConditionStep: <name> (branch on <metric> <op> <threshold>; if_steps/else_steps)
  [✓|✗] TransformStep: <name> (batch input: s3://...) | Not used
  [✓|✗] RegisterModelStep: <name> (group: <group-name>, PendingManualApproval|Approved)
  [✓|✗] Caching: enabled (P30D) | disabled | ParallelismConfiguration: MaxParallelExecutionSteps=<n>
  [✓|✗] Trigger: manual | EventBridge rule <rule-name> (schedule|S3|CodeCommit)
  [✓|✗] Model Registry gate: enforced (PendingManualApproval) | bypassed (auto-approve)
VERIFICATION_COMMANDS:
  aws sagemaker describe-pipeline --pipeline-name <pipeline-name>
  aws sagemaker list-pipeline-executions --pipeline-name <pipeline-name>
  aws sagemaker describe-model-package-group --model-package-group-name <group>
  aws events describe-rule --name <rule-name>
```

### Worked example — end-to-end pipeline with conditional register

```text
PIPELINE: xgb-training-pipeline
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Execution role: arn:aws:iam::123456789012:role/SageMakerPipelineExecutionRole (PassRole on SageMakerExecutionRole)
  [✓] Pipeline parameters: ProcessingInstanceType, TrainingInstanceType, TrainingInstanceCount, ApprovalThreshold
  [✓] Steps DAG: Preprocess → Train → Evaluate → CheckAUC → [CreateModel, Transform, RegisterModel] | else → FailStep
  [✓] ProcessingStep: Preprocess (sklearn 1.2-1, ml.m5.xlarge)
  [✓] TrainingStep: Train (built-in xgboost 1.7-1, ml.m5.2xlarge x2)
  [✓] ConditionStep: CheckAUC (JsonGet metrics.accuracy.value ≥ 0.9)
  [✓] TransformStep: BatchScore (input s3://my-ml-bucket/batch-input)
  [✓] RegisterModelStep: RegisterModel (group: xgb-classifier-group, PendingManualApproval)
  [✓] Caching: enabled (window: P30D) | ParallelismConfiguration: MaxParallelExecutionSteps=3
  [✓] Trigger: EventBridge rule sagemaker-pipeline-on-new-data (S3 PUT raw/)
  [✓] Model Registry gate: enforced (PendingManualApproval)
VERIFICATION_COMMANDS:
  aws sagemaker describe-pipeline --pipeline-name xgb-training-pipeline
  aws sagemaker list-pipeline-executions --pipeline-name xgb-training-pipeline
  aws sagemaker describe-model-package-group --model-package-group-name xgb-classifier-group
  aws events describe-rule --name sagemaker-pipeline-on-new-data
```

## Error handling
All seven error deep dives (cycle detected, iam:PassRole on first job, JsonGet unresolved, cache re-runs, RegisterModel never deploys, EventBridge fires but pipeline does not execute, parallelism vs quotas): [references/error-handling.md](references/error-handling.md).
Load on demand on the first execution failure.

## References (load on demand)

- [Pipeline steps and DAG](references/pipeline-steps-and-dag.md) — configuration dependency graph, DAG-not-a-sequence heuristic, full step recipes for Processing/Training/Tuning/CreateModel/Condition/Transform
- [Registry and caching](references/registry-and-caching.md) — caching cache-key heuristic and the model-registry approval-gate heuristic
- [Advanced patterns](references/advanced-patterns.md) — recent AWS features (2023-2026)
- [Error handling](references/error-handling.md) — deep dives: cycle detection, iam:PassRole, JsonGet resolution, cache misses, RegisterModel gate, EventBridge triggers, parallelism vs quotas

## Domain

AWS CloudOps / Amazon SageMaker Pipeline Definition & ML Workflow Orchestration.

## AWS documentation

- **SageMaker Pipelines overview** — https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html
- **Build and manage pipelines** — https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-build.html
- **Step types reference** — https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html
- **Caching** — https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-caching.html
- **Model Registry** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html
- **StartPipelineExecution** — https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_StartPipelineExecution.html
- **ParallelismConfiguration** — https://docs.aws.amazon.com/sagemaker/latest/dg/run-pipeline.html#run-pipeline-parallelism
- **EventBridge triggers** — https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-event-driven.html
- **Python SDK** — https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/index.html
