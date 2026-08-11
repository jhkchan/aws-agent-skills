# Baseline (no-skill) — ab-testing-deployment

> This is the response a model produces **without** the skill definition.
> It produces generic create-endpoint-config with two variants but misses
> the same-instance-type requirement (confounds comparison), data capture
> enablement for offline analysis, the weight-shifting guidance, and the
> READY_TO_DEPLOY checklist format.

---

To set up A/B testing on SageMaker:

1. Create both models:
```bash
aws sagemaker create-model --model-name churn-model-v1 \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1,ModelDataUrl=s3://ml/churn-v1/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole

aws sagemaker create-model --model-name churn-model-v2 \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1,ModelDataUrl=s3://ml/churn-v2/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

2. Create endpoint config with two variants:
```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name ab-churn-config \
  --production-variants '[{"VariantName":"variantA","ModelName":"churn-model-v1","InstanceType":"ml.c5.xlarge","InitialInstanceCount":1,"InitialVariantWeight":9},{"VariantName":"variantB","ModelName":"churn-model-v2","InstanceType":"ml.t3.medium","InitialInstanceCount":1,"InitialVariantWeight":1}]'
```

3. Create the endpoint and test.
