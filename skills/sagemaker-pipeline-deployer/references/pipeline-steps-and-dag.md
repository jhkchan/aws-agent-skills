# Pipeline Steps and the DAG Model — SageMaker Pipeline Deployer

Deep reference on SageMaker Pipeline step types (Processing, Training,
Tuning, CreateModel, Condition, Transform, RegisterModel, Fail), the DAG
dependency model (implicit via property references, explicit via
DependsOn), parameter passing between steps, and parallelism
configuration. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## The DAG model

A pipeline is a directed acyclic graph (DAG). Each node is a step. Each
edge represents a dependency: "step B cannot start until step A has
completed (and B wants to read A's output)."

Two mechanisms create edges:

### Implicit edges via property references

When a downstream step reads an upstream step's `properties`, SageMaker
adds an edge automatically.

```python
train = TrainingStep(
    name="Train",
    inputs=[TrainingInput(
        s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri
    )],
)
# Edge: Train → depends on → Preprocess
```

This is the preferred mechanism because it both orders the steps AND
wires the data flow.

### Explicit edges via DependsOn

When no property flows but execution order still matters:

```python
from sagemaker.workflow.steps import DependsOn

deploy = ConditionalOrOtherStep(
    name="Deploy",
    ...
    depends_on=[approval_step],
)
```

### Cycle detection

A cycle in the declared edges is rejected at `pipeline.upsert()` with a
`ValidationException: Cycle detected in pipeline definition`. Common
cause: an upstream step references a downstream step's property by
mistake (e.g., copy-paste of a property path).

## Step type reference

### ProcessingStep

Runs a `Processor` (sklearn / Spark / custom) on a managed compute
instance. Used for preprocessing, postprocessing, evaluation, and any
script-based data work.

```python
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput, PropertyFile
from sagemaker.workflow.steps import ProcessingStep

processor = SKLearnProcessor(
    framework_version="1.2-1",
    role=execution_role,
    instance_type="ml.m5.xlarge",
    instance_count=1,
)

evaluation_report = PropertyFile(
    name="EvaluationReport",
    output_name="evaluation",
    path="evaluation.json",
)

evaluate = ProcessingStep(
    name="Evaluate",
    processor=processor,
    code="evaluate.py",
    inputs=[ProcessingInput(source=train.properties.ModelArtifacts.S3ModelArtifacts,
                            destination="/opt/ml/processing/model")],
    outputs=[ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/output")],
    property_files=[evaluation_report],
)
```

**Spark variant:** `PySparkProcessor` or `SparkProcessor` from
`sagemaker.spark.processing`. Set `instance_count > 1` for a Spark
cluster; the container ships with Spark pre-installed.

**EMR variant (newer):** `EMRStep` (in `sagemaker.workflow.emr`) launches
a transient EMR cluster as a pipeline step — useful when Spark
processing outgrows the SageMaker Spark container.

### TrainingStep

Runs a `TrainingJob` via an `Estimator` (built-in or custom algorithm).

```python
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.workflow.steps import TrainingStep
from sagemaker.image_uris import retrieve

xgb = retrieve(framework="xgboost", region=region, version="1.7-1")
estimator = Estimator(
    image_uri=xgb,
    role=execution_role,
    instance_count=2,
    instance_type="ml.m5.2xlarge",
    output_path=f"s3://{bucket}/models",
)

train = TrainingStep(
    name="Train",
    estimator=estimator,
    inputs={
        "train":      TrainingInput(s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri),
        "validation": TrainingInput(s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri),
    },
)
# Property exposed: train.properties.ModelArtifacts.S3ModelArtifacts
```

**Custom algorithm:** build a container that conforms to the SageMaker
training contract (reads channels from `/opt/ml/input/data/<channel>`,
writes model artifacts to `/opt/ml/model`), push to ECR, and pass the
image URI to `Estimator(image_uri=...)`.

### TuningStep

Runs a `HyperparameterTuner` that spawns N `TrainingJob`s in parallel.

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

# Best model S3 URI (consumed downstream)
best_uri = tuning.get_top_model_s3_uri(top_k=0, s3_bucket=bucket, prefix="tuning")
```

**Cost warning:** `max_jobs=20` runs up to 20 TrainingJobs.
`max_parallel_jobs=4` caps concurrency at 4. Each job is billed
independently. Use warm-up strategies (e.g., `warm_start_config`) to
reuse prior tuning results and cut cost.

### CreateModelStep

Creates a SageMaker Model object. Used as input to TransformStep and
to endpoint deployment (the latter typically outside the pipeline).

```python
from sagemaker.model import Model
from sagemaker.workflow.step_collections import CreateModelStep

model = Model(
    image_uri=xgb,
    model_data=train.properties.ModelArtifacts.S3ModelArtifacts,
    role=execution_role,
)
create_model = CreateModelStep(
    name="CreateModel",
    model=model,
    inputs=sagemaker.model.ModelInputs(instance_type="ml.m5.large"),
)
# Property exposed: create_model.properties.ModelName
```

**Note:** for custom algorithms, the serving image may differ from the
training image. Use a re-packaging step or use the same image if it
supports both modes.

### ConditionStep

Branches the DAG based on conditions evaluated at runtime.

```python
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.fail_step import FailStep

accuracy = JsonGet(
    step_name=evaluate.name,
    property_file=evaluation_report,
    json_path="metrics.accuracy.value",
)

condition_step = ConditionStep(
    name="CheckAUC",
    conditions=[ConditionGreaterThanOrEqualTo(left=accuracy, right=approval_threshold)],
    if_steps=[create_model, transform, register],
    else_steps=[FailStep(name="MetricMiss", error_message="AUC below threshold")],
)
```

**Important:** conditions are evaluated at EXECUTION time, not at
authoring time. The Python `if/else` flow does NOT apply. The DAG
itself branches based on resolved JsonGet values.

Available condition operators:
- `ConditionGreaterThanOrEqualTo(left, right)`
- `ConditionGreaterThan`
- `ConditionLessThanOrEqualTo`
- `ConditionLessThan`
- `ConditionEquals`
- `ConditionIn`
- `ConditionNot`

### TransformStep

Runs a batch `TransformJob` — no endpoint needed.

```python
from sagemaker.transformer import Transformer
from sagemaker.workflow.steps import TransformStep

transformer = Transformer(
    model_name=create_model.properties.ModelName,
    instance_type="ml.m5.large",
    instance_count=1,
    output_path=f"s3://{bucket}/batch-output",
)
transform = TransformStep(
    name="BatchScore",
    transformer=transformer,
    inputs=sagemaker.inputs.TransformInput(data=f"s3://{bucket}/batch-input"),
)
# Property exposed: transform.properties.TransformOutput.S3OutputPath
```

**Gotcha:** `model_name` references the CreateModelStep property. If
CreateModelStep is in a ConditionStep's `if_steps`, TransformStep must
also be in `if_steps` — referencing a skipped step is a DAG error.

### RegisterModelStep

Adds a versioned entry to a Model Package Group in the Model Registry.

```python
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.model_metrics import MetricsSource, ModelMetrics

model_metrics = ModelMetrics(
    model_statistics=MetricsSource(
        s3_uri=evaluate.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
        content_type="application/json",
    ),
)

register = RegisterModel(
    name="RegisterModel",
    estimator=estimator,
    model_data=train.properties.ModelArtifacts.S3ModelArtifacts,
    content_types=["application/json"],
    response_types=["application/json"],
    inference_instances=["ml.m5.large", "ml.t2.medium"],
    transform_instances=["ml.m5.large"],
    model_package_group_name="xgb-classifier-group",
    approval_status="PendingManualApproval",
    model_metrics=model_metrics,
)
```

See `references/registry-and-caching.md` for the approval workflow.

### FailStep

Explicitly fails the pipeline execution with a custom error message.
Pairs naturally with ConditionStep's `else_steps`.

```python
from sagemaker.workflow.fail_step import FailStep

fail = FailStep(
    name="MetricMiss",
    error_message="AUC below threshold; re-tune or inspect data drift",
)
```

## Parameter and property passing

### Parameters

Pipeline-scoped inputs declared once; overridable per execution.

```python
from sagemaker.workflow.parameters import (
    ParameterString, ParameterInteger, ParameterFloat, ParameterBoolean,
)

processing_instance_type = ParameterString(
    name="ProcessingInstanceType",
    default_value="ml.m5.xlarge",
)
training_instance_count = ParameterInteger(
    name="TrainingInstanceCount",
    default_value=1,
)
approval_threshold = ParameterFloat(
    name="ApprovalThreshold",
    default_value=0.9,
)
```

Override at execution time:

```bash
aws sagemaker start-pipeline-execution \
  --pipeline-name training-pipeline \
  --pipeline-parameters \
    Name="ProcessingInstanceType",Value="ml.m5.4xlarge" \
    Name="ApprovalThreshold",Value="0.92"
```

### Properties (step outputs)

Each step type exposes a different property set. See the per-step
sections above for the canonical properties.

### JsonGet

Extracts a scalar from a JSON property file produced by a prior step.
Required for ConditionStep's metric-based branching.

```python
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.properties import PropertyFile

# Option A: inline PropertyFile
accuracy = JsonGet(
    step_name=evaluate.name,
    property_file=PropertyFile(name="EvaluationReport", output_name="evaluation", path="evaluation.json"),
    json_path="metrics.accuracy.value",
)
```

The `json_path` follows JSONPath syntax. The referenced file must be
written by the upstream ProcessingStep to its declared output and
declared in the upstream step's `property_files`.

### ExecutionVariables

Read-only context about the current execution.

```python
from sagemaker.workflow.execution_variables import ExecutionVariables

execution_id = ExecutionVariables.PIPELINE_EXECUTION_ID
execution_time = ExecutionVariables.CURRENT_TIME
```

Useful for parameterizing output paths per execution (e.g.,
`s3://{bucket}/output/{execution_id}/`).

## ParallelismConfiguration

Caps concurrent step executions per pipeline execution. Default is 1.

```python
execution = pipeline.start(
    parallelism_config={"MaxParallelExecutionSteps": 5},
)
```

```bash
aws sagemaker start-pipeline-execution \
  --pipeline-name training-pipeline \
  --parallelism-configuration MaxParallelExecutionSteps=5
```

**Quota gotcha:** the account-level quotas (max concurrent TrainingJobs,
TransformJobs) cap total concurrency ACROSS all pipeline executions. If
the quota is 10 and two pipelines each set parallelism=8, only 10 jobs
run at any instant. Check quotas:

```bash
aws service-quotas get-service-quota \
  --service-code sagemaker \
  --quota-code L-CD7B9C7A  # Studio Kernels per user (example; check the right code)
```

## Common DAG pitfalls

### Pitfall 1: assumed ordering without edges

```python
# BAD: no edges — steps may run in any order
steps=[preprocess, train]   # train may start before preprocess finishes
```

**Fix:** wire property references or add `DependsOn`.

### Pitfall 2: cycle from copy-paste

```python
# BAD: train references evaluate, evaluate references train
evaluate_inputs = train.properties.ModelArtifacts.S3ModelArtifacts
train_inputs    = evaluate.properties.ProcessingOutputConfig.Outputs["..."].S3Output.S3Uri
# Cycle: Train → Evaluate → Train
```

**Fix:** verify each property reference direction. Edges must point
from downstream (consumer) to upstream (producer).

### Pitfall 3: referencing a skipped step

If `CreateModelStep` is in `ConditionStep.if_steps`, then
`TransformStep` (which reads `create_model.properties.ModelName`) must
also be in `if_steps`. Otherwise, on the else-branch, the DAG tries to
resolve an unrun step's property.

**Fix:** group all consumers of a conditionally-run step's properties
inside the same branch.

### Pitfall 4: parallelism vs account quota

`ParallelismConfiguration=5` does not override account quotas. If the
account quota is 3 concurrent TrainingJobs, only 3 run; the rest queue
silently.

**Fix:** verify quotas with `service-quotas` before raising
parallelism. Request quota increases for production pipelines.
