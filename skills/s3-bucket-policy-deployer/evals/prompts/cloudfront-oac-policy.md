# Eval: cloudfront-oac-policy

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cloudfront.amazonaws.com service principal, AWS:SourceArn condition, OAC config verified

## Prompt

Set up a CloudFront OAC bucket policy for bucket
"cdn-origin-assets" in us-east-1 (account 123456789012).
CloudFront distribution ARN:
arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456.
Allow s3:GetObject on all objects. The OAC config already
exists in CloudFront. HTTPS-only Deny should also be present.
ACLs disabled, BPA enabled.
