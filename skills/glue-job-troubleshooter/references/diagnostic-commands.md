# Diagnostic Commands — Glue Job Troubleshooter

Diagnostic and pre-flight command listings moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Pre-flight: data gate — gather-info commands

```bash
# 1. Job-run metadata
RUN_ID=jr_abc123def456
aws glue get-job-run --job-name nightly-sales-aggregation \
  --run-id $RUN_ID --output json > job-run.json

# 2. Recent runs (was this the first failure?)
aws glue get-job-runs --job-name nightly-sales-aggregation \
  --max-results 20 --output json > job-runs.json

# 3. CloudWatch Logs for the failing run (/aws-glue/jobs/output)
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/output \
  --log-stream-name $RUN_ID --filter-pattern "ERROR" \
  --output json > job-errors.json

# 4. Bookmark state (for bookmark-stall category)
aws glue get-job-bookmark --job-name nightly-sales-aggregation \
  --run-id $RUN_ID --output json > bookmark.json

# 5. Spark UI event log (when enabled via --spark-event-logs-path)
LOG_PATH=$(jq -r '.JobRun.Arguments["--spark-event-logs-path"] // empty' job-run.json)
aws s3 cp "$LOG_PATH/$RUN_ID/" ./spark-ui/ --recursive
```

## Step 1 probe — Python traceback log filter

```bash
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/output \
  --log-stream-name $RUN_ID --filter-pattern "Traceback" \
  --output json
```

## Step 3 probe — Glue connection and network checks

```bash
aws glue get-connection --name nightly-rds-conn --output json > conn.json
CONN_SG=$(jq -r '.Connection.Properties.SECURITY_GROUP_ID' conn.json)
CONN_SUBNET=$(jq -r '.Connection.Properties.SUBNET_ID' conn.json)

aws ec2 describe-security-groups --group-ids $CONN_SG --output json
aws ec2 describe-security-groups --group-ids $DB_SG --output json
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=$CONN_SUBNET --output json
```

## Step 6 probe — Spark UI event log retrieval

```bash
LOG_BUCKET=$(jq -r '.JobRun.Arguments["--spark-event-logs-path"]' job-run.json)
aws s3 ls "$LOG_BUCKET/$RUN_ID/" --recursive
# Inspect with spark-events-reader or the Glue Console "Spark UI" tab
```

