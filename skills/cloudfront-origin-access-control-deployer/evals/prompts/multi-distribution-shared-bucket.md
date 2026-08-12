# Eval: multi-distribution-shared-bucket

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — three distributions each with own OAC, bucket policy lists all distribution ARNs in AWS:SourceArn condition

## Prompt

Create OACs for three CloudFront distributions
(EDFDVBD6EXAMPLE, E2QWRUEXAMPLE2, E3EXAMPLE3XXX) all serving
from S3 bucket shared-content-bucket in us-east-1, account
111122223333. Each distribution needs its own OAC. The bucket
is private, no SSE-KMS. Tags: Environment=production,
Pattern=multi-distribution.
