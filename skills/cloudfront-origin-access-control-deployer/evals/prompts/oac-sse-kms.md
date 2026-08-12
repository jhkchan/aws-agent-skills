# Eval: oac-sse-kms

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SSE-KMS bucket requires sigv4 always-sign, S3 bucket policy, AND KMS key policy granting cloudfront.amazonaws.com kms:Decrypt

## Prompt

Create a CloudFront OAC for distribution E2QWRUEXAMPLE2 serving
S3 bucket my-secure-data-bucket in us-east-1, account 111122223333.
The bucket is encrypted with SSE-KMS using key
arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab.
No website hosting. Tags: Environment=production, Encryption=sse-kms.
