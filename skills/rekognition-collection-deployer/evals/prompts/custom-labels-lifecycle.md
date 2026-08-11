# Eval: custom-labels-lifecycle

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — custom labels project created, training data in S3, model started with 1 inference unit

## Prompt

Create a Rekognition custom labels project "industrial-defects" in
us-east-1. Training data manifest at
s3://my-bucket/training/manifest.json. Model output bucket:
my-bucket/model-output/. Start model with 1 inference unit. IAM
role: arn:aws:iam::123456789012:role/RekognitionCustomLabelsRole.
Tags: Environment=production, UseCase=defect-detection.
