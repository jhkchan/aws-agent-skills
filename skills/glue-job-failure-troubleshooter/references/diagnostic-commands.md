# Diagnostic Commands — Glue Job Failure Troubleshooter

Diagnostic and pre-flight command listings moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Pre-flight commands

```bash
# 1. Job configuration (WorkerType, NumberOfWorkers, Timeout, GlueVersion,
#    SecurityConfiguration, Arguments, Command, Role)
aws glue get-job --job-name <name> --output json

# 2. Job run details (state, execution time, error message, arguments)
aws glue get-job-run --job-name <name> --run-id <run-id> --output json

# 3. Recent job runs (state transitions, failure patterns)
aws glue get-job-runs --job-name <name> --output json

# 4. CloudWatch Logs for the failed run
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/default \
  --filter-pattern '"Container killed by YARN" OR "Table not found" OR "Connection timed out" OR "OutOfMemoryError"' \
  --start-time $(date -d '-2 hours' +%s)000 --output json

# 5. Security configuration (CloudWatch encryption, S3 encryption, KMS key)
aws glue get-security-configuration --name <sec-config-name> --output json 2>/dev/null
```

## Step 3 probe — table existence (get-table)

```bash
aws glue get-table --database <database> --name <table> --output json
```

## Step 3 probe — database existence (get-database)

```bash
aws glue get-database --name <database> --output json
```

## Step 4 probe — catalog location and S3 listing

```bash
# Check the table's StorageDescriptor.Location
aws glue get-table --database <db> --name <table> --output json | \
  jq '.Table.StorageDescriptor.Location'

# Verify the S3 path exists and has objects
aws s3 ls s3://<bucket>/<prefix>/ --recursive | head -20
```

## Step 4 example — hardcoded S3 path bypassing the catalog

```python
# In the script — this bypasses the Data Catalog
datasource = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": ["s3://wrong-bucket/data/"]},
    format="parquet")
```

## Step 5 probe — partition count

```bash
aws glue get-partitions --database <db> --table-name <table> --output json | \
  jq '.Partitions | length'
```

## Step 5 fix — MSCK REPAIR / crawler

```bash
# Option 1: MSCK REPAIR TABLE (via Athena)
aws athena start-query-execution \
  --query-string "MSCK REPAIR TABLE <database>.<table>" \
  --work-group <workgroup> --output json

# Option 2: Run a Glue crawler on the S3 path
aws glue start-crawler --name <crawler-name>
```

## Step 8 probe — timeout vs execution time

```bash
aws glue get-job --job-name <name> --output json | jq '.Job.Timeout'
aws glue get-job-run --job-name <name> --run-id <run-id> --output json | \
  jq '.JobRun.{ExecutionTime, CompletedOn, ErrorMessage}'
```

## Step 9 probe — logs encryption and role permissions

```bash
# Check if the job has a security configuration with CloudWatch encryption
aws glue get-job --job-name <name> --output json | \
  jq '.Job.SecurityConfiguration'

# Check the IAM role for logs permissions
ROLE_NAME=$(aws glue get-job --job-name <name> --output json | jq -r '.Job.Role' | cut -d/ -f2)
aws iam list-attached-role-policies --role-name "$ROLE_NAME" --output json
```

## Step 10 probe — Python traceback filter

```bash
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/default \
  --filter-pattern '"Traceback" OR "py4j" OR "PythonException"' \
  --start-time $(date -d '-2 hours' +%s)000 --output json
```

## Step 11 probe — metrics enablement

```bash
# Check if metrics are enabled
aws glue get-job --job-name <name> --output json | \
  jq '.Job.DefaultArguments["--enable-metrics"]'
```

