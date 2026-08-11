# Eval: moderation-and-labels-pipeline

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — content moderation min confidence 60%, label detection max 50, SNS topic for async jobs

## Prompt

Create a Rekognition content moderation and label detection
pipeline in us-east-1. Min moderation confidence: 60%. Max labels:
50, min label confidence: 75%. Async video jobs from S3 bucket
my-video-bucket. SNS notification topic:
arn:aws:sns:us-east-1:123456789012:rekognition-complete. IAM role
for SNS: arn:aws:iam::123456789012:role/RekognitionSNSRole. Tags:
Environment=production, Pipeline=moderation.
