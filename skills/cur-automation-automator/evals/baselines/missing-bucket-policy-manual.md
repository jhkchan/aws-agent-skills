# Baseline (no-skill) response: missing-bucket-policy-manual

This file captures what a generic assistant produces WITHOUT the
cur-automation-automator skill loaded — the contrast that proves the
skill catches the missing athena.amazonaws.com principal in the bucket
policy before applying.

---

Here's a CloudFormation template for your CUR automation stack:

```yaml
Resources:
  CURReport:
    Type: AWS::CUR::ReportDefinition
    Properties:
      ReportName: prod-cur-hourly
      TimeUnit: HOURLY
      Format: Parquet
      S3Bucket: prod-cur-bucket
      S3Prefix: cur/
      S3Region: us-east-1
```

After the stack creates, wait 24 hours and then in Athena run:

```sql
CREATE EXTERNAL TABLE cur_data (...)
PARTITIONED BY (year, month, day)
LOCATION 's3://prod-cur-bucket/cur/prod-cur-hourly/';
```

That should work. Let me know if you have any issues.
