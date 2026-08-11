# Baseline (no-skill) — missing-artifact-and-role

> This is the response a model produces **without** the skill definition.
> It provides generic CLI commands without checking that the model artifact
> exists in S3 or that the execution role is set up, proceeding to deployment
> with placeholders instead of catching the missing prerequisites.

---

To create a SageMaker endpoint:

1. Upload your model to S3:
```bash
aws s3 cp model.tar.gz s3://your-bucket/fraud-detection/model.tar.gz
```

2. Create the model:
```bash
aws sagemaker create-model \
  --model-name fraud-detection-model \
  --primary-container Image=<image>,ModelDataUrl=s3://your-bucket/fraud-detection/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/<your-role>
```

3. Create endpoint config:
```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name fraud-detection-config \
  --production-variants VariantName=AllTraffic,ModelName=fraud-detection-model,InstanceType=ml.c5.xlarge,InitialInstanceCount=2
```

4. Create endpoint and test.
