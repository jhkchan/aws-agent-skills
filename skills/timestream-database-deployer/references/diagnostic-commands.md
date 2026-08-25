# Diagnostic Commands — Timestream Database Deployer

Verification and monitoring command listings moved verbatim from SKILL.md. Loaded on demand.

## Step 7 — CloudWatch metric queries

```bash
# Get cumulative memory store metered bytes (total cost driver)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Timestream \
  --metric-name MemoryStoreMeteredBytes \
  --dimensions Name=DatabaseName,Value=IoTSensorData Name=TableName,Value=TemperatureReadings \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --region us-east-1

# Get interval query bytes read (per-period scan volume)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Timestream \
  --metric-name QueryBytesRead \
  --dimensions Name=DatabaseName,Value=IoTSensorData Name=TableName,Value=TemperatureReadings \
  --start-time 2026-08-10T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

## Step 8 — Magnetic store S3 integration verification

```bash
# Verify the bucket policy grants Timestream access
aws s3api get-bucket-policy \
  --bucket timestream-magnetic-late-arrival-us-east-1 \
  --region us-east-1

# Verify the table's magnetic store write properties
aws timestream-write describe-table \
  --database-name "IoTSensorData" \
  --table-name "TemperatureReadings" \
  --query 'Table.MagneticStoreWriteProperties' \
  --region us-east-1
```

**S3 object lifecycle:** objects written by Timestream to the magnetic
store write bucket are managed by the service. Do NOT configure S3
lifecycle rules to delete them — Timestream manages the lifecycle
internally. The bucket is a staging area, not a permanent archive.
