# Baseline (no-skill) — serverless-inference-intermittent

> This is the response a model produces **without** the skill definition.
> It produces a generic real-time endpoint config instead of the serverless
> ServerlessConfig structure, missing the scale-to-zero benefit and the
> MemorySizeInMB / MaxConcurrency / ProvisionedConcurrency parameters.

---

To create a SageMaker endpoint for intermittent traffic:

1. Create the model:
```bash
aws sagemaker create-model \
  --model-name serverless-classifier-model \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310,ModelDataUrl=s3://ml-artifacts/classifier/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

2. Create endpoint config:
```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name serverless-classifier-config \
  --production-variants VariantName=AllTraffic,ModelName=serverless-classifier-model,InstanceType=ml.c5.xlarge,InitialInstanceCount=1
```

3. Create the endpoint. For intermittent traffic you can stop and start it manually.
