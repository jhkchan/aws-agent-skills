# Eval prompt: broad-allow-list-masking

Audit the following Amazon Macie posture for data-classification coverage.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 555555555555, Region: us-east-1
Test case: broad-allow-list-masking

Macie session:
  status: ENABLED

Automated discovery (ASDD):
  status: ENABLED
  lastRunTime: 2026-08-04T14:00:00Z

Classification jobs:
  - jobId: broad-allow-list-masking
    name: data-lake-scan
    jobStatus: RUNNING
    jobType: SCHEDULED
    lastRunTime: 2026-08-04T06:00:00Z
    samplingPercentage: 100
    buckets: [data-lake]

Findings:
  - findingId: f-201
    severity: MEDIUM
    type: SensitiveData:S3Object/Personal
    archived: true
    resourceName: s3://data-lake/uploads/contacts.csv

Allow lists:
  - id: al-001
    name: suppress-data-lake-logs
    criteria:
      s3Bucket: data-lake
      s3Prefix: "*"
    description: Suppress all findings in data-lake bucket

Security Hub export: enabled
