# Baseline (no-skill) — real-time-endpoint-production

> This is the response a model produces **without** the skill definition.
> It produces generic create-model / create-endpoint-config / create-endpoint
> commands but misses the auto-scaling registration (not enabled by default),
> data capture configuration, model monitoring baseline, the 2-instance HA
> rationale, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To create a SageMaker real-time endpoint:

1. Create the model:
```bash
aws sagemaker create-model \
  --model-name prod-recommendation-model \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310,ModelDataUrl=s3://ml-artifacts/models/rec/model.tar.gz \
  --execution-role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

2. Create the endpoint config:
```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name prod-recommendation-config \
  --production-variants VariantName=AllTraffic,ModelName=prod-recommendation-model,InstanceType=ml.c5.xlarge,InitialInstanceCount=1
```

3. Create the endpoint:
```bash
aws sagemaker create-endpoint \
  --endpoint-name prod-recommendation \
  --endpoint-config-name prod-recommendation-config
```

4. Test it with invoke-endpoint.
