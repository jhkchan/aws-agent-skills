# Eval: static-assets-cdn

**Difficulty:** easy
**Branch:** READY_TO_DEPLOY — CDN workload with SSE-S3 (cost-sensitive)

## Prompt

Create an S3 bucket for static website assets served via
CloudFront. Name: "cdn-assets-prod", region: us-east-1.
This is a CDN origin so it will be accessed frequently.
Use SSE-S3 encryption (cost-sensitive, not compliance data).
No lifecycle needed (frequently accessed). Access logging to
"s3-access-logs-prod". Account: 123456789012.
