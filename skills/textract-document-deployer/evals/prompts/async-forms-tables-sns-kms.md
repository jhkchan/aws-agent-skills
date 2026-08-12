# Eval: async-forms-tables-sns-kms

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — async StartDocumentAnalysis, 1450-page PDF, FORMS+TABLES, OutputConfig to customer S3, KMS on input+output, SNS notification role

## Prompt

Set up an async Textract pipeline for a 1450-page PDF invoice bundle
at s3://doc-input/invoices/2026-q3.pdf in us-east-1. Extract Forms
and Tables. Write structured output to s3://doc-output/textract/
(same region). Encrypt with KMS key
arn:aws:kms:us-east-1:123456789012:key/abcd1234.... Notify SNS topic
arn:aws:sns:us-east-1:123456789012:TextractComplete on completion.
IAM role arn:aws:iam::123456789012:role/TextractProcessingRole. Tag
Project=invoice-automation.
