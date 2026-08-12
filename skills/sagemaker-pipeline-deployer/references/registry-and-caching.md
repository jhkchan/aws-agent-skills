# Model Registry and Caching — SageMaker Pipeline Deployer

Deep reference on the SageMaker Model Registry (Model Package Groups,
RegisterModel step, PendingManualApproval gate, approval workflow,
downstream CI/CD deployment) and Pipeline caching (cache-key
composition, opt-in via enable_caching, MaxCacheWindowSize, image-tag-
vs-digest gotchas, EventBridge triggers for automated execution).
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Model Registry fundamentals

### What the Registry is

The Model Registry is a versioned catalog of ML models. Each model
lives as a "version" inside a "Model Package Group." Each version
carries:

- The model artifact URI (S3 path to `model.tar.gz`)
- The inference image URI
- Model metrics (data quality, model quality, bias, explainability)
- An approval status: `PendingManualApproval`, `Approved`, or
  `Rejected`

The approval status is the gate between experimentation and production.

### Creating a Model Package Group

```bash
aws sagemaker create-model-package-group \
  --model-package-group-name xgb-classifier-group \
  --model-package-group-description "XGBoost binary classifier, prod candidates"
```

The first `RegisterModel` step can also implicitly create the group, but
explicit creation lets you set description and tags upfront.

### Registering a version via RegisterModel step

```python
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.model_metrics import MetricsSource, ModelMetrics

model_metrics = ModelMetrics(
    model_statistics=MetricsSource(
        s3_uri=evaluate.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
        content_type="application/json",
    ),
    bias=MetricsSource(
        s3_uri=f"s3://{bucket}/bias/report.json",
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

### Approval workflow

By default, new versions are `PendingManualApproval`. Approving or
rejecting is a separate API call (manual or CI/CD).

```bash
# Approve version N
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:123456789012:model-package/xgb-classifier-group/12 \
  --model-approval-status Approved \
  --approval-description "AUC=0.94 on holdout, bias checks passed"

# Reject version N
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:123456789012:model-package/xgb-classifier-group/12 \
  --model-approval-status Rejected \
  --approval-description "AUC regression vs v11"
```

### Discovering Approved versions

```bash
aws sagemaker list-model-packages \
  --model-package-group-name xgb-classifier-group \
  --approval-status Approved \
  --sort-by CreationTime --sort-order Descending \
  --max-results 1
```

### Deploying an Approved version (CI/CD pattern)

The pipeline registers; a SEPARATE CI/CD job deploys Approved versions.
The pipeline does not deploy.

```bash
# 1. Find the latest Approved version
VERSION_ARN=$(aws sagemaker list-model-packages \
  --model-package-group-name xgb-classifier-group \
  --approval-status Approved \
  --sort-by CreationTime --sort-order Descending \
  --max-results 1 \
  --query 'ModelPackageSummaryList[0].ModelPackageArn' --output text)

# 2. Describe it to get the inference image and model artifact
DESCRIBE=$(aws sagemaker describe-model-package --model-package-name "$VERSION_ARN")
IMAGE=$(echo "$DESCRIBE" | jq -r '.InferenceSpecification.Containers[0].Image')
MODEL_DATA=$(echo "$DESCRIBE" | jq -r '.InferenceSpecification.Containers[0].ModelDataUrl')

# 3. Create the model
MODEL_NAME="xgb-classifier-$(date +%s)"
aws sagemaker create-model \
  --model-name "$MODEL_NAME" \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole \
  --primary-container Image="$IMAGE",ModelDataUrl="$MODEL_DATA"

# 4. Create endpoint config + endpoint
aws sagemaker create-endpoint-config \
  --endpoint-config-name "$MODEL_NAME-config" \
  --production-variants VariantName=prod,ModelName="$MODEL_NAME",InstanceType=ml.m5.large,InitialInstanceCount=1

aws sagemaker create-endpoint \
  --endpoint-name xgb-classifier-prod \
  --endpoint-config-name "$MODEL_NAME-config"
```

### EventBridge on approval

```bash
# Fire when a version is approved
aws events put-rule \
  --name sagemaker-model-approved \
  --event-pattern '{
    "source": ["aws.sagemaker"],
    "detail-type": ["SageMaker Model Package State Change"],
    "detail": {"ModelApprovalStatus": ["Approved"]}
  }'

aws events put-targets \
  --rule sagemaker-model-approved \
  --targets '[{"Id": "trigger-cicd", "Arn": "arn:aws:codepipeline:...:my-deploy-pipeline", "RoleArn": "arn:aws:iam::...:role/EventBridgeInvokeCodePipeline"}]'
```

## Caching fundamentals

### Opt-in

Caching is OFF by default. Enable at pipeline creation time:

```python
pipeline = Pipeline(
    name="training-pipeline",
    parameters=[...],
    steps=[...],
    enable_caching=True,
    cache_execution_config={
        "Enabled": True,
        "MaxCacheWindowSize": "P30D",  # ISO 8601 duration; max P30D
    },
)
```

`MaxCacheWindowSize` caps how old a prior run can be to be reused.
Maximum is 30 days (`P30D`).

### Cache-key composition

The cache key for each step is derived from:

```text
cache_key = hash(
    step_type,            # Processing / Training / Tuning / ...
    arguments,            # inputs, hyperparameters, code S3 path
    instance_type,
    instance_count,
    image_uri,            # the URI string as written
    algorithm_spec,
    input_s3_etags,       # ETag of each S3 input object (NOT the URI alone)
    environment,
)
```

**What invalidates the cache:**
- Changing any hyperparameter value
- Changing instance type or count
- Changing an S3 input's ETag (i.e., the object's content changed)
- Changing the image URI string

**What does NOT invalidate the cache (gotchas):**
- Changing the contents of a code tarball at a stable S3 URI without
  changing the ETag — this can't happen because S3 ETag changes when
  the content changes. So S3-referenced code is safe.
- Pushing a new container image to the same tag (e.g.,
  `my-image:latest`). The URI string is identical, so the cache key
  matches and a STALE step result is served. **Always pin to digests**
  (`my-image@sha256:...`) or to immutable, version-bumped tags
  (`my-image:v1.4.2`) for cache-sensitive steps.

### Cache reuse behavior

When a step's cache key matches a prior successful run within the
window, SageMaker reuses the prior output and the step shows status
`Cached` instead of re-executing. The output artifacts (S3 paths) are
the same. Downstream steps that depend on cached outputs also reuse
their outputs if their cache keys match.

```bash
aws sagemaker describe-pipeline-execution \
  --pipeline-execution-arn arn:aws:sagemaker:... \
  --query 'PipelineExecutionStatus'

aws sagemaker list-execution-steps \
  --pipeline-execution-arn arn:aws:sagemaker:... \
  --query 'PipelineExecutionSteps[*].{Step:Metadata.StepName,Status:Metadata.StepStatus}'
# Cached steps show StepStatus: Cached
```

### Forcing a cache bypass

To force a re-run, override a parameter or pass `--pipeline-execution-description`
plus a `--client-request-token` (it doesn't bust the cache by itself,
but changes to parameter values do). The clean way is to bump a
parameter value intentionally.

```bash
aws sagemaker start-pipeline-execution \
  --pipeline-name training-pipeline \
  --pipeline-parameters Name="ForceCacheBust",Value="$(date +%s)"
```

(Only works if `ForceCacheBust` is a declared Parameter that's
referenced in some step's arguments.)

## Cost implications

Caching is the single biggest cost reducer for iterative ML
development. Typical patterns:

- **Iterative hyperparameter tuning:** the preprocessing step is
  expensive (Spark on a large dataset) and rarely changes. Caching
  skips it on every re-run that only changes training hyperparameters.
  Cost reduction of 5-10x is common.

- **Production re-runs:** if raw data hasn't changed, caching skips
  preprocessing AND training. The pipeline completes in minutes
  instead of hours, at near-zero compute cost.

- **Parallel dev teams:** multiple data scientists iterating on
  different steps benefit from shared cache within the same pipeline.

## EventBridge-driven execution

### S3 PUT trigger

```bash
aws events put-rule \
  --name sagemaker-pipeline-on-new-data \
  --event-pattern '{
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {
      "bucket": {"name": ["my-ml-bucket"]},
      "object": {"key": [{"prefix": "raw/"}]}
    }
  }'

aws events put-targets \
  --rule sagemaker-pipeline-on-new-data \
  --targets '[{
    "Id": "start-pipeline",
    "Arn": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/training-pipeline",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSageMakerInvoke"
  }]'
```

### Schedule (cron) trigger

```bash
aws events put-rule \
  --name sagemaker-pipeline-nightly \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

aws events put-targets \
  --rule sagemaker-pipeline-nightly \
  --targets '[{
    "Id": "start-pipeline",
    "Arn": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/training-pipeline",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSageMakerInvoke"
  }]'
```

### CodeCommit trigger

Use EventBridge on `codecommit` reference-updated events, or wire
CodePipeline as the upstream that invokes SageMaker StartPipelineExecution.

### Invoke role trust policy

The invoke role must trust `events.amazonaws.com` and allow
`sagemaker:StartPipelineExecution`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sagemaker:StartPipelineExecution",
      "Resource": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/*"
    }
  ]
}
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Principal": {"Service": "events.amazonaws.com"}, "Action": "sts:AssumeRole"}
  ]
}
```

## Terraform example

```hcl
resource "aws_sagemaker_pipeline" "training" {
  pipeline_name = "training-pipeline"
  role_arn      = aws_iam_role.sagemaker_pipeline.arn

  pipeline_definition = jsonencode({
    Version = "2020-12-01"
    # ... Steps, Parameters, etc. (matches the JSON definition
    # produced by sagemaker.Pipeline.definition())
  })
}

resource "aws_sagemaker_model_package_group" "xgb" {
  model_package_group_name = "xgb-classifier-group"
  model_package_group_description = "XGBoost binary classifier"
}
```

**Warning:** do NOT mix Terraform-managed pipelines with SDK-upserted
pipelines. Pick one tool to own the pipeline definition.
