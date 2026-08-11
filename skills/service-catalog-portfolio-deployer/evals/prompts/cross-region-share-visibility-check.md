# Eval: cross-region-share-visibility-check

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — region mismatch documented, replication via StackSets recommended

## Prompt

Provision portfolio "Multi-Region S3" by "Platform Governance"
in us-east-1 with the S3-bucket product and full constraints
(LAUNCH sc-launch-s3-role, TAG_UPDATE NOT_ALLOWED). The consumer
accounts are in eu-west-1 and ap-southeast-1. TagOptions
CostCenter=platform-1234. Share with ORGANIZATION o-abc123def456
(Organizations enabled). Multi-region rollout is required.
