# Eval: basic-s3-oac

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — standard OAC with S3 origin, always-sign signing, bucket policy with cloudfront.amazonaws.com and AWS:SourceArn

## Prompt

Create a CloudFront Origin Access Control for distribution
EDFDVBD6EXAMPLE serving S3 bucket my-assets-bucket in us-east-1.
Account 111122223333. The bucket is private (no website hosting).
Use sigv4 signing with always-sign behavior. Tags:
Environment=production, Team=platform.
