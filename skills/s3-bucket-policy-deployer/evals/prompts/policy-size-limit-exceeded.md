# Eval: policy-size-limit-exceeded

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — policy JSON is 24 KB, exceeds the 20 KB S3 bucket policy limit; Access Points recommended

## Prompt

Attach a bucket policy to bucket "large-policy-bucket" in
us-east-1 (account 123456789012). The policy JSON file is
24 KB (exceeds the 20 KB S3 limit). It contains per-team
Allow statements for 15 teams. The bucket exists with BPA
enabled.
