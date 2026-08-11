# Eval: https-only-secure-transport

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — aws:SecureTransport with Bool operator (not StringNotEquals), BucketOwnerEnforced, BPA all 4 True

## Prompt

Attach an HTTPS-only policy to bucket "prod-app-data" in
us-east-1 (account 123456789012). Deny all non-HTTPS S3
traffic. Also disable ACLs with BucketOwnerEnforced and
enable Block Public Access (all 4 settings). Bucket exists
and has no existing policy.
