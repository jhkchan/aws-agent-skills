# End-to-End Example: SageMaker Pipeline Deployment

A walkthrough showing how to use the `sagemaker-pipeline-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are defining an end-to-end SageMaker Pipeline for XGBoost model
training with a conditional register gate. The pipeline needs:

- ProcessingStep "Preprocess" (sklearn 1.2-1, ml.m5.xlarge) — outputs
  train/validation datasets to S3
- TrainingStep "Train" (built-in XGBoost 1.7-1, ml.m5.2xlarge x2) —
  consumes Preprocess outputs via property references
- ProcessingStep "Evaluate" — writes evaluation.json
- ConditionStep "CheckAUC" — branches on accuracy >= 0.9
- if_steps: CreateModelStep, TransformStep, RegisterModelStep
- else_steps: FailStep
- Caching enabled (30-day window)
- ParallelismConfiguration MaxParallelExecutionSteps=3
- Triggered by EventBridge on S3 PUT to `raw/`
- Pipeline execution role:
  arn:aws:iam::123456789012:role/SageMakerPipelineExecutionRole

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-sagemaker-pipeline
```

Then paste the requirements.

### Option B: Natural language

```
You: "Build a SageMaker Pipeline named xgb-training-pipeline
      with sklearn preprocessing, XGBoost training, a conditional
      register on accuracy >= 0.9, caching, and EventBridge trigger
      on S3 PUT."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a sagemaker pipeline"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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
  [✓] Caching: enabled (window: P30D)
  [✓] ParallelismConfiguration: MaxParallelExecutionSteps=3
  [✓] Trigger: EventBridge rule sagemaker-pipeline-on-new-data (S3 PUT raw/)
  [✓] Model Registry gate: enforced (PendingManualApproval)
VERIFICATION_COMMANDS:
  aws sagemaker describe-pipeline --pipeline-name xgb-training-pipeline
  aws sagemaker list-pipeline-executions --pipeline-name xgb-training-pipeline
  aws sagemaker describe-model-package-group --model-package-group-name xgb-classifier-group
  aws events describe-rule --name sagemaker-pipeline-on-new-data
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the Model Package Group (if it doesn't exist)
aws sagemaker create-model-package-group \
  --model-package-group-name xgb-classifier-group \
  --model-package-group-description "XGBoost binary classifier, prod candidates"

# Step 2: Upsert the pipeline (Python SDK recommended)
# (run: python pipelines/upsert_pipeline.py — uses sagemaker.Pipeline.upsert())

# Step 3: EventBridge rule + target
aws events put-rule \
  --name sagemaker-pipeline-on-new-data \
  --event-pattern '{
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {"bucket": {"name": ["my-ml-bucket"]}, "object": {"key": [{"prefix": "raw/"}]}}
  }'

aws events put-targets \
  --rule sagemaker-pipeline-on-new-data \
  --targets '[{
    "Id": "start-pipeline",
    "Arn": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/xgb-training-pipeline",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSageMakerInvoke"
  }]'

# Step 4: Start a manual execution (or wait for S3 PUT trigger)
aws sagemaker start-pipeline-execution \
  --pipeline-name xgb-training-pipeline \
  --pipeline-execution-displayName "manual-run-2026-08-11" \
  --parallelism-configuration MaxParallelExecutionSteps=3
```

---

## Step 4 — Post-deployment verification

```bash
# Pipeline definition
aws sagemaker describe-pipeline \
  --pipeline-name xgb-training-pipeline \
  --query 'PipelineStatus'

# Latest executions
aws sagemaker list-pipeline-executions \
  --pipeline-name xgb-training-pipeline \
  --max-results 3

# Steps of the latest execution (note Cached status)
EXEC_ARN=$(aws sagemaker list-pipeline-executions \
  --pipeline-name xgb-training-pipeline \
  --max-results 1 \
  --query 'PipelineExecutionSummaries[0].PipelineExecutionArn' --output text)

aws sagemaker list-execution-steps \
  --pipeline-execution-arn "$EXEC_ARN" \
  --query 'PipelineExecutionSteps[*].{Step:Metadata.StepName,Status:Metadata.StepStatus}'

# Registry — pending approval versions
aws sagemaker list-model-packages \
  --model-package-group-name xgb-classifier-group \
  --approval-status PendingManualApproval

# EventBridge rule
aws events describe-rule --name sagemaker-pipeline-on-new-data
```

---

## What the skill catches that a naive pipeline misses

| Configuration | Naive pipeline | Skill output | Why the skill is right |
|---|---|---|---|
| Step ordering | List order = run order | DAG via property references | Steps run as a DAG; list order is NOT execution order |
| Execution role | Uses default | Verifies iam:PassRole on child roles | Without PassRole, job launch fails at runtime |
| RegisterModel | "Deploys the model" | PendingManualApproval gate | Registry is the gate; deployment is a separate CI/CD flow |
| Image references | `:latest` tag | Pinned to digest/version | Tag immutability determines cache behavior |
| TuningStep best model | Hardcoded S3 path | get_top_model_s3_uri | Best model is only known after tuning completes |
| ConditionStep | Python if/else | JsonGet from PropertyFile at runtime | Conditions are runtime DAG branches, not authoring-time Python |
| ParallelismConfiguration | Set to N | Verifies account quota | Account quota caps total concurrency across pipelines |

---

## Related artifacts

- **Skill definition:** `skills/sagemaker-pipeline-deployer/SKILL.md`
- **Steps and DAG guide:** `skills/sagemaker-pipeline-deployer/references/pipeline-steps-and-dag.md`
- **Registry and caching guide:** `skills/sagemaker-pipeline-deployer/references/registry-and-caching.md`
- **Slash command:** `commands/aws/deploy-sagemaker-pipeline.md`
- **Eval suite:** `skills/sagemaker-pipeline-deployer/evals/evals.json`
- **Legacy test cases:** `skills/sagemaker-pipeline-deployer/eval/test-cases.yaml`
