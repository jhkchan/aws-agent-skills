# Eval: logs-archive-2024

**Difficulty:** medium
**Branch:** Rule 3 — legacy ACL grant (AllUsers READ)

## Prompt

Audit this S3 bucket configuration and tell me whether it is publicly
accessible. Classify the exposure and provide remediation guidance.

```
Bucket: logs-archive-2024
Block Public Access (account + bucket level):
  BlockPublicAcls: False
  IgnorePublicAcls: False
  BlockPublicPolicy: False
  RestrictPublicBuckets: False
ACL: READ granted to http://acs.amazonaws.com/groups/global/AllUsers
Bucket Policy: (none)
```
