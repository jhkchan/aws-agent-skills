# Eval: backup-exports

**Difficulty:** easy
**Branch:** Rule 1 — BPA authoritative, no public configs

## Prompt

Audit this S3 bucket configuration and tell me whether it is publicly
accessible. Classify the exposure and provide remediation guidance.

```
Bucket: backup-exports
Block Public Access (account + bucket level):
  BlockPublicAcls: True
  IgnorePublicAcls: True
  BlockPublicPolicy: True
  RestrictPublicBuckets: True
ACL: private
Bucket Policy: (none)
```
