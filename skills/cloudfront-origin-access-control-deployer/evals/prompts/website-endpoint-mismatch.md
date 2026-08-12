# Eval: website-endpoint-mismatch

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — bucket has static website hosting enabled; OAC only supports the S3 origin type, not Website Endpoint

## Prompt

Create a CloudFront OAC for distribution E4EXAMPLE4XXX serving
S3 bucket my-website-bucket in us-east-1, account 111122223333.
The bucket has static website hosting enabled with index.html
as the index document. Tags: Environment=production.
