# Eval: kms-collection-face-index

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — KMS collection, ExternalImageId indexing, 85% face match threshold, IAM role with S3 access

## Prompt

Create a Rekognition collection "employee-faces" in us-east-1
with KMS encryption using key arn:aws:kms:us-east-1:123456789012:key/abcd-1234.
Index faces from S3 bucket my-face-bucket using ExternalImageId
employee-001. Set face search threshold to 85%. IAM role
arn:aws:iam::123456789012:role/RekognitionRole. Tags:
Environment=production, UseCase=employee-access.
