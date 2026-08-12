# Eval: temp-credentials-batch-execute

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — temp creds via GetClusterCredentials, AutoCreate true, DurationSeconds 3600, sequential batch execution

## Prompt

Create a Redshift Data API batch execution configuration for
cluster analytics-cluster, database reports. Use temporary
credentials via GetClusterCredentials with DbUser
iam_report_user, DurationSeconds 3600, AutoCreate true. Batch
contains: CREATE TEMP TABLE temp_sales AS SELECT * FROM sales,
SELECT COUNT(*) FROM temp_sales, DROP TABLE temp_sales.
Tags: Environment=production, Workflow=batch-reports.
