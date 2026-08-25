# SageMaker Endpoint Deployer — Advanced Patterns

Step 7-10 deep dives (model monitoring, A/B, shadow, latest features), the instance-selection and auto-scaling heuristics, and recent AWS features — moved verbatim from SKILL.md for progressive disclosure.

## Step 7 — Model monitoring (data quality, model quality, bias drift)

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

## Step 8 — A/B testing (multiple weighted variants)

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

## Step 9 — Shadow testing (shadow variant)

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

## Step 10 — Latest features: Serverless, Async, JumpStart foundation models

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

