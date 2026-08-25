# Retention Properties and Scheduled Queries — Timestream Database Deployer

Deep reference on memory store and magnetic store retention TTL
configuration (the two-tier storage model, cost implications, TTL
updates), scheduled query mechanics (target table, notification
configuration, execution role, error reporting), and the relationship
between retention properties and scheduled query freshness. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Two-tier storage model

### Memory store vs magnetic store

Amazon Timestream uses a two-tier storage architecture:

```text
Record written via WriteRecords API
  → Enters memory store
    → Queryable at sub-second latency (in-memory scan)
    → Billed per GB-hour (higher rate)
  → After memory_store_ttl expires:
    → Transitions to magnetic store
      → Queryable at seconds latency (disk-based scan)
      → Billed per GB-hour (lower rate)
  → After magnetic_store_ttl expires:
    → Permanently deleted (no recovery)
```

### TTL configuration

```bash
# Create table with specific TTLs
aws timestream-write create-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=12,MagneticStoreRetentionPeriodInDays=365"

# Update TTLs (applies to new data; existing data is not affected retroactively)
aws timestream-write update-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=24,MagneticStoreRetentionPeriodInDays=730"
```

### TTL tuning guidelines

| Workload type | Recommended memory store TTL | Rationale |
|---|---|---|
| Real-time monitoring (last 15 min) | 15 min - 1 hour | Hot queries access only recent data |
| Near-real-time dashboards (last 12h) | 12 hours | Dashboard queries span a half-day window |
| Historical analysis (months/years) | 1 hour + scheduled queries | Pre-compute aggregates; avoid memory store for long ranges |
| Debugging / forensics | 1 hour + magnetic store 730 days | Keep raw data long; query from magnetic store as needed |

### Cost impact of memory store TTL

Memory store charges are per GB-hour. Example:

```text
Table ingestion rate: 50 GB/day
Memory store TTL:     24 hours (1 day)

Data in memory store at steady state: 50 GB
Memory store cost: 50 GB * memory-store-rate-per-GB-hour * 24 hours/day

If TTL is increased to 7 days:
Data in memory store: 350 GB
Memory store cost: 7x higher

Recommendation: use scheduled queries instead of extending memory store TTL
for long-range query needs.
```

## Scheduled queries

### Scheduled query lifecycle

```text
1. Create target table (must exist before scheduled query runs)
2. Create scheduled query with:
   ├── QueryString (SQL that materializes results)
   ├── ScheduleExpression (rate or cron)
   ├── NotificationConfiguration (SNS topic for errors)
   ├── TargetConfiguration (destination table + dimension mapping)
   ├── ScheduledQueryExecutionRoleArn (IAM role)
   └── ErrorReportConfiguration (S3 path for detailed errors, optional)
3. Scheduled query runs on schedule:
   ├── SUCCESS: results written to target table
   └── FAILURE: error notification sent to SNS, detailed report to S3
4. Query the materialized results from the target table
```

### Target table dimension mapping

The target table receives query results. Each column in the query
output must be mapped to a Timestream dimension or measure:

```bash
aws timestream-query create-scheduled-query \
  --name "DailyTemperatureAggregation" \
  --query-string \
    "SELECT region, device_id, BIN(time, 1d) as day, \
     AVG(measure_value::double) as avg_temp \
     FROM \"IoTSensorData\".\"TemperatureReadings\" \
     WHERE measure_name = 'temperature' \
     GROUP BY region, device_id, BIN(time, 1d)" \
  --schedule-configuration "ScheduleExpression='rate(1 day)'" \
  --notification-configuration "SnsConfiguration={TopicArn='$SNS_ARN'}" \
  --target-configuration \
    "TimestreamConfiguration={\
      DatabaseName='IoTSensorData',\
      TableName='DailyTempAggregates',\
      TimeColumn='day',\
      DimensionMappings=[\
        {Name='region',DimensionValueType='VARCHAR'},\
        {Name='device_id',DimensionValueType='VARCHAR'}\
      ],\
      MeasureNameColumn='avg_temp_measure',\
      MeasureValueType='DOUBLE'}" \
  --scheduled-query-execution-role-arn "$ROLE_ARN"
```

### Schedule expression formats

| Format | Meaning |
|---|---|
| `rate(1 minute)` | Every minute |
| `rate(1 hour)` | Every hour |
| `rate(1 day)` | Every day |
| `cron(0 */6 * * ? *)` | Every 6 hours via cron |

### Verifying scheduled query execution

```bash
# Describe the scheduled query
aws timestream-query describe-scheduled-query \
  --scheduled-query-arn arn:aws:timestream:us-east-1:123456789012:scheduled-query/DailyTemperatureAggregation

# Query CloudWatch for execution history
aws cloudwatch get-metric-statistics \
  --namespace AWS/Timestream \
  --metric-name ScheduledQueryExecutions \
  --start-time 2026-08-10T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Terraform examples

```hcl
# Database
resource "aws_timestreamwrite_database" "iot" {
  database_name = "IoTSensorData"
}

# Table with retention properties and magnetic store writes
resource "aws_timestreamwrite_table" "temperature" {
  database_name = aws_timestreamwrite_database.iot.database_name
  table_name    = "TemperatureReadings"

  retention_properties {
    magnetic_store_retention_period_in_days = 365
    memory_store_retention_period_in_hours  = 12
  }

  magnetic_store_write_properties {
    enable_magnetic_store_writes = true

    magnetic_store_rejected_data_location {
      s3_configuration {
        bucket_name = "timestream-magnetic-late-arrival-us-east-1"
        encryption_option = "SSE_S3"
      }
    }
  }
}

# Scheduled query
resource "aws_timestreamquery_scheduled_query" "hourly_agg" {
  name = "HourlyTemperatureAggregation"

  query_string = "SELECT region, device_id, BIN(time, 1h) as hour, AVG(measure_value::double) as avg_temp FROM \"IoTSensorData\".\"TemperatureReadings\" WHERE measure_name = 'temperature' GROUP BY region, device_id, BIN(time, 1h)"

  schedule_configuration {
    schedule_expression = "rate(1 hour)"
  }

  notification_configuration {
    sns_configuration {
      topic_arn = aws_sns_topic.timestream_errors.arn
    }
  }

  target_configuration {
    timestream_configuration {
      database_name = aws_timestreamwrite_database.iot.database_name
      table_name    = "HourlyTempAggregates"
      time_column   = "hour"

      dimension_mapping {
        name                 = "region"
        dimension_value_type = "VARCHAR"
      }

      dimension_mapping {
        name                 = "device_id"
        dimension_value_type = "VARCHAR"
      }

      measure_name_column = "avg_temp_measure"
      measure_value_type  = "DOUBLE"
    }
  }

  scheduled_query_execution_role_arn = aws_iam_role.timestream_sq.arn
}
```

## Extended from SKILL.md

## Expert heuristic: scheduled query materialized view freshness

## Expert heuristic: scheduled query materialized view freshness

Scheduled queries continuously materialize results into a target
table. The freshness of the materialized view depends on the query
schedule and the target table's own retention properties.

```text
Scheduled query materialization:
  Source table (raw events)
    → Scheduled query runs every 1 hour (schedule expression)
    → Query: SELECT region, measure_name, AVG(measure_value) ...
             GROUP BY region, measure_name, bin(time, 1h)
    → Results written to target table (pre-computed aggregates)

  Target table considerations:
    ├── Memory store TTL on target: controls how fresh aggregates are queryable fast
    │     e.g., 30 days of aggregates in memory store → fast recent aggregates
    ├── Magnetic store TTL on target: controls long-term aggregate retention
    │     e.g., 5 years → historical aggregate analysis
    └── Schedule frequency vs data freshness:
          schedule = 1 min → aggregates are at most 1 min stale
          schedule = 1 hour → aggregates are at most 1 hour stale
          schedule = 1 day → aggregates are at most 1 day stale

Notification configuration:
  ├── SNS topic → alerts on scheduled query errors (DDL errors, permission issues)
  └── SQS queue → programmatic error handling for retry pipelines
```

**Key implication:** scheduled queries are the primary tool for
balancing query freshness, latency, and cost. Choose the schedule
frequency to match the acceptable staleness of the materialized view.
Configure error notifications via SNS/SQS to catch failures early.

## Step 2 — Table creation and retention update CLI

```bash
# Create a table with retention properties
aws timestream-write create-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=12,MagneticStoreRetentionPeriodInDays=365" \
  --region us-east-1

# Verify
aws timestream-write describe-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --region us-east-1
```

**Retention property rules:**

| Property | Minimum | Maximum | Effect |
|---|---|---|---|
| MemoryStoreRetentionPeriodInHours | 1 hour | practically unlimited (but costly) | Data queryable from fast in-memory storage |
| MagneticStoreRetentionPeriodInDays | 1 day | 73000 days (~200 years) | Data retained in cost-effective magnetic storage |

**Updating retention properties:**

```bash
aws timestream-write update-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=24,MagneticStoreRetentionPeriodInDays=730" \
  --region us-east-1
```

## Step 5 — Scheduled query creation CLI

```bash
# Create the target table for materialized results
aws timestream-write create-table \
  --database-name "IoTSensorData" \
  --table-name "HourlyTempAggregates" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=720,MagneticStoreRetentionPeriodInDays=1825" \
  --region us-east-1

# Create an SNS topic for error notifications
SNS_ARN=$(aws sns create-topic \
  --name timestream-scheduled-query-errors \
  --region us-east-1 \
  --query 'TopicArn' --output text)

# Create the scheduled query
aws timestream-query create-scheduled-query \
  --name "HourlyTemperatureAggregation" \
  --query-string \
    "SELECT region, device_id, BIN(time, 1h) as hour, AVG(measure_value::double) as avg_temp \
     FROM \"IoTSensorData\".\"TemperatureReadings\" \
     WHERE measure_name = 'temperature' \
     GROUP BY region, device_id, BIN(time, 1h)" \
  --schedule-configuration "ScheduleExpression='rate(1 hour)'" \
  --notification-configuration "SnsConfiguration={TopicArn='${SNS_ARN}'}" \
  --target-configuration \
    "TimestreamConfiguration={DatabaseName='IoTSensorData',TableName='HourlyTempAggregates',TimeColumn='hour',DimensionMappings=[{Name='region',DimensionValueType='VARCHAR'},{Name='device_id',DimensionValueType='VARCHAR'}],MeasureNameColumn='avg_temp_measure',MeasureValueType='DOUBLE'}" \
  --scheduled-query-execution-role-arn arn:aws:iam::123456789012:role/TimestreamScheduledQueryRole \
  --region us-east-1
```

**Scheduled query components:**

| Component | Purpose | Required |
|---|---|---|
| QueryString | The SQL query to materialize | Yes |
| ScheduleExpression | How often to run (rate or cron) | Yes |
| NotificationConfiguration | SNS topic for error reporting | Yes |
| TargetConfiguration | Destination table for results | Yes |
| ScheduledQueryExecutionRoleArn | IAM role for query execution | Yes |
| ErrorReportConfiguration | S3 path for detailed error reports | No (recommended) |

**Common mistake:** forgetting to create the target table before
creating the scheduled query. The scheduled query fails at execution
time if the target table does not exist.
