# Eval: endpoint-policy-deny

**Difficulty:** medium
**Branch:** ROOT_CAUSE_IDENTIFIED — custom endpoint policy allows only s3:GetObject and s3:ListBucket; s3:PutObject is denied at the endpoint policy layer despite IAM allowing it

## Prompt

Diagnose a Gateway VPC endpoint vpce-s3policy789 for S3.
Clients are getting HTTP 403 Access Denied when trying to upload
objects (s3:PutObject) to bucket my-data-bucket. The endpoint
policy only allows s3:GetObject and s3:ListBucket on
arn:aws:s3:::my-data-bucket. The IAM policy allows s3:PutObject.
The endpoint is available and in the correct route table.
