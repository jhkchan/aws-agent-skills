# Eval: secure-compliance-bucket

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, SSE-KMS + MFA Delete + lifecycle

## Prompt

Provision a production S3 bucket named "compliance-archive-2024"
in us-east-1 for compliance workloads (HIPAA). Use SSE-KMS with
customer-managed CMK (alias/compliance-s3-key), enable versioning
with MFA delete, access logging to "s3-access-logs-prod", CloudTrail
data events on trail "aws-controltower-trail", lifecycle:
STANDARD_IA@30d then GLACIER@90d then DEEP_ARCHIVE@365d, expire
noncurrent versions at 180d. Tags: Environment=production,
DataClassification=phi. Account ID: 123456789012.
