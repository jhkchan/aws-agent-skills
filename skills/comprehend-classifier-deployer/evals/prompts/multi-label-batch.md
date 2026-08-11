# Eval: multi-label-batch

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — multi-label mode, Augmented Manifest training data, batch inference for cost efficiency on nightly 50k-doc workload

## Prompt

Train a Comprehend custom document classifier named
news-tag-classifier. Multi-label mode, English, plain text.
Training data is an Augmented Manifest at
s3://my-bucket/news/training/manifest.jsonl with 8000 documents.
Labels: politics, economy, world, sports, technology, health.
Each label has at least 500 documents. Use batch inference (not
endpoint) for cost efficiency — we process 50000 articles nightly.
Input at s3://my-bucket/news/input/, output at
s3://my-bucket/news/output/. IAM role
arn:aws:iam::123456789012:role/ComprehendBatchRole. Region
us-east-1. Tags: Environment=production, Pipeline=news-tagging.
