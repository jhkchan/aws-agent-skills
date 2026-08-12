# Eval: tag-policy-enforced-for

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — TAG_POLICIES policy type, Environment/Owner tags enforced on ec2:instance and s3:bucket

## Prompt

Create a tag policy named mandatory-tag-policy that enforces
two tags: Environment (AllowedValues: dev, staging, production;
EnforcedFor ec2:instance and s3:bucket) and Owner
(CaseSensitive true). Attach to root r-xxxx. The organization
has TAG_POLICIES already enabled. Management account
123456789012.
