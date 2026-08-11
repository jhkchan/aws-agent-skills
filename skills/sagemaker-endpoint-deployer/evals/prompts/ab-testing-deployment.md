# Eval: ab-testing-deployment

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — A/B testing with two variants, same instance type, weighted traffic

## Prompt

Set up A/B testing on a SageMaker endpoint "ab-churn-endpoint" in
us-east-1. Two models: "churn-model-v1" (artifact s3://ml/churn-v1/model.tar.gz)
and "churn-model-v2" (artifact s3://ml/churn-v2/model.tar.gz). Both
use the same container image 763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1.
Execution role arn:aws:iam::123456789012:role/SageMakerExecutionRole.
Instance type ml.c5.xlarge, 2 instances each. Traffic split 90% to
variantA (v1), 10% to variantB (v2). Data capture enabled at 50%
sampling. KMS encryption with alias/sagemaker-key. Tags:
Environment=staging, Workload=churn-ab-test.
Account ID: 123456789012.
