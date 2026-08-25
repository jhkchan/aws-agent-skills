# Worked Examples — Timestream Database Deployer

Step-by-step CLI walkthroughs moved verbatim from SKILL.md. Loaded on demand.

## Step 1 — Database creation CLI

```bash
# Create a Timestream database
aws timestream-write create-database \
  --database-name "IoTSensorData" \
  --region us-east-1

# With KMS encryption (customer-managed key)
aws timestream-write create-database \
  --database-name "IoTSensorData" \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --region us-east-1

# With tags
aws timestream-write create-database \
  --database-name "IoTSensorData" \
  --tags Key=Environment,Value=production Key=Team,Value=iot \
  --region us-east-1
```

**Verify the database:**

```bash
aws timestream-write describe-database \
  --database-name "IoTSensorData" \
  --region us-east-1
```

**Database naming rules:** 3-256 characters, alphanumeric characters
and underscores. Must be unique within the account and region.

**Database ARN pattern:**
`arn:aws:timestream:<region>:<account>:database/<database-name>`

## Step 4 — Partition key enforcement CLI

```bash
# Create a table with partition key enforcement
aws timestream-write create-table \
  --database-name "IoTSensorData" \
  --table-name "PartitionedReadings" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=12,MagneticStoreRetentionPeriodInDays=365" \
  --schema \
    "CompositePartitionKey={EnforcementInRecord=REQUIRED,DimInsightsOptimization=DISABLED}" \
  --region us-east-1
```

## Step 4 — Verify partition key configuration

**Verify partition key configuration:**

```bash
aws timestream-write describe-table \
  --database-name "IoTSensorData" \
  --table-name "PartitionedReadings" \
  --query 'Table.Schema' --region us-east-1
```

## Step 6 — Raw vs scheduled query CLI

**Raw query (direct SQL):**

```bash
aws timestream-query query \
  --query-string \
    "SELECT region, AVG(measure_value::double) as avg_temp \
     FROM \"IoTSensorData\".\"TemperatureReadings\" \
     WHERE time > ago(1h) AND measure_name = 'temperature' \
     GROUP BY region" \
  --region us-east-1
```

**Scheduled query result (materialized view):**

```bash
aws timestream-query query \
  --query-string \
    "SELECT region, hour, avg_temp \
     FROM \"IoTSensorData\".\"HourlyTempAggregates\" \
     WHERE hour > ago(24h)" \
  --region us-east-1
```

## Step 11 — Tagging CLI

```bash
# Tag a database
aws timestream-write tag-resource \
  --resource-arn arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData \
  --tags Key=Environment,Value=production Key=Team,Value=iot \
  --region us-east-1

# Tag a table
aws timestream-write tag-resource \
  --resource-arn arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData/table/TemperatureReadings \
  --tags Key=Environment,Value=production Key=CostCenter,Value=CC-1001 \
  --region us-east-1

# List tags
aws timestream-write list-tags-for-resource \
  --resource-arn arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData \
  --region us-east-1
```
