# Eval: app-data-prod

**Difficulty:** medium
**Branch:** Rule 1 — BPA authoritative (Deny policy is a red herring)

## Prompt

Audit this S3 bucket configuration and tell me whether it is publicly
accessible. Classify the exposure and provide remediation guidance.

```
Bucket: app-data-prod
Block Public Access (account + bucket level):
  BlockPublicAcls: True
  IgnorePublicAcls: True
  BlockPublicPolicy: True
  RestrictPublicBuckets: True
ACL: private
Bucket Policy:
  Version: "2012-10-17"
  Statement:
    - Effect: Deny
      Principal: "*"
      Action: "s3:*"
      Resource:
        - "arn:aws:s3:::app-data-prod"
        - "arn:aws:s3:::app-data-prod/*"
      Condition:
        Bool:
          aws:SecureTransport: false
```
