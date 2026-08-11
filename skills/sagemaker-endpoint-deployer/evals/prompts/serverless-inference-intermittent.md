# Eval: serverless-inference-intermittent

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — serverless with ProvisionedConcurrency=1, scale-to-zero when idle

## Prompt

Deploy a SageMaker Serverless Inference endpoint in us-east-1 for a
text classification model. Endpoint name "serverless-classifier".
Model artifact at s3://ml-artifacts/classifier/model.tar.gz.
Container image 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310.
Execution role arn:aws:iam::123456789012:role/SageMakerExecutionRole.
Traffic is intermittent — a few requests per hour. Serverless config:
MemorySizeInMB 2048, MaxConcurrency 10, ProvisionedConcurrency 1
for minimal warm capacity. KMS encryption with alias/sagemaker-key.
Tags: Environment=production, Workload=text-classification.
Account ID: 123456789012.
