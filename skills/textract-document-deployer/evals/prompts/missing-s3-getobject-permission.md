# Eval: missing-s3-getobject-permission

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — IAM role has s3:PutObject on output and textract:Start* but NO s3:GetObject on input bucket; Textract cannot read documents

## Prompt

Set up an async Textract pipeline for
s3://doc-input/invoices/2026-q3.pdf in us-east-1. Forms + Tables.
Output to s3://doc-output/textract/. The IAM role is
arn:aws:iam::123456789012:role/TextractProcessingRole — it has
s3:PutObject on the output bucket and textract:Start* but NO
s3:GetObject permission on the input bucket.
