# SageMaker Endpoint Deployer — Worked Examples and Boilerplate Patterns

Boilerplate CLI bundles, moved verbatim from SKILL.md. The primary worked example stays in SKILL.md.

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

