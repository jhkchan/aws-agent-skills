# Eval: public-assets-cdn

**Difficulty:** medium
**Branch:** Rule 2 — unrestricted wildcard Allow (read-only, HIGH severity)

## Prompt

Audit this S3 bucket configuration and tell me whether it is publicly
accessible. Classify the exposure and provide remediation guidance.

```
Bucket: public-assets-cdn
Block Public Access (account + bucket level):
  BlockPublicAcls: False
  IgnorePublicAcls: False
  BlockPublicPolicy: False
  RestrictPublicBuckets: False
ACL: private
Bucket Policy:
  Version: "2012-10-17"
  Statement:
    - Effect: Allow
      Principal: "*"
      Action: "s3:GetObject"
      Resource: "arn:aws:s3:::public-assets-cdn/*"
```
