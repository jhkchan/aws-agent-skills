# Eval prompt: config-gap-legacy-no-resources

Audit the following CUR configuration for FinOps data pipeline health. Emit
the standard VERDICT block (REPORT, VERDICT, REASON, FINDINGS, REMEDIATION).

Account type: payer (management account)
Region: us-east-1
Evaluation date: 2026-08-04

describe-report-definitions output:

```json
{
  "ReportDefinitions": [
    {
      "ReportName": "config-gap-legacy-no-resources",
      "TimeUnit": "DAILY",
      "Format": "Parquet",
      "Compression": "Parquet",
      "AdditionalSchemaElements": [],
      "S3Bucket": "cur-bucket-shared",
      "S3Prefix": "reports/",
      "S3Region": "us-east-1",
      "AdditionalArtifacts": ["ATHENA"],
      "RefreshClosedReports": false,
      "ReportVersion": "legacy-v0"
    }
  ]
}
```

S3 latest manifest timestamp: 2026-08-03T12:00:00Z (less than 24 hours ago)
S3 bucket versioning: Enabled
