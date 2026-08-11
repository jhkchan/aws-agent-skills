---
name: sagemaker-endpoint-deployer
description: >-
  Provisions SageMaker real-time, serverless, and asynchronous inference
  endpoints with production defaults: model creation (S3 artifact, container
  image), endpoint config (instance type, count, variant, weights), endpoint
  creation, auto-scaling on InvocationsPerInstance, data capture, model
  monitor (data quality, model quality, bias drift), A/B testing (weighted
  variants), shadow testing, Serverless Inference, Asynchronous Inference,
  and JumpStart foundation model deployment. Emits a READY_TO_DEPLOY
  checklist with verification commands. Use when deploying a SageMaker
  endpoint, configuring auto-scaling, enabling data capture and model
  monitoring, setting up A/B or shadow variants, or deploying JumpStart
  foundation models. Triggers: create SageMaker endpoint, deploy model,
  real-time inference, serverless inference, async inference, A/B test,
  shadow deployment, data capture, model monitor, JumpStart.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with sagemaker, s3, iam, ec2,
  cloudwatch, and application-autoscaling access. Works with Terraform
  aws_sagemaker_model / aws_sagemaker_endpoint_configuration /
  aws_sagemaker_endpoint resources and CloudFormation
  AWS::SageMaker::Model / EndpointConfig / Endpoint templates.
keywords:
  - aws
  - sagemaker
  - endpoint
  - inference
  - deploy
  - real-time
  - serverless inference
  - asynchronous inference
  - model deployment
  - auto-scaling
  - data capture
  - model monitor
  - a/b testing
  - shadow testing
  - jumpstart
  - foundation models
  - variant
  - invocations
  - container image
  - model artifact
tags:
  - aws
  - sagemaker
  - inference
  - deploy
  - ai-ml
  - endpoint
  - auto-scaling
  - model-monitor
  - jumpstart
  - serverless-inference
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Invoke when the user wants to deploy a SageMaker inference endpoint
    (real-time, serverless, or asynchronous), configure auto-scaling on
    InvocationsPerInstance, enable data capture and model monitoring, set
    up A/B testing or shadow variants, or deploy a JumpStart foundation
    model. Do NOT invoke for SageMaker training jobs, processing jobs,
    feature store, or model registry auditing.
  activation_triggers:
    - "create sagemaker endpoint"
    - "deploy sagemaker model"
    - "real-time inference"
    - "serverless inference"
    - "asynchronous inference"
    - "sagemaker auto-scaling"
    - "data capture"
    - "model monitor"
    - "a/b testing variants"
    - "shadow deployment"
    - "jumpstart foundation model"
---

# SageMaker Endpoint Deployer

## What this skill does

Provisions SageMaker inference endpoints with production-grade defaults
across three hosting modes (real-time, serverless, asynchronous). The
skill walks the operator through model creation, endpoint configuration,
auto-scaling, data capture, model monitoring, and traffic distribution
(A/B testing, shadow testing). Emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create SageMaker endpoint, deploy model, real-time inference, serverless
inference, asynchronous inference, auto-scaling, InvocationsPerInstance,
data capture, model monitor, data quality, model quality, bias drift,
A/B testing, weighted variants, shadow testing, shadow variant, JumpStart,
foundation model, container image, inference code, S3 model artifact,
execution role.

## Invocation contract (hard requirement)

When this skill is invoked with a SageMaker-endpoint-provisioning request
(model name, S3 artifact, container image, instance type, hosting mode,
or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the section "Output format" using the
literal all-caps labels `ENDPOINT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

## Mindset

**One-line takeaway:** a SageMaker endpoint is a three-resource chain
(Model -> EndpointConfig -> Endpoint) where the hosting mode
(real-time vs serverless vs async) is decided at EndpointConfig creation
and cannot be changed in place — switching modes requires a new config
and endpoint update.

Three misconceptions dominate SageMaker endpoint misdesign at provisioning
time:

- **"I can switch from real-time to serverless by updating the endpoint."**
  The hosting mode is baked into the EndpointConfig via the
  `ProductionVariants` (real-time/async) vs `ServerlessConfig` (serverless)
  structure. Switching modes requires creating a new EndpointConfig and
  calling `update-endpoint` with the new config. There is no in-place
  mode toggle.

- **"Auto-scaling is enabled by default."** It is NOT. A newly created
  real-time endpoint runs at `InitialInstanceCount` with no scaling
  policy. Without an auto-scaling policy on `InvocationsPerInstance`,
  the endpoint either throttles under load (too few instances) or burns
  cost at idle (too many). Auto-scaling must be registered explicitly via
  Application Auto Scaling.

- **"Data capture and model monitoring are the same thing."** Data
  capture (DataCaptureConfig) records incoming requests and outgoing
  responses to S3. Model monitoring (MonitoringSchedule) analyzes that
  captured data for drift, quality, and bias. Data capture is the
  prerequisite; model monitoring consumes its output. Without data
  capture, model monitoring has no data to evaluate.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Deployment checklist + hosting mode decision gate | Before any deployment |
| **§ Mindset** | Three-resource chain, hosting mode immutability, auto-scaling gap | Understanding the model |
| **§ Prerequisites** | S3 artifact, execution role, VPC, model registry | Before producing the plan |
| **§ Hosting mode selection** | Real-time vs serverless vs async decision matrix | Choosing the right mode |
| **§ Provisioning procedure** | 10-step deploy: model, config, endpoint, scaling, capture, monitor, A/B, shadow, JumpStart | When building the deploy plan |
| **§ Common patterns** | Boilerplate for real-time, serverless, async, A/B, shadow | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, CHECKLIST, VERIFICATION_COMMANDS | Formatting the response |
| **§ STRICT output contract** | Required structure + FORBIDDEN patterns | Validating the output |
| **§ NEVER** | Top 5 anti-patterns | Review before risky operations |
| **§ Expert heuristic** | Instance selection + auto-scaling target strategy | Sizing decisions |

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| S3 model artifact | Compressed model data (`model.tar.gz`) in an S3 bucket | Step 1 |
| Container image | Pre-built SageMaker DLC image or custom image in ECR | Step 1 |
| Execution role | IAM role with SageMaker assume + S3 read + ECR pull | Step 1 |
| Model creation | `create-model` referencing artifact + image + role | Step 2 |
| Hosting mode | Real-time / Serverless / Async (decided at EndpointConfig) | Step 3 |
| Instance type | Real-time: ml.c5/m5/g5/r5; GPU for deep learning | Step 3 |
| Initial instance count | >= 2 for HA (different AZs) in production | Step 3 |
| Variant name | Named variant for A/B or shadow testing | Step 3 |
| Endpoint creation | `create-endpoint` from EndpointConfig | Step 4 |
| Auto-scaling | Target tracking on InvocationsPerInstance | Step 5 |
| Data capture | Request/response to S3 with sampling percentage | Step 6 |
| Model monitor | Data quality, model quality, bias drift schedules | Step 7 |
| A/B testing | Multiple variants with traffic weights | Step 8 |
| Shadow testing | Shadow variant at 0% traffic receiving a copy | Step 9 |
| JumpStart | Pre-trained foundation model deployment | Step 10 |

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If any
are missing, the verdict is **PREREQUISITES_MISSING** with a specific gap
citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with SageMaker access | Cannot provision without it | `aws sts get-caller-identity` |
| Region selected | Instance availability varies by region; GPU types are limited | `aws configure get region` |
| S3 model artifact (`model.tar.gz`) | The model data the container loads at startup | `aws s3 ls s3://<bucket>/<prefix>/model.tar.gz` |
| Container image URI (DLC or ECR) | The inference code that serves predictions | `aws ecr describe-images --repository-name <repo>` or DLC registry |
| SageMaker execution role | Needs `sagemaker:CreateModel`, S3 read, ECR pull, KMS decrypt | `aws iam get-role --role-name <execution-role>` |
| VPC + subnets (for VPC-attached endpoints) | Private networking; S3/Gateway VPC endpoints | `aws ec2 describe-subnets` |
| KMS key (for encryption at rest) | Endpoint config and data capture encryption | `aws kms describe-key --key-id <key-id>` |
| Model monitoring S3 bucket | Data capture destination + baseline constraints | `aws s3 ls s3://<monitoring-bucket>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Hosting mode selection (decide at EndpointConfig — not swappable in place)

| Mode | Latency | Payload size | Auto-scaling | Use when |
|---|---|---|---|---|
| **Real-time** | Low (< 1s typical) | < 6 MB | Application Auto Scaling (InvocationsPerInstance) | Interactive inference, synchronous APIs, low-latency SLAs |
| **Serverless** | Cold-start + low | < 4 MB | Automatic (scale-to-zero) | Intermittent traffic, unpredictable workloads, cost optimization |
| **Asynchronous** | Minutes (with S3) | Up to 256 MB S3 payload | Application Auto Scaling (ApproximateBacklogSizePerInstance) | Large payloads, long inference times (LLM generation, batch scoring) |

**Immutability note:** the hosting mode is embedded in the EndpointConfig
structure (`ProductionVariants` for real-time/async, `ServerlessConfig`
for serverless). Switching modes requires a new EndpointConfig and
`update-endpoint`. Plan the mode before creating the config.

## 10-step provisioning procedure

### Step 1 — Model artifact, container image, and execution role

**S3 model artifact:** package the trained model as `model.tar.gz`
containing model weights and any inference code. Upload to S3.

```bash
aws s3 cp model.tar.gz s3://<bucket>/<prefix>/model.tar.gz
```

**Container image:** choose a SageMaker Deep Learning Container (DLC) or
a custom image in ECR.

```bash
# List available DLC images for your framework + region
aws ecr describe-images --registry-id 763104351884 \
  --repository-name pytorch-inference --region us-east-1 \
  --query 'sort_by(imageDetails,& imagePushedAt)[-5].imageTags'
```

**Execution role:** the SageMaker execution role needs:
- Trust policy: `sagemaker.amazonaws.com`
- Permissions: `s3:GetObject` on the model artifact bucket, `ecr:BatchGetImage`
  on the container image, optionally `kms:Decrypt` for encrypted endpoints.

```bash
aws iam get-role --role-name SageMakerExecutionRole \
  --query 'Role.Arn' --output text
```

### Step 2 — Create the model

The model resource binds the S3 artifact, container image, and execution
role. This is the first resource in the three-resource chain.

```bash
aws sagemaker create-model \
  --model-name <model-name> \
  --primary-container Image=<image-uri>,ModelDataUrl=s3://<bucket>/<prefix>/model.tar.gz \
  --execution-role-arn arn:aws:iam::<account-id>:role/SageMakerExecutionRole \
  --vpc-config Subnets=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-xxx
```

**VPC-attached endpoints:** for private networking, specify subnets and
security groups. The endpoint's VPC needs S3 and ECR VPC endpoints (or
NAT gateway) to pull the model artifact and container image.

### Step 3 — Endpoint config (hosting mode + instance selection)

The EndpointConfig defines the hosting mode, instance type, initial count,
variant name, and optionally data capture.

**Real-time endpoint config:**

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name> \
  --production-variants \
    VariantName=AllTraffic,ModelName=<model-name>,InstanceType=ml.c5.xlarge,InitialInstanceCount=2,InitialVariantWeight=1 \
  --data-capture-config \
    EnableCapture=true,InitialSamplingPercentage=100,DestinationS3Uri=s3://<capture-bucket>/captures/,CaptureOptions=[{CaptureMode=Input},{CaptureMode=Output}],CaptureContentTypeHeaders={CsvContentTypes=[text/csv],JsonContentTypes=[application/json]} \
  --kms-key-id arn:aws:kms:<region>:<account-id>:key/<key-id>
```

**Instance type selection guide:**

| Workload | CPU instances | GPU instances | When to choose |
|---|---|---|---|
| Tabular / classical ML | `ml.c5.xlarge` - `ml.c5.9xlarge` | n/a | XGBoost, sklearn, light payloads |
| NLP (transformers, small) | `ml.c5.2xlarge` - `ml.c5.9xlarge` | `ml.g4dn.xlarge` - `ml.g4dn.12xlarge` | BERT-base, DistilBERT, token classification |
| Computer vision | `ml.c5.4xlarge`+ | `ml.g5.xlarge` - `ml.g5.48xlarge` | ResNet, YOLO, image classification |
| LLM inference | n/a (too slow) | `ml.g5.12xlarge` - `ml.g5.48xlarge`, `ml.inf2.xlarge` - `ml.inf2.48xlarge` | 7B-70B parameter models; inf2 for cost-efficient LLM |
| High-throughput batch scoring | `ml.m5.4xlarge` - `ml.m5.24xlarge` | n/a | Batch transform or async inference |

**Production HA rule:** `InitialInstanceCount` of at least 2. SageMaker
distributes instances across AZs within the region. A single-instance
endpoint has no redundancy — an AZ failure takes the endpoint down.

**Serverless endpoint config (different structure):**

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-serverless \
  --serverless-config \
    ServerlessInferenceConfigName=AllTraffic,MaxConcurrency=10,MemorySizeInMB=2048,ProvisionedConcurrency=2
```

Serverless inference does NOT use `ProductionVariants` or instance types.
It uses `MemorySizeInMB` (1024-6144) and `MaxConcurrency` (1-200).

**Asynchronous endpoint config:**

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-async \
  --production-variants \
    VariantName=AllTraffic,ModelName=<model-name>,InstanceType=ml.g5.xlarge,InitialInstanceCount=1 \
  --async-inference-config \
    OutputConfig=S3OutputPath=s3://<async-bucket>/output/,NotificationConfig=SuccessTopic=<topic-arn>,ErrorTopic=<error-topic-arn>,MaxConcurrentInvocationsPerInstance=4
```

Asynchronous endpoints queue requests via S3; results are written back to
S3 with optional SNS notification. Supports `InstanceCount: 0` for
scale-to-zero when idle.

### Step 4 — Create the endpoint

```bash
aws sagemaker create-endpoint \
  --endpoint-name <endpoint-name> \
  --endpoint-config-name <config-name>
```

Endpoint creation takes 5-15 minutes (container pull, model load, health
check). Wait for `InService` status:

```bash
aws sagemaker describe-endpoint --endpoint-name <endpoint-name> \
  --query 'EndpointStatus' --output text
```

### Step 5 — Auto-scaling (target tracking on InvocationsPerInstance)

Auto-scaling is NOT enabled by default. A real-time endpoint without a
scaling policy runs at a fixed instance count.

```bash
# Register the endpoint as a scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker \
  --resource-id endpoint/<endpoint-name>/variant/<variant-name> \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --min-capacity 1 \
  --max-capacity 8

# Apply target tracking policy on InvocationsPerInstance
aws application-autoscaling put-scaling-policy \
  --policy-name <endpoint-name>-scaling-policy \
  --service-namespace sagemaker \
  --resource-id endpoint/<endpoint-name>/variant/<variant-name> \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    TargetMetricType=SageMakerVariantInvocationsPerInstance,TargetValue=300,PredefinedMetricSpecification={PredefinedMetricType=SageMakerVariantInvocationsPerInstance},ScaleInCooldown=300,ScaleOutCooldown=60
```

**TargetValue tuning:** `InvocationsPerInstance` target depends on the
instance type and model latency. A target too high causes throttling
under burst; too low causes over-scaling. Monitor `Invocations` and
`InvocationsPerInstance` CloudWatch metrics.

**For async inference:** scale on `ApproximateBacklogSizePerInstance`
instead of `InvocationsPerInstance`. This metric tracks queue depth per
instance.

**For serverless inference:** auto-scaling is built-in (scale-to-zero).
No Application Auto Scaling configuration needed.

### Step 6 — Data capture (prerequisite for model monitoring)

Data capture records incoming requests and outgoing responses to S3.
It is configured in the EndpointConfig via `DataCaptureConfig`.

Key parameters:
- **EnableCapture:** `true` / `false`
- **InitialSamplingPercentage:** 0-100 (production: 10-50%; staging: 100%)
- **DestinationS3Uri:** S3 prefix for captured data
- **CaptureOptions:** `Input`, `Output` (or both)
- **CaptureContentTypeHeaders:** `CsvContentTypes`, `JsonContentTypes`

```bash
# Data capture is set in create-endpoint-config (see Step 3)
# Verify capture is flowing:
aws s3 ls s3://<capture-bucket>/captures/<endpoint-name>/AllTraffic/
```

**Common mistake:** setting `InitialSamplingPercentage: 100` in production
doubles inference latency for the capture write and fills S3 rapidly.
Use 10-50% for production monitoring; 100% for pre-production validation.

### Step 7 — Model monitoring (data quality, model quality, bias drift)

Model monitoring runs scheduled analysis on captured data using baseline
constraints. Three monitor types:

**Data quality monitor:** detects feature drift and schema violations.
```bash
aws sagemaker create-monitoring-schedule \
  --monitoring-schedule-name <endpoint-name>-data-quality \
  --endpoint-name <endpoint-name> \
  --monitoring-type DataQuality \
  --monitoring-job-definition-name <baseline-job-definition> \
  --schedule-config 'ScheduleExpression=polling/1h'
```

**Model quality monitor:** tracks prediction quality (accuracy, F1, MSE)
against ground-truth labels.

**Bias drift monitor:** detects fairness metric changes over time using
the captured data.

**Baseline constraints:** before enabling monitoring, generate baseline
statistics and constraints from a representative dataset using
`suggest_baseline`. The monitor compares live traffic against this baseline.

```bash
# Generate baseline from training data
aws sagemaker processing start \
  --app-specification Image=156402425085.dkr.ecr.us-west-2.amazonaws.com/sagemaker-model-monitor-analyzer, ... \
  --processing-input SourceS3Uri=s3://<bucket>/baseline-data/,Destination=/opt/ml/processing/input/baseline ...
```

### Step 8 — A/B testing (multiple weighted variants)

A/B testing deploys multiple models behind a single endpoint with traffic
weights. The EndpointConfig defines multiple `ProductionVariants`, each
with an `InitialVariantWeight`.

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-ab \
  --production-variants \
    '[{"VariantName":"variantA","ModelName":"model-a","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":9},
      {"VariantName":"variantB","ModelName":"model-b","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":1}]'
```

Traffic distribution: weights are relative. `9:1` sends 90% to variantA,
10% to variantB. Shift weights via `update-endpoint-weights-and-capacities`:

```bash
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name <endpoint-name> \
  --desired-weights-and-capacities \
    variantA=5,variantB=5
```

**Common mistake:** using different instance types for A/B variants.
Differing instance types confound the comparison — latency differences
may come from the hardware, not the model. Use the same instance type
for both variants.

### Step 9 — Shadow testing (shadow variant)

Shadow testing deploys a candidate model that receives a copy of live
traffic but its responses are NOT returned to the caller. This allows
comparing candidate performance against production without risk.

```bash
# Create a shadow variant config
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-shadow \
  --production-variants \
    '[{"VariantName":"prod","ModelName":"model-prod","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":1}]' \
  --shadow-production-variants \
    '[{"VariantName":"shadow","ModelName":"model-candidate","InstanceType":"ml.c5.xlarge","InitialInstanceCount":1}]'
```

The shadow variant receives the same requests as the prod variant. Enable
data capture on both variants to compare predictions offline. Shadow
variant responses are discarded — callers only see the prod variant
response.

### Step 10 — Latest features: Serverless, Async, JumpStart foundation models

**SageMaker Serverless Inference** (GA 2024-2025):
- Scales automatically including scale-to-zero when idle
- Billed by request count and compute duration (no idle cost)
- `MemorySizeInMB` (1024-6144), `MaxConcurrency` (1-200),
  optional `ProvisionedConcurrency` for warm capacity
- Best for intermittent or unpredictable workloads

**SageMaker Asynchronous Inference** (GA 2024):
- Queues inference requests via S3; supports payloads up to 256 MB
- Scale-to-zero when queue drains (`InstanceCount: 0` minimum)
- SNS notification on completion or error
- Best for large payloads, long inference times (LLM generation, video
  processing, batch scoring)

**SageMaker JumpStart foundation models** (2024-2025):
- Pre-trained models (Llama, Mistral, Qwen, Stable Diffusion, etc.)
- One-command deploy via `create-model` with JumpStart-provided
  artifact and container
- Use `list-models --query 'Models[?contains(ModelName, `foundation`)]'`
  to discover available models

```bash
# Deploy a JumpStart foundation model
aws sagemaker create-model \
  --model-name jumpstart-llama-7b \
  --primary-container \
    Image=763104351884.dkr.ecr.us-west-2.amazonaws.com/djl-inference:0.23.0-deepspeed0.9.5-cu118,ModelDataUrl=s3://jumpstart-cache-prod-us-west-2/meta-llama/models/meta-llama-7b/ \
  --execution-role-arn arn:aws:iam::<account-id>:role/SageMakerExecutionRole
```

JumpStart models use optimized inference containers (DJL, vLLM, TGI) with
quantization support (bitsandbytes, AWQ, GPTQ) for cost-efficient LLM
deployment on `ml.g5` or `ml.inf2` instances.

## Common patterns (boilerplate)

### Real-time endpoint with auto-scaling and data capture (production)

```bash
aws sagemaker create-model \
  --model-name prod-rec-model \
  --primary-container Image=<image-uri>,ModelDataUrl=s3://<bucket>/rec/model.tar.gz \
  --execution-role-arn arn:aws:iam::<acct>:role/SageMakerExecutionRole

aws sagemaker create-endpoint-config \
  --endpoint-config-name prod-rec-config \
  --production-variants VariantName=AllTraffic,ModelName=prod-rec-model,InstanceType=ml.c5.xlarge,InitialInstanceCount=2 \
  --data-capture-config EnableCapture=true,InitialSamplingPercentage=20,DestinationS3Uri=s3://<capture-bucket>/rec/ \
  --kms-key-id arn:aws:kms:<region>:<acct>:key/<key-id>

aws sagemaker create-endpoint --endpoint-name prod-rec --endpoint-config-name prod-rec-config

aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker --resource-id endpoint/prod-rec/variant/AllTraffic \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount --min-capacity 2 --max-capacity 8

aws application-autoscaling put-scaling-policy \
  --policy-name prod-rec-scaling --service-namespace sagemaker \
  --resource-id endpoint/prod-rec/variant/AllTraffic \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration TargetValue=14,PredefinedMetricSpecification={PredefinedMetricType=SageMakerVariantInvocationsPerInstance},ScaleInCooldown=300,ScaleOutCooldown=60
```

### Serverless inference endpoint

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name serverless-config \
  --serverless-config ServerlessInferenceConfigName=AllTraffic,MaxConcurrency=10,MemorySizeInMB=2048,ProvisionedConcurrency=2

aws sagemaker create-endpoint --endpoint-name serverless-ep --endpoint-config-name serverless-config
```

### A/B testing with two variants

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name ab-config \
  --production-variants \
    '[{"VariantName":"variantA","ModelName":"model-v1","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":9},
      {"VariantName":"variantB","ModelName":"model-v2","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":1}]'

aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name ab-ep --desired-weights-and-capacities variantA=5,variantB=5
```

## NEVER do these things (top 5)

1. **NEVER deploy a production real-time endpoint with
   `InitialInstanceCount: 1`.** A single-instance endpoint has no
   redundancy — an AZ failure takes it down with zero failover. Use
   at least 2 for production (SageMaker distributes across AZs).

2. **NEVER omit auto-scaling on a real-time endpoint expecting variable
   traffic.** Without a scaling policy on `InvocationsPerInstance`, the
   endpoint runs at a fixed count. Under burst load it throttles (429s);
   at idle it burns cost. Register the scalable target and apply a
   target-tracking policy.

3. **NEVER set `InitialSamplingPercentage: 100` for data capture in a
   high-traffic production endpoint.** 100% capture doubles the
   inference path latency (synchronous write to S3) and fills S3
   rapidly. Use 10-50% for production monitoring; 100% only for
   pre-production validation.

4. **NEVER use different instance types for A/B testing variants.**
   Differing hardware confounds the model comparison — latency or
   throughput differences may come from the instance, not the model.
   Use the same instance type for all variants in an A/B test.

5. **NEVER try to switch hosting modes by updating the endpoint
   in place.** The hosting mode (real-time / serverless / async) is
   embedded in the EndpointConfig structure (`ProductionVariants` vs
   `ServerlessConfig`). Switching modes requires creating a new
   EndpointConfig and calling `update-endpoint` with the new config.

## Expert heuristic: instance selection and auto-scaling target

```
INSTANCE SELECTION
   ├─ CPU-only model (XGBoost, sklearn, light NLP)
   │    └─ ml.c5.xlarge (2 vCPU) — ml.c5.2xlarge (8 vCPU)
   │         • Start at c5.xlarge for dev; c5.2xlarge for prod
   │         • 2 GB RAM per vCPU — enough for most tabular models
   │
   ├─ GPU model (transformers, computer vision)
   │    ├─ Single-GPU: ml.g4dn.xlarge (1x T4) — ml.g5.xlarge (1x A10G)
   │    │    └─ BERT-base, ResNet, small image generation
   │    ├─ Multi-GPU: ml.g5.12xlarge (4x A10G) — ml.g5.48xlarge (8x A10G)
   │    │    └─ Large transformers, batch image processing
   │    └─ Inferentia2: ml.inf2.xlarge — ml.inf2.48xlarge
   │         └─ LLM inference (Llama, Mistral) — lowest cost/token
   │
   └─ LLM (7B-70B parameters)
        ├─ 7B-13B: ml.g5.2xlarge (1x A10G, 24GB) — quantized
        ├─ 30B-70B: ml.g5.48xlarge (8x A10G) or ml.inf2.48xlarge (12x Inferentia2)
        └─ Use DJL/vLLM containers with quantization (AWQ, GPTQ)

AUTO-SCALING TARGET (InvocationsPerInstance)
   ├─ Target = (instance_per_second_capacity) × (target_utilization)
   ├─ c5.xlarge serving a 50ms model:
   │    └─ 1000ms / 50ms = 20 req/s capacity
   │         • Target at 70% utilization = 14 InvocationsPerInstance
   │         • Set TargetValue=14, min=2, max=8
   ├─ g5.xlarge serving a 200ms LLM:
   │    └─ 1000ms / 200ms = 5 req/s capacity
   │         • Target at 60% utilization = 3 InvocationsPerInstance
   │         • Set TargetValue=3 (conservative for GPU memory)
   └─ ScaleInCooldown=300s (avoid flapping); ScaleOutCooldown=60s (react fast)
```

**Async inference scaling:** target `ApproximateBacklogSizePerInstance`
instead. This metric tracks the queue depth per instance. A target of 5
means each instance should have at most 5 pending requests in the queue.

## Output format

```text
ENDPOINT: <endpoint-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Model: <model-name> (S3 artifact: s3://<bucket>/<prefix>/model.tar.gz)
  [✓|✗] Container image: <image-uri> (DLC | custom ECR)
  [✓|✗] Execution role: <role-arn> (S3 read + ECR pull + KMS decrypt)
  [✓|✗] Hosting mode: <real-time | serverless | asynchronous>
  [✓|✗] Instance type: <ml.c5.xlarge> (CPU) | <ml.g5.xlarge> (GPU) | serverless (Memory=<MB>)
  [✓|✗] Initial instance count: <N> (>=2 for HA if real-time production)
  [✓|✗] Variant: <variant-name> (InitialVariantWeight: <weight>)
  [✓|✗] Encryption: KMS <key-arn>
  [✓|✗] Auto-scaling: target=<InvocationsPerInstance|ApproximateBacklogSizePerInstance>, TargetValue=<N>, min=<N>, max=<N> | Serverless (built-in)
  [✓|✗] Data capture: Enabled, sampling=<N>%, destination=s3://<capture-bucket>/
  [✓|✗] Model monitor: <data quality | model quality | bias drift> schedule=<interval> | Disabled
  [✓|✗] A/B testing: <variants and weights> | Single variant
  [✓|✗] Shadow testing: <shadow variant> | None
  [✓|✗] VPC config: <subnet-ids, sg-ids> | Public
  [✓|✗] Tags: <list>
VERIFICATION_COMMANDS:
  aws sagemaker describe-endpoint --endpoint-name <endpoint-name>
  aws sagemaker describe-endpoint-config --endpoint-config-name <config-name>
  aws sagemaker describe-model --model-name <model-name>
  aws application-autoscaling describe-scaling-policies --service-namespace sagemaker
  aws s3 ls s3://<capture-bucket>/captures/<endpoint-name>/AllTraffic/
```

### Worked example — real-time endpoint with auto-scaling and monitoring

```text
ENDPOINT: prod-recommendation
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Model: prod-recommendation-model (S3: s3://ml-artifacts/models/recommendation/model.tar.gz)
  [✓] Container image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310 (DLC)
  [✓] Execution role: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  [✓] Hosting mode: real-time
  [✓] Instance type: ml.c5.xlarge (CPU, tabular recommendation model)
  [✓] Initial instance count: 2 (HA across 2 AZs)
  [✓] Variant: AllTraffic (InitialVariantWeight: 1)
  [✓] Encryption: KMS arn:aws:kms:us-east-1:123456789012:key/abc-123
  [✓] Auto-scaling: target=InvocationsPerInstance, TargetValue=14, min=2, max=8
  [✓] Data capture: Enabled, sampling=20%, destination=s3://sagemaker-captures-prod/recommendation/
  [✓] Model monitor: data quality schedule=hourly | model quality=disabled | bias drift=disabled
  [✓] A/B testing: Single variant
  [✓] Shadow testing: None
  [✓] VPC config: subnet-aaa, subnet-bbb, sg-xxx
  [✓] Tags: Environment=production, Workload=recommendation, Team=ml-platform
VERIFICATION_COMMANDS:
  aws sagemaker describe-endpoint --endpoint-name prod-recommendation
  aws sagemaker describe-endpoint-config --endpoint-config-name prod-recommendation-config
  aws sagemaker describe-model --model-name prod-recommendation-model
  aws application-autoscaling describe-scaling-policies --service-namespace sagemaker --resource-id endpoint/prod-recommendation/variant/AllTraffic
  aws s3 ls s3://sagemaker-captures-prod/recommendation/prod-recommendation/AllTraffic/
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
ENDPOINT: <endpoint-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] <check description>
VERIFICATION_COMMANDS:
  <aws sagemaker / application-autoscaling / s3 commands>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble. The ENDPOINT/VERDICT block
  is the FIRST line, always. Use uppercase verdict values only
  (`READY_TO_DEPLOY`, `PREREQUISITES_MISSING`).
- NEVER omit the CHECKLIST — every dimension (model, image, role, hosting
  mode, instance type, instance count, variant, encryption, auto-scaling,
  data capture, model monitor, A/B, shadow, VPC, tags) must appear with
  a pass/fail marker.
- NEVER recommend a single-instance real-time endpoint for production
  without flagging it as a WARN finding (no HA, AZ failure = outage).
- NEVER list a CLI command with placeholder flags in a READY_TO_DEPLOY
  plan — every flag must be populated with actual values from the input.
- NEVER recommend serverless inference for a latency-sensitive workload
  without flagging the cold-start risk.

## Recent AWS features (2024-2026)

- **SageMaker Serverless Inference GA (2024):** automatic scaling
  including scale-to-zero. Provisioning tip: use `ProvisionedConcurrency`
  to eliminate cold-start latency for production workloads with
  latency requirements.

- **SageMaker Asynchronous Inference GA (2024):** S3-queued inference
  for large payloads (up to 256 MB) and long inference times. Scale-to-
  zero when queue drains. Provisioning tip: pair with SNS notification
  for completion callbacks.

- **SageMaker JumpStart foundation models (2024-2025):** pre-trained
  Llama, Mistral, Qwen, Stable Diffusion models with optimized inference
  containers (DJL, vLLM, TGI). One-command deployment. Provisioning tip:
  use `ml.inf2` instances with Neuron for lowest cost per token on LLMs.

- **Inferentia2 instances (ml.inf2) (2024):** purpose-built for
  transformer inference. Up to 12x Inferentia2 chips on ml.inf2.48xlarge.
  Provisioning tip: requires Neuron SDK compilation; not all frameworks
  supported out of the box.

- **SageMaker model monitoring enhancements (2024-2025):** near-real-
  time monitoring (15-minute schedules), model quality monitoring with
  ground-truth merge, bias drift detection. Provisioning tip: data
  capture must be enabled first; monitoring analyzes captured data.

- **Shadow testing enhancements (2024):** `shadow-production-variants`
  in EndpointConfig for zero-risk model validation. Provisioning tip:
  shadow responses are discarded; enable data capture on both variants
  to compare offline.

- **Quantization support (AWQ, GPTQ) (2024-2025):** DJL and vLLM
  containers support 4-bit and 8-bit quantization for LLM inference,
  reducing GPU memory by 2-4x. Provisioning tip: quantize before
  deployment; verify accuracy retention on a held-out set.

## Domain

AWS CloudOps / SageMaker Inference Endpoint Provisioning, Auto-Scaling,
Data Capture, and Model Monitoring.

## AWS documentation

- **SageMaker Developer Guide** — https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html
- **Deploy Models for Real-Time Inference** — https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints-deployment.html
- **Serverless Inference** — https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoint.html
- **Asynchronous Inference** — https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference-endpoint.html
- **Auto-Scaling SageMaker Endpoints** — https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-scaling.html
- **Data Capture and Model Monitor** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html
- **A/B Testing** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-ab-testing.html
- **Shadow Testing** — https://docs.aws.amazon.com/sagemaker/latest/dg/shadow-tests.html
- **SageMaker JumpStart** — https://docs.aws.amazon.com/sagemaker/latest/dg/studio-jumpstart.html
- **Inferentia2** — https://docs.aws.amazon.com/dlami/latest/devguide/tutorial-inferentia2.html
