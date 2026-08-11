# Baseline (no-skill) response: linked-account-caller-manual

This file captures what a generic assistant produces WITHOUT the
cur-automation-automator skill loaded — the contrast that proves the
skill catches the payer-only CUR restriction.

---

To set up CUR for organization-wide FinOps from your account
222222222222:

1. Open the Billing console and navigate to Cost and Usage Reports.
2. Click "Create report" and configure:
   - Report name: `org-cur-hourly`
   - Time unit: Hourly
   - Format: Parquet
   - S3 bucket: create a new bucket in us-east-1
3. Wait 24 hours for the first delivery.

Once the report is delivered, set up Athena to query it:

```sql
CREATE EXTERNAL TABLE cur_data (...)
PARTITIONED BY (year, month, day)
STORED AS PARQUET
LOCATION 's3://your-bucket/cur/org-cur-hourly/';
```

You should be good to go. Let me know if you run into any permission
issues.
