# Eval: export-s3-compliance

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — S3 bucket configured, IAM role for QLDB to write to S3, export time range documented

## Prompt

Create a QLDB ledger named regulatory-ledger in us-east-1 with
journal export to S3 for compliance audit. Permissions mode
STANDARD. Deletion protection. KMS key
arn:aws:kms:us-east-1:123456789012:key/export789. S3 bucket
qldb-regulatory-export. IAM role QLDBExportRole. Export time range
2026-01-01 to 2026-12-31. Tags: Environment=production,
Compliance=GDPR.
