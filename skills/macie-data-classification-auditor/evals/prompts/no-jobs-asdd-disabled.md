# Eval prompt: no-jobs-asdd-disabled

Audit the following Amazon Macie posture for data-classification coverage.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111, Region: us-east-1
Test case: no-jobs-asdd-disabled

Macie session:
  status: ENABLED
  createdAt: 2026-01-15T00:00:00Z

Automated discovery (ASDD):
  status: DISABLED
  lastRunTime: null

Classification jobs: (none)

Findings: (none)

Allow lists: (none)

Security Hub export: disabled

S3 buckets in account: customer-data, app-uploads, backups (3 buckets, ~500 GB total)
