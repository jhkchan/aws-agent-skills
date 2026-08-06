# Eval prompt: job-failed-no-coverage

Audit the following Amazon Macie posture for data-classification coverage.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 222222222222, Region: us-east-1
Test case: job-failed-no-coverage

Macie session:
  status: ENABLED

Automated discovery (ASDD):
  status: DISABLED

Classification jobs:
  - jobId: job-failed-no-coverage
    name: pii-scan-prod
    jobStatus: FAILED
    jobType: SCHEDULED
    lastRunTime: 2026-07-01T10:00:00Z
    samplingPercentage: 100
    buckets: [prod-data-lake]

Findings: (none — job never completed successfully)

Allow lists: (none)

Security Hub export: disabled

S3 buckets in account: prod-data-lake, analytics-export (2 buckets)
