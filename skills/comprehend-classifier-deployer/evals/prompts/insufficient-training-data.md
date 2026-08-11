# Eval: insufficient-training-data

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — billing class has only 30 docs, below the 50-doc minimum per class

## Prompt

Train a Comprehend custom document classifier named
email-router-classifier. Multi-class mode, English. Training data
is CSV at s3://my-bucket/email/training/training.csv. 4 classes:
sales (200 docs), support (150 docs), billing (30 docs), general
(180 docs). Deploy endpoint email-endpoint with 1 inference unit.
IAM role arn:aws:iam::123456789012:role/ComprehendRole. Region
us-east-1.
