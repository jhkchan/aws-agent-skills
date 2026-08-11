# Eval: multi-class-endpoint

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — multi-class mode, CSV training data, endpoint inference with auto-scaling, KMS encryption for model and volume

## Prompt

Train a Comprehend custom document classifier named
support-ticket-classifier. Multi-class mode, English, plain text
input. Training data is a CSV at
s3://my-bucket/comprehend/training/training.csv with 5000
documents across 5 classes (billing, technical, general, sales,
refund). Each class has at least 800 documents. Deploy a
real-time endpoint named ticket-endpoint with 1 inference unit
and auto-scaling (min 1, max 5). Encrypt model artifacts and
volume with KMS key arn:aws:kms:us-east-1:123456789012:key/abcd1234.
IAM role arn:aws:iam::123456789012:role/ComprehendTrainingRole.
Region us-east-1. Tags: Environment=production, Team=support.
