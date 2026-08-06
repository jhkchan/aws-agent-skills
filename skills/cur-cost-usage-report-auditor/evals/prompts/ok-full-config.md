# Eval prompt: ok-full-config

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
      "ReportName": "ok-full-config",
      "TimeUnit": "HOURLY",
      "Format": "Parquet",
      "Compression": "Parquet",
      "AdditionalSchemaElements": ["Resources"],
      "S3Bucket": "cur-bucket-prod",
      "S3Prefix": "cur/",
      "S3Region": "us-east-1",
      "AdditionalArtifacts": ["ATHENA"],
      "RefreshClosedReports": true,
      "ReportVersion": "cur-1.0"
    }
  ]
}
```

S3 latest manifest timestamp: 2026-08-04T08:00:00Z (2 hours ago)
S3 bucket versioning: Enabled
