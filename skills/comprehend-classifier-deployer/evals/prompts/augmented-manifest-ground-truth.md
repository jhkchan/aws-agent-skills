# Eval: augmented-manifest-ground-truth

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — multi-class mode, Augmented Manifest from SageMaker Ground Truth, endpoint inference

## Prompt

Train a Comprehend custom document classifier named
review-sentiment-classifier. Multi-class mode, English. Training
data is an Augmented Manifest produced by SageMaker Ground Truth
at s3://my-bucket/reviews/labeled/manifest.jsonl. 12000 reviews
across 3 sentiment classes (positive, negative, neutral). Each
class has at least 3500 labeled reviews. Use endpoint inference
with endpoint name review-endpoint, 1 inference unit. IAM role
arn:aws:iam::123456789012:role/ComprehendRole. Region us-east-1.
Tags: Environment=staging, Source=ground-truth.
