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

Pipeline configurations are NOT independent. A step consuming a property
from an upstream step depends on that step. The Model Registry depends
on a model artifact from Training/Tuning. EventBridge triggers operate
at the pipeline level, not per-step.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Pipeline execution role | Role exists; trusts `sagemaker.amazonaws.com`; has `iam:PassRole` for child-job roles | Without `iam:PassRole`, underlying TrainingJob/ProcessingJob fail to launch | All steps that create child jobs |
| Pipeline name | Globally unique within account+region; 1-256 chars | Cannot be renamed; must delete + re-create | The pipeline itself |
| Parameters | Pipeline-scoped; default must satisfy type | Cannot be re-typed; defaults are immutable | Override at StartPipelineExecution |
| ProcessingStep | Execution role; container image; S3 inputs/outputs | Without `Properties` reference, downstream can't read outputs | Preprocessing output feeds Training |
| TrainingStep | Algorithm spec (built-in or custom ECR URI); channels | `S3ModelArtifacts` is the property downstream steps consume | Model artifact feeds CreateModel / RegisterModel |
| TuningStep | Tuner config (objective, ranges, max jobs) | `BestTrainingJob` available only after tuning completes; runs N child jobs (cost) | Best model feeds CreateModel |
| CreateModelStep | Model artifacts from Training/Tuning | Image URI must match training image or be re-packaged | Model object for Transform / Endpoint |
| ConditionStep | Conditions reference `JsonGet` from a prior step's output | Branch selection at execution time, not creation time | Sub-branches run only if condition holds |
| TransformStep | Model object; batch input S3 URI; instance type | Without batch input the step runs but scores nothing | Batch predictions to S3 |
| RegisterModelStep | Model artifact; model package group (or auto-created) | New versions default to `PendingManualApproval` | Approval gate; downstream CI/CD deploys Approved |
| Caching (enable_caching) | Set on Pipeline creation | Cache key per step; arg changes invalidate only that step | Cost reduction on re-runs |
| ParallelismConfiguration | Integer ≥1; quota-aware | Default is 1 (sequential at top level even with independent steps) | Multiple branches run concurrently |
| EventBridge rule | Pipeline ARN; rule target = `sagemaker` StartPipelineExecution | Without the rule, manual invoke only | Automated triggers (S3 PUT, schedule, CodeCommit) |

**The execution-role-PassRole row is the one a baseline model misses.**
A pipeline that defines a TrainingStep needs the pipeline's execution
role to call `iam:PassRole` on the TrainingJob's role. Without that,
creation succeeds but execution fails on the first job-launching step.

**Cross-dependency gotchas:**
- A property reference is the ONLY way to chain an upstream output into
  a downstream input without an explicit `DependsOn`. Without either,
  steps run in undeclared order.
- TuningStep's `BestTrainingJob` is available only AFTER tuning
  completes; downstream CreateModel must reference it via
  `tuning_step.get_top_model_s3_uri()`, NOT a hardcoded S3 path.
- `ParallelismConfiguration` caps concurrency PER pipeline execution.
  Account-level quotas cap concurrency ACROSS all executions — hitting
  the account quota serializes steps even with parallelism=5.

## Expert heuristic: steps are a DAG, not a sequence

A baseline model strings steps into a list and assumes the list order is
the execution order. The correct heuristic: SageMaker builds a DAG from
declared dependencies.

```text
Pipeline execution plan (DAG):

  ProcessingStep (preprocess)
        │  properties: ProcessingOutputConfig → S3 train/val URIs
        ▼
  TrainingStep (train)         ← depends on ProcessingStep via property ref
        │  properties: S3ModelArtifacts
        ▼
  ConditionStep (check metric) ← depends on TrainingStep via JsonGet(metric)
      ├── if accuracy ≥ threshold:
      │     ├── CreateModelStep → TransformStep (batch)
      │     └── RegisterModelStep (registry, PendingManualApproval)
      └── else: FailStep (re-tune or alert)
```

**Key implication:** the `steps=[...]` list is NOT a script. It's a node
collection. Edges are added by property references and `DependsOn`. Two
nodes with no path between them are eligible to run in parallel.

## Expert heuristic: caching reduces cost for unchanged steps

Caching is opt-in (`enable_caching=True` on `Pipeline`). The cache key
per step is derived from:

```text
cache_key = hash(
    step_type, arguments, instance_type, instance_count,
    image_uri,           # for image-by-tag: tag string only (NOT digest!)
    algorithm_spec,
    input_s3_etags,      # ETag of each S3 input object
)
```

**Gotcha:** when an image is referenced by tag (`my-image:latest`), the
tag string is part of the key — not the underlying digest. A push of a
new image to the same tag does NOT invalidate the cache. Pin to
*digests* (`my-image@sha256:...`) or bump the tag on every code change.
Changing a hyperparameter value also invalidates; use pipeline
Parameters for values you expect to sweep.

## Expert heuristic: model registry gates production deployment

The Model Registry is the gate between experimentation and production.
`RegisterModel` adds a version to a Model Package Group in
`PendingManualApproval` status. Production deployment pipelines query
for `Approved` versions and deploy only those.

```text
Registry-driven deployment flow:

  1. Pipeline runs RegisterModel → creates version N (PendingManualApproval)
  2. Model reviewer evaluates version N (offline metrics, bias, drift)
     ├── approve → UpdateModelPackage(ApprovalStatus=Approved)
     └── reject  → UpdateModelPackage(ApprovalStatus=Rejected)
  3. CI/CD polls for Approved versions, or EventBridge fires on approval
  4. CI/CD calls describe-model-package → create-model → create-endpoint
```

**Key implication:** registering a model is NOT deploying it. The
approval workflow is the safety gate. Auto-approving defeats it — only
do this for non-production stages.

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

```python
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.workflow.steps import ProcessingStep

processor = SKLearnProcessor(
    framework_version="1.2-1", role=execution_role,
    instance_type=processing_instance_type, instance_count=1,
)
preprocess = ProcessingStep(
    name="Preprocess", processor=processor, code="pipelines/preprocess.py",
    inputs=[ProcessingInput(source=f"s3://{bucket}/raw", destination="/opt/ml/processing/input")],
    outputs=[
        ProcessingOutput(output_name="train", source="/opt/ml/processing/output/train"),
        ProcessingOutput(output_name="validation", source="/opt/ml/processing/output/validation"),
    ],
)
```

**Spark variant:** `PySparkProcessor` / `SparkProcessor`. Set
`instance_count>1` for a Spark cluster. For very large Spark workloads,
consider the newer `EMRStep` in Pipelines.

## Step 5 — TrainingStep (built-in or custom algorithm)

```python
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.workflow.steps import TrainingStep
from sagemaker.image_uris import retrieve

xgb_image = retrieve(framework="xgboost", region=region, version="1.7-1")
estimator = Estimator(
    image_uri=xgb_image, role=execution_role,
    instance_count=training_instance_count,
    instance_type=training_instance_type,
    output_path=f"s3://{bucket}/models",
    hyperparameters={"max_depth": 6, "eta": 0.2, "objective": "binary:logistic"},
)
train = TrainingStep(
    name="Train", estimator=estimator,
    inputs={
        "train":      TrainingInput(s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri),
        "validation": TrainingInput(s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri),
    },
)
```

**Custom algorithm:** push to ECR; image must conform to the SageMaker
training container contract (reads `/opt/ml/input/data/<channel>`,
writes `/opt/ml/model`).

## Step 6 — TuningStep (hyperparameter optimization)

```python
from sagemaker.tuner import HyperparameterTuner, ContinuousParameter, IntegerParameter
from sagemaker.workflow.steps import TuningStep

tuner = HyperparameterTuner(
    estimator=estimator,
    objective_metric_name="validation:auc",
    objective_type="Maximize",
    metric_definitions=[{"Name": "validation:auc", "Regex": "auc: ([0-9\\.]+)"}],
    hyperparameter_ranges={
        "max_depth": IntegerParameter(3, 10),
        "eta":       ContinuousParameter(0.05, 0.4),
    },
    max_jobs=20,
    max_parallel_jobs=4,
)
tuning = TuningStep(name="Tune", tuner=tuner, inputs={...})

# Downstream: best model via get_top_model_s3_uri (NOT a hardcoded S3 path)
best_model_uri = tuning.get_top_model_s3_uri(top_k=0, s3_bucket=bucket, prefix="tuning")
```

**Cost warning:** `max_jobs=20` spawns up to 20 TrainingJobs. Account
quotas cap concurrency across all pipelines.

## Step 7 — CreateModelStep (model artifact)

```python
from sagemaker.model import Model
from sagemaker.workflow.step_collections import CreateModelStep

model = Model(image_uri=xgb_image,
              model_data=train.properties.ModelArtifacts.S3ModelArtifacts,
              role=execution_role)
create_model = CreateModelStep(
    name="CreateModel", model=model,
    inputs=sagemaker.model.ModelInputs(instance_type="ml.m5.large"),
)
```

**Note:** the model image URI must match the training image (built-ins)
or be a compatible serving image (custom) — a mismatch is a runtime
failure at first inference.

## Step 8 — ConditionStep (branching based on metrics)

```python
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.fail_step import FailStep

cond = ConditionGreaterThanOrEqualTo(left=accuracy, right=approval_threshold)
condition_step = ConditionStep(
    name="CheckAUC", conditions=[cond],
    if_steps=[create_model, transform, register],
    else_steps=[FailStep(name="MetricMiss", error_message="AUC below threshold")],
)
```

**Important:** conditions evaluate at EXECUTION time using `JsonGet`
values resolved from the prior step's property file. They are NOT Python
`if` statements — the DAG itself branches at runtime.

## Step 9 — TransformStep (batch inference)

```python
from sagemaker.transformer import Transformer
from sagemaker.workflow.steps import TransformStep

transformer = Transformer(
    model_name=create_model.properties.ModelName,
    instance_type="ml.m5.large", instance_count=1,
    output_path=f"s3://{bucket}/batch-output",
)
transform = TransformStep(
    name="BatchScore", transformer=transformer,
    inputs=sagemaker.inputs.TransformInput(data=f"s3://{bucket}/batch-input"),
)
```

**Gotcha:** `model_name` references the CreateModelStep property. If
CreateModelStep is in a ConditionStep's `if_steps`, TransformStep must
also be there — referencing a skipped step is a DAG error.

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

**Recent AWS features (2023-2026):**

- **Pipeline definition config (2023-2024):** `pipeline_definition_config`
  lets you manage the JSON definition as an artifact for CI/CD diffs.
- **FailStep (2023-2024):** dedicated step type for explicit failure
  with custom error message. Replaces raising in a processing script.
- **EMRStep in Pipelines (2023-2024):** launches a transient EMR cluster
  as a step — for Spark workloads beyond the SageMaker Spark container.
- **Richer ModelMetrics (2023-2024):** data quality, model quality,
  bias, explainability metrics surface in Studio and inform approval.
- **Cache-key digest improvements (2024-2025):** SageMaker clarified
  cache-key includes S3 object ETags (not just URIs), closing the
  source-tarball-at-stable-path loophole.
- **InfrastructureConfig (2024-2025):** declarative VPC config on
  Pipeline (instead of per-estimator `subnets` / `security_group_ids`).

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

### Pipeline creation fails with `ValidationException: Cycle detected`
- A circular dependency exists in the step edges. Inspect every
  `DependsOn` and property reference. Common cause: an upstream step
  references a downstream step's property.

### Execution fails with `iam:PassRole` error on first job
- The pipeline execution role lacks permission to pass the child-job
  role. Add `iam:PassRole` on the child role ARN to the pipeline role.

### ConditionStep errors with `Unable to resolve JsonGet`
- The property file was not produced. Verify the upstream step writes a
  `PropertyFile` with the expected name and the `json_path` matches.

### Caching re-runs steps unexpectedly
- The cache key changed. Common cause: image referenced by `:latest`
  whose content changed but tag did not; S3 input ETag changed;
  hyperparameter drifted. Pin images to digests and parameterize
  values you intend to sweep.

### RegisterModel creates versions but never deploys
- RegisterModel is the gate, not the deployer. Approval is a separate
  `UpdateModelPackage(ApprovalStatus=Approved)` call. CI/CD must poll
  or be EventBridge-triggered on approval, then deploy.

### EventBridge rule fires but pipeline never executes
- The target's invoke role lacks `sagemaker:StartPipelineExecution` or
  its trust policy doesn't allow `events.amazonaws.com`.

### ParallelismConfiguration=5 but steps still serialize
- The account quota caps total concurrency across ALL pipelines. Check
  `aws service-quotas get-service-quota --service-code sagemaker`.

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
