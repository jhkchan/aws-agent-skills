# Eval: full-deploy-with-replication

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all items including CRR replication + MFA Delete

## Prompt

Provision a production backup bucket named "prod-backup-primary"
in us-east-1 with CRR to "prod-backup-dr" in us-west-2. Use
SSE-KMS (alias/prod-backup-key in us-east-1,
alias/prod-backup-key-dr in us-west-2). Enable MFA delete,
versioning, lifecycle: GLACIER@90d then DEEP_ARCHIVE@180d,
expire noncurrent@365d. Access logging to "s3-access-logs-prod".
CloudTrail data events on trail "management-trail". Tags:
Environment=production, Workload=backup. Account: 123456789012.
