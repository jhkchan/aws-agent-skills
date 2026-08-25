# Advanced Patterns — Timestream Database Deployer

Edge-case catalog and recent-feature notes moved verbatim from SKILL.md. Loaded on demand.

## Step 9 — Batch load task

```bash
# Create a batch load task
aws timestream-write create-batch-load-task \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --data-source-configuration \
    "DataSourceS3Configuration={BucketName='historical-sensor-data',ObjectKeyPrefix='2025/'}" \
  --report-configuration \
    "ReportS3Configuration={BucketName='batch-load-reports',ObjectKeyPrefix='reports/2025/'}" \
  --region us-east-1

# Check batch load task status
aws timestream-write describe-batch-load-task \
  --task-id "task-abc123" \
  --region us-east-1
```

**Batch load task stages:**

| Stage | Description |
|---|---|
| PENDING | Task created, waiting to start |
| LOADING | Data is being ingested |
| SUCCEEDED | All records loaded successfully |
| FAILED | Task failed (check report for details |
| CANCELLED | Task was cancelled by the operator |

**CSV format requirements:** the data source CSV must have a header
row with columns matching the Timestream table schema. Dimensions,
measures, and time columns must be present.

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Partition key enforcement (2023-2024):** Enforce partition key
  dimensions at write time for improved query performance on
  high-cardinality tables. Records missing the partition key dimension
  are rejected (REQUIRED mode) or accepted without enforcement
  (OPTIONAL mode).

- **Magnetic store write properties (2023-2024):** Enable late-arrival
  data ingestion via S3. Records with timestamps older than the memory
  store TTL are routed to an S3 bucket and ingested into the magnetic
  store, preventing data loss.

- **Batch load task (2023-2024):** Bulk ingestion of historical data
  from S3 (CSV or Parquet) into Timestream tables. Asynchronous task
  with progress tracking and detailed error reporting.

- **Scheduled query improvements (2023-2025):** Enhanced scheduled
  query error reporting with S3 error report configuration. SNS
  notification improvements for real-time alerting on query failures.

- **CloudWatch metrics enhancements (2024-2025):** Additional
  CloudWatch metrics for magnetic store write monitoring and batch
  load task progress tracking.

- **Dimension insights optimization (2024-2025):** Optimize partition
  key access patterns for common dimension queries, reducing scan
  volume and cost for analytical workloads.

- **Terraform provider maturity (2023-2025):** Full Terraform support
  for `aws_timestreamwrite_database`, `aws_timestreamwrite_table`
  (with magnetic store write properties and partition key enforcement),
  and `aws_timestreamquery_scheduled_query` resources.
