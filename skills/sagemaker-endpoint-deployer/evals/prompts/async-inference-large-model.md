# Eval: async-inference-large-model

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — async with S3 queueing, SNS notification, scale-to-zero

## Prompt

Deploy a SageMaker Asynchronous Inference endpoint in us-east-1 for
a computer vision model that processes large images. Endpoint name
"async-vision". Model artifact at s3://ml-artifacts/vision/model.tar.gz.
Container image 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-gpu-py310.
Execution role arn:aws:iam::123456789012:role/SageMakerExecutionRole.
Instance type ml.g5.xlarge, initial count 1 (scale to 0 when idle).
Async output to s3://async-output/vision/ with SNS success topic
arn:aws:sns:us-east-1:123456789012:vision-success and error topic
arn:aws:sns:us-east-1:123456789012:vision-error. Auto-scaling on
ApproximateBacklogSizePerInstance with target 5, min 0, max 4.
KMS encryption with alias/sagemaker-key. Tags: Environment=production,
Workload=computer-vision-async.
Account ID: 123456789012.
