# Eval prompt: untriaged-high-pii-findings

Audit the following Amazon Macie posture for data-classification coverage.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 333333333333, Region: us-east-1
Test case: untriaged-high-pii-findings

Macie session:
  status: ENABLED

Automated discovery (ASDD):
  status: ENABLED
  lastRunTime: 2026-08-04T14:00:00Z

Classification jobs:
  - jobId: untriaged-high-pii-findings
    name: full-pii-scan
    jobStatus: COMPLETE
    jobType: ONE_TIME
    lastRunTime: 2026-08-04T12:00:00Z
    samplingPercentage: 100
    buckets: [customer-data, app-config]

Findings (open, archived: false):
  - findingId: f-001
    severity: HIGH
    type: SensitiveData:S3Object/Credentials
    category: CLASSIFICATION
    archived: false
    resourceName: s3://customer-data/exports/q3-customers.csv
    classificationDetails:
      sensitiveData:
        - category: CREDENTIALS
          detectedDataType: AWS_CREDENTIALS
          count: 1
  - findingId: f-002
    severity: HIGH
    type: SensitiveData:S3Object/Personal
    category: CLASSIFICATION
    archived: false
    resourceName: s3://customer-data/exports/q3-customers.csv
    classificationDetails:
      sensitiveData:
        - category: PERSONAL_INFORMATION
          detectedDataType: US_SOCIAL_SECURITY_NUMBER
          count: 45000
  - findingId: f-003
    severity: HIGH
    type: SensitiveData:S3Object/Financial
    category: CLASSIFICATION
    archived: false
    resourceName: s3://customer-data/exports/payment-history.csv
    classificationDetails:
      sensitiveData:
        - category: FINANCIAL_INFORMATION
          detectedDataType: CREDIT_CARD_NUMBER
          count: 12000

Allow lists: (none)

Security Hub export: enabled
