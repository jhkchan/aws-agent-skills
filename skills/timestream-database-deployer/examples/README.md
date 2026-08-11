# End-to-End Example: Timestream Database Deployment

A walkthrough showing how to use the `timestream-database-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Timestream database for IoT sensor data with
a table configured for optimal query performance, magnetic store
writes for late-arrival data, and a scheduled query for hourly
aggregations. The deployment needs:

- Database: IoTSensorData
- Table: TemperatureReadings (memory TTL 12h, magnetic TTL 365d)
- Magnetic store writes: enabled (S3: timestream-magnetic-late-arrival)
- Scheduled query: HourlyTemperatureAggregation
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-timestream-database
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Timestream database IoTSensorData with table
      TemperatureReadings. Memory store TTL 12 hours, magnetic
      store TTL 365 days. Enable magnetic store writes with S3
      bucket timestream-magnetic-late-arrival. Create a scheduled
      query for hourly temperature aggregation."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a timestream database"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
TIMESTREAM: IoTSensorData / TemperatureReadings
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Database: IoTSensorData (region us-east-1)
  [✓] Table: TemperatureReadings
  [✓] Memory store TTL: 12h
  [✓] Magnetic store TTL: 365d
  [✓] Magnetic store writes: Enabled (S3: timestream-magnetic-late-arrival)
  [✓] Partition key enforcement: None
  [✓] Scheduled query: HourlyTemperatureAggregation (rate(1 hour), target: HourlyTempAggregates)
  [✓] Scheduled query notification: SNS arn:aws:sns:us-east-1:123456789012:timestream-errors
  [✓] Tags: Environment=production, Team=iot
VERIFICATION_COMMANDS:
  aws timestream-write describe-database --database-name IoTSensorData --region us-east-1
  aws timestream-write describe-table --database-name IoTSensorData --table-name TemperatureReadings --region us-east-1
  aws timestream-query describe-scheduled-query --scheduled-query-arn arn:aws:timestream:us-east-1:123456789012:scheduled-query/HourlyTemperatureAggregation --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the database
aws timestream-write create-database \
  --database-name "IoTSensorData" \
  --tags Key=Environment,Value=production Key=Team,Value=iot \
  --region us-east-1

# Step 2: Create the table with retention properties
aws timestream-write create-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=12,MagneticStoreRetentionPeriodInDays=365" \
  --region us-east-1

# Step 3: Enable magnetic store writes (requires S3 bucket policy)
aws timestream-write update-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --magnetic-store-write-properties \
    "EnableMagneticStoreWrites=true,MagneticStoreRejectedDataLocation=s3://timestream-magnetic-late-arrival/" \
  --region us-east-1

# Step 4: Create the target table for scheduled query results
aws timestream-write create-table \
  --database-name "IoTSensorData" \
  --table-name "HourlyTempAggregates" \
  --retention-properties \
    "MemoryStoreRetentionPeriodInHours=720,MagneticStoreRetentionPeriodInDays=1825" \
  --region us-east-1

# Step 5: Create the scheduled query
aws timestream-query create-scheduled-query \
  --name "HourlyTemperatureAggregation" \
  --query-string "SELECT region, device_id, BIN(time, 1h) as hour, AVG(measure_value::double) as avg_temp FROM \"IoTSensorData\".\"TemperatureReadings\" WHERE measure_name = 'temperature' GROUP BY region, device_id, BIN(time, 1h)" \
  --schedule-configuration "ScheduleExpression='rate(1 hour)'" \
  --notification-configuration "SnsConfiguration={TopicArn='arn:aws:sns:us-east-1:123456789012:timestream-errors'}" \
  --target-configuration "TimestreamConfiguration={DatabaseName='IoTSensorData',TableName='HourlyTempAggregates',TimeColumn='hour',DimensionMappings=[{Name='region',DimensionValueType='VARCHAR'},{Name='device_id',DimensionValueType='VARCHAR'}],MeasureNameColumn='avg_temp_measure',MeasureValueType='DOUBLE'}" \
  --scheduled-query-execution-role-arn arn:aws:iam::123456789012:role/TimestreamSQRole \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Database status
aws timestream-write describe-database \
  --database-name IoTSensorData --region us-east-1

# Table status and retention properties
aws timestream-write describe-table \
  --database-name IoTSensorData \
  --table-name TemperatureReadings --region us-east-1

# Verify magnetic store write properties
aws timestream-write describe-table \
  --database-name IoTSensorData \
  --table-name TemperatureReadings \
  --query 'Table.MagneticStoreWriteProperties' --region us-east-1

# Scheduled query status
aws timestream-query describe-scheduled-query \
  --scheduled-query-arn arn:aws:timestream:us-east-1:123456789012:scheduled-query/HourlyTemperatureAggregation \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Magnetic store writes | Not configured | Enabled with S3 bucket + bucket policy | Late-arrival data is silently rejected without this |
| Scheduled query target table | Target table not created | Target table created before scheduled query | Scheduled query fails if target table is missing |
| Memory store TTL | Set to default or too high | Tuned to workload hot-data window | High TTL inflates memory store cost dramatically |
| S3 bucket policy | Not configured | Bucket policy granting Timestream s3:PutObject | Without bucket policy, magnetic store writes silently fail |
| Execution role permissions | Only query permission | Query + write + SNS publish | Missing any permission causes silent scheduled query failures |
| CUMULATIVE vs interval metrics | Confused | Distinguished for cost monitoring | CUMULATIVE metrics need delta calculation for per-period cost |

---

## Related artifacts

- **Skill definition:** `skills/timestream-database-deployer/SKILL.md`
- **Retention and scheduled queries guide:** `skills/timestream-database-deployer/references/retention-and-scheduled-queries.md`
- **IAM and magnetic store guide:** `skills/timestream-database-deployer/references/iam-and-magnetic-store.md`
- **Slash command:** `commands/aws/deploy-timestream-database.md`
- **Eval suite:** `skills/timestream-database-deployer/evals/evals.json`
- **Legacy test cases:** `skills/timestream-database-deployer/eval/test-cases.yaml`
