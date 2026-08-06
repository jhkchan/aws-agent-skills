# Eval: internal-reports-finance

**Difficulty:** hard
**Branch:** Rule 4 — condition-restricted wildcard (strong VPCe condition)

## Prompt

Audit this S3 bucket configuration and tell me whether it is publicly
accessible. Classify the exposure and provide remediation guidance.

```
Bucket: internal-reports-finance
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
      Resource: "arn:aws:s3:::internal-reports-finance/*"
      Condition:
        StringEquals:
          aws:sourceVpce: "vpce-1a2b3c4d5e6f7g8h9"
```
