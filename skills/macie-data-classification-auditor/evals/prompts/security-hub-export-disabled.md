# Eval prompt: security-hub-export-disabled

Audit the following Amazon Macie posture for data-classification coverage.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 444444444444, Region: us-east-1
Test case: security-hub-export-disabled

Macie session:
  status: ENABLED

Automated discovery (ASDD):
  status: ENABLED
  lastRunTime: 2026-08-04T14:00:00Z

Classification jobs:
  - jobId: security-hub-export-disabled
    name: weekly-pii-scan
    jobStatus: COMPLETE
    jobType: SCHEDULED
    lastRunTime: 2026-08-04T02:00:00Z
    samplingPercentage: 100
    buckets: [finance-reports]

Findings:
  - findingId: f-101
    severity: HIGH
    type: SensitiveData:S3Object/Financial
    archived: true
    resourceName: s3://finance-reports/q2-statement.csv

Allow lists: (none)

Security Hub export: disabled
