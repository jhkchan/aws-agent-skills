# Eval prompt: healthy-macie-posture

Audit the following Amazon Macie posture for data-classification coverage.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 666666666666, Region: us-east-1
Test case: healthy-macie-posture

Macie session:
  status: ENABLED

Automated discovery (ASDD):
  status: ENABLED
  lastRunTime: 2026-08-04T14:00:00Z

Classification jobs:
  - jobId: healthy-macie-posture
    name: compliance-full-scan
    jobStatus: COMPLETE
    jobType: SCHEDULED
    lastRunTime: 2026-08-04T02:00:00Z
    samplingPercentage: 100
    buckets: [prod-app-data, prod-user-uploads]

Findings:
  - findingId: f-301
    severity: HIGH
    type: SensitiveData:S3Object/Personal
    archived: true
    resourceName: s3://prod-user-uploads/2026/q3/backup-contacts.csv
    classificationDetails:
      sensitiveData:
        - category: PERSONAL_INFORMATION
          detectedDataType: US_SOCIAL_SECURITY_NUMBER
          count: 500

Allow lists:
  - id: al-002
    name: suppress-known-test-data
    criteria:
      s3Bucket: prod-app-data
      s3Prefix: test-fixtures/sample-users.json
    description: Suppress known test fixture that contains synthetic SSNs

Security Hub export: enabled
