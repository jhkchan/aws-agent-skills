# End-to-End Example: Real-Time Endpoint with Auto-Scaling and Monitoring

A walkthrough showing how to use the `sagemaker-endpoint-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a SageMaker real-time inference endpoint for a
recommendation model. The endpoint needs:

- Model artifact at s3://ml-artifacts/models/rec/model.tar.gz
- DLC container image (PyTorch inference, CPU)
- ml.c5.xlarge instances, 2 for HA across AZs
- Auto-scaling on InvocationsPerInstance (target 14, min 2, max 8)
- Data capture at 20% sampling for model monitoring
- Data quality monitor on hourly schedule
- KMS encryption with customer-managed key
- VPC-attached for private networking

Endpoint name: `prod-recommendation`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-sagemaker-endpoint
```

Then paste the endpoint requirements.

### Option B: Natural language

```
You: "Deploy a SageMaker real-time endpoint named prod-recommendation in
      us-east-1. Model artifact s3://ml-artifacts/models/rec/model.tar.gz,
      container pytorch-inference:2.1.0-cpu-py310. Instance type ml.c5.xlarge,
      initial count 2. Auto-scaling on InvocationsPerInstance target 14, min 2,
      max 8. Data capture at 20% to s3://sagemaker-captures-prod/rec/. Data
      quality monitor hourly. KMS alias/prod-sagemaker-key. VPC subnets
      subnet-aaa, subnet-bbb, sg sg-xxx. Account: 123456789012."
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ENDPOINT: prod-recommendation
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Model: prod-recommendation-model (S3: s3://ml-artifacts/models/rec/model.tar.gz)
  [✓] Container image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310
  [✓] Execution role: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  [✓] Hosting mode: real-time
  [✓] Instance type: ml.c5.xlarge (CPU, tabular recommendation)
  [✓] Initial instance count: 2 (HA across 2 AZs)
  [✓] Variant: AllTraffic
  [✓] Encryption: KMS alias/prod-sagemaker-key
  [✓] Auto-scaling: target=InvocationsPerInstance, TargetValue=14, min=2, max=8
  [✓] Data capture: Enabled, sampling=20%, destination=s3://sagemaker-captures-prod/rec/
  [✓] Model monitor: data quality schedule=hourly
  [✓] VPC config: subnet-aaa, subnet-bbb, sg-xxx
  [✓] Tags: Environment=production, Workload=recommendation
VERIFICATION_COMMANDS:
  aws sagemaker describe-endpoint --endpoint-name prod-recommendation
  aws sagemaker describe-endpoint-config --endpoint-config-name prod-recommendation-config
  aws application-autoscaling describe-scaling-policies --service-namespace sagemaker
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# 1. Create model
aws sagemaker create-model \
  --model-name prod-recommendation-model \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310,ModelDataUrl=s3://ml-artifacts/models/rec/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole \
  --vpc-config Subnets=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-xxx

# 2. Create endpoint config (2 instances, data capture, KMS)
aws sagemaker create-endpoint-config \
  --endpoint-config-name prod-recommendation-config \
  --production-variants VariantName=AllTraffic,ModelName=prod-recommendation-model,InstanceType=ml.c5.xlarge,InitialInstanceCount=2,InitialVariantWeight=1 \
  --data-capture-config EnableCapture=true,InitialSamplingPercentage=20,DestinationS3Uri=s3://sagemaker-captures-prod/rec/,CaptureOptions=[{CaptureMode=Input},{CaptureMode=Output}],CaptureContentTypeHeaders={JsonContentTypes=[application/json]} \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-sagemaker-key

# 3. Create endpoint
aws sagemaker create-endpoint \
  --endpoint-name prod-recommendation \
  --endpoint-config-name prod-recommendation-config

# 4. Register auto-scaling (NOT enabled by default)
aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker \
  --resource-id endpoint/prod-recommendation/variant/AllTraffic \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --min-capacity 2 --max-capacity 8

# 5. Apply scaling policy
aws application-autoscaling put-scaling-policy \
  --policy-name prod-recommendation-scaling \
  --service-namespace sagemaker \
  --resource-id endpoint/prod-recommendation/variant/AllTraffic \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration TargetValue=14,PredefinedMetricSpecification={PredefinedMetricType=SageMakerVariantInvocationsPerInstance},ScaleInCooldown=300,ScaleOutCooldown=60
```

---

## Step 4 — Post-deployment verification

```bash
# Endpoint status — wait for "InService"
aws sagemaker describe-endpoint --endpoint-name prod-recommendation \
  --query 'EndpointStatus'

# Verify auto-scaling policy
aws application-autoscaling describe-scaling-policies \
  --service-namespace sagemaker \
  --resource-id endpoint/prod-recommendation/variant/AllTraffic

# Verify data capture is flowing (after some traffic)
aws s3 ls s3://sagemaker-captures-prod/rec/prod-recommendation/AllTraffic/

# Test invocation
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name prod-recommendation \
  --content-type application/json \
  --body '{"user_id": 12345, "item_id": 67890}' \
  /tmp/prediction.json
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Instance count | `InitialInstanceCount=1` | `InitialInstanceCount=2` | Single instance = no HA; AZ failure = outage. |
| Auto-scaling | Omitted (not default) | Registered + target tracking | Without scaling policy, endpoint throttles under burst or burns cost at idle. |
| Data capture | Omitted | Enabled at 20% | Without data capture, model monitoring has no data to analyze. |
| Sampling % | 100% if enabled | 20% for production | 100% doubles inference latency for the synchronous S3 write. |
| Hosting mode | Real-time only | Correct mode for workload | Serverless/async are better for intermittent/large-payload workloads. |
| VPC config | Public endpoint | VPC-attached with subnets+SG | Private networking for production; S3/Gateway VPC endpoints needed. |

---

## Related artifacts

- **Skill definition:** `skills/sagemaker-endpoint-deployer/SKILL.md`
- **Provisioning CLI commands:** `skills/sagemaker-endpoint-deployer/references/provisioning-cli-commands.md`
- **Instance types and hosting modes:** `skills/sagemaker-endpoint-deployer/references/instance-types-and-hosting-modes.md`
- **Slash command:** `commands/aws/deploy-sagemaker-endpoint.md`
- **Eval suite:** `skills/sagemaker-endpoint-deployer/evals/evals.json`
- **Legacy test cases:** `skills/sagemaker-endpoint-deployer/eval/test-cases.yaml`
