# Eval: native-pdf-vpc-kms

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Native PDF input mode, Augmented Manifest with S3 URIs, VPC config for training, KMS encryption, endpoint deployment

## Prompt

Train a Comprehend custom document classifier named
document-type-classifier. Multi-class mode, English. Native PDF
input — training data is PDF documents referenced in an Augmented
Manifest at s3://my-bucket/docs/training/pdf_manifest.jsonl.
Labels: invoice, contract, report, letter, memo. 3000 documents
total, each class has at least 500 PDFs. Train inside VPC with
subnets subnet-aaa, subnet-bbb and security group sg-abc123.
Encrypt with KMS key
arn:aws:kms:us-east-1:123456789012:key/efgh5678. IAM role
arn:aws:iam::123456789012:role/ComprehendSecureRole. Deploy
endpoint doc-classifier-endpoint with 2 inference units. Region
us-east-1. Tags: Environment=production, Compliance=HIPAA.
