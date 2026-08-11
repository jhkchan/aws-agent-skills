# Baseline (no-skill) — async-inference-large-model

> This is the response a model produces **without** the skill definition.
> It produces a generic real-time endpoint instead of an async endpoint with
> AsyncInferenceConfig, missing the S3 queueing, SNS notification, scale-to-
> zero capability, and the ApproximateBacklogSizePerInstance scaling metric.

---

To create a SageMaker endpoint for large image processing:

1. Create the model:
```bash
aws sagemaker create-model \
  --model-name async-vision-model \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-gpu-py310,ModelDataUrl=s3://ml-artifacts/vision/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

2. Create endpoint config:
```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name async-vision-config \
  --production-variants VariantName=AllTraffic,ModelName=async-vision-model,InstanceType=ml.g5.xlarge,InitialInstanceCount=1
```

3. Create the endpoint and use invoke-endpoint for predictions.
