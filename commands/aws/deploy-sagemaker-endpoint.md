---
description: Deploy a SageMaker inference endpoint (real-time, serverless, or async) with production defaults (auto-scaling, data capture, model monitoring, KMS). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create sagemaker endpoint"
  - "deploy sagemaker model"
  - "deploy sagemaker endpoint"
  - "sagemaker real-time inference"
  - "sagemaker serverless inference"
  - "sagemaker async inference"
  - "sagemaker asynchronous inference"
  - "sagemaker auto-scaling"
  - "sagemaker data capture"
  - "sagemaker model monitor"
  - "sagemaker a/b testing"
  - "sagemaker shadow testing"
  - "sagemaker jumpstart"
  - "deploy jumpstart foundation model"
  - "invocations per instance"
  - "sagemaker endpoint config"
routes_to: sagemaker-endpoint-deployer
---

# /aws:deploy-sagemaker-endpoint

Activate the `sagemaker-endpoint-deployer` skill and deploy a SageMaker
inference endpoint with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Model artifact, container image, and execution role
2. Model creation (S3 artifact + image + role)
3. Endpoint config (hosting mode + instance type + variant)
4. Endpoint creation
5. Auto-scaling (target tracking on InvocationsPerInstance)
6. Data capture (request/response to S3 with sampling)
7. Model monitoring (data quality, model quality, bias drift)
8. A/B testing (multiple weighted variants)
9. Shadow testing (shadow variant at 0% traffic)
10. Latest: Serverless Inference, Async Inference, JumpStart models

## When to use

- You need to deploy a SageMaker endpoint (real-time, serverless, or async).
- You want to configure auto-scaling on a SageMaker endpoint.
- You need data capture and model monitoring enabled.
- You want to set up A/B testing or shadow testing for model validation.
- You want to deploy a JumpStart foundation model.

## How to invoke

### Slash command

```
/aws:deploy-sagemaker-endpoint
```

Then provide: endpoint name, model artifact S3 URI, container image URI,
execution role ARN, hosting mode, instance type, instance count,
auto-scaling target, data capture config, and any optional features
(A/B testing, shadow testing, model monitoring, JumpStart model ID).

### Natural language

Any of these routes to the same skill:

- "create a SageMaker real-time endpoint for my model"
- "set up SageMaker serverless inference"
- "configure auto-scaling on my SageMaker endpoint"
- "deploy a JumpStart foundation model"
- "set up A/B testing between two model versions"

### CLI routing

```bash
node cli/bin/cli.js route "create a sagemaker endpoint"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
orchestrator routes to it when the user wants to deploy a SageMaker
inference endpoint. The output checklist feeds into verification pipelines
and audit skills.

## Example

```
You: /aws:deploy-sagemaker-endpoint

     Deploy a SageMaker real-time endpoint "prod-recommendation" in
     us-east-1. Model s3://ml-artifacts/models/rec/model.tar.gz, container
     pytorch-inference:2.1.0-cpu-py310, ml.c5.xlarge x2. Auto-scaling on
     InvocationsPerInstance target 14, min 2, max 8. Data capture 20%
     to s3://sagemaker-captures-prod/rec/. Data quality monitor hourly.
     KMS alias/prod-sagemaker-key. VPC subnets subnet-aaa, subnet-bbb,
     sg sg-xxx. Account: 123456789012.

Skill:
  ENDPOINT: prod-recommendation
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Model: prod-recommendation-model (s3://ml-artifacts/models/rec/model.tar.gz)
    [✓] Hosting mode: real-time
    [✓] Instance type: ml.c5.xlarge, count: 2 (HA)
    [✓] Auto-scaling: InvocationsPerInstance=14, min=2, max=8
    [✓] Data capture: 20% sampling
    [✓] Model monitor: data quality hourly
    [✓] Encryption: KMS alias/prod-sagemaker-key
  VERIFICATION_COMMANDS:
    aws sagemaker describe-endpoint --endpoint-name prod-recommendation
    aws application-autoscaling describe-scaling-policies --service-namespace sagemaker
```

## References

- Skill definition: `skills/sagemaker-endpoint-deployer/SKILL.md`
- Provisioning CLI commands: `skills/sagemaker-endpoint-deployer/references/provisioning-cli-commands.md`
- Instance types and hosting modes: `skills/sagemaker-endpoint-deployer/references/instance-types-and-hosting-modes.md`
- Eval suite: `skills/sagemaker-endpoint-deployer/evals/evals.json`
