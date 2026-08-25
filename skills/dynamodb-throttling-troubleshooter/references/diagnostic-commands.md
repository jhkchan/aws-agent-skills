# Diagnostic Commands (load on demand) — DynamoDB Throttling Troubleshooter

Pre-flight and diagnostic command listings, moved verbatim from SKILL.md.


---

## Step 0: Find recent throttle events across all tables (moved from SKILL.md)

```bash
# Find recent throttle events across all tables in the account/region.
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

# Or scan all tables (requires a script):
for t in $(aws dynamodb list-tables --query 'TableNames[]' --output text); do
  echo "== $t =="
  aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
    --metric-name ThrottledRequests \
    --dimensions Name=TableName,Value=$t \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 --statistics Sum --query 'Datapoints[*].Sum' --output text
done
```

---

## Step 2: READ_CAPACITY_LOW diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
aws dynamodb describe-table --table-name <table> \
  --query 'Table.{provisioned:ProvisionedThroughput.{read:ReadCapacityUnits,write:WriteCapacityUnits},gsis:GlobalSecondaryIndexes[*].{name:IndexName,provisioned:ProvisionedThroughput}}'

aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ProvisionedReadCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average --output json
```

---

## Step 3: WRITE_CAPACITY_LOW diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> Name=Operation,Value=PutItem \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json
```

---

## Step 4: GSI_HOT_KEY diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
# Per-GSI throttle metrics (the key signal).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

# Per-GSI consumed capacity.
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=<table> Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average --output json

# Inspect the GSI key schema and cardinality.
aws dynamodb describe-table --table-name <table> \
  --query 'Table.GlobalSecondaryIndexes[?IndexName==`<gsi>`].{key:KeySchema,projection:Projection,provisioned:ProvisionedThroughput}'
```

---

## Step 5: BURST_EXHAUSTED diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
# 1-minute period reveals the spiky pattern that 5-min period hides.
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average Maximum --output json

# Throttle timing relative to the spike.
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json
```

---

## Step 6: ADAPTIVE_LAG / HOT_PARTITION diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
# Enable contributor insights if not already enabled.
aws dynamodb update-contributor-insights --table-name <table> \
  --contributor-insights-action ENABLE

# Read contributor insights for the top partition keys.
aws dynamodb describe-contributor-insights --table-name <table> \
  --index-name <gsi-or-blank-for-base-table>

# Sample the partition key distribution (for low-cardinality keys).
aws dynamodb scan --table-name <table> \
  --select SPECIFIC_ATTRIBUTES --attributes-to-get <partition-key-attr> \
  --limit 1000 --return-consumed-capacity TOTAL \
  --query 'Items[*].<partition-key-attr>.S' --output text | \
  sort | uniq -c | sort -rn | head -20
```

---

## Step 7: SCAN_MISUSE / BATCH_LIMIT diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
# Find recent Scan calls (CloudTrail).
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Scan \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Events[*].{time:EventTime,user:Username,resource:CloudTrailEvent' --output json

# Find BatchGetItem / BatchWriteItem calls.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=BatchGetItem \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --output json

# ReturnConsumedCapacity on a Scan reveals the cost.
aws dynamodb scan --table-name <table> \
  --limit 100 --return-consumed-capacity TOTAL \
  --query 'ConsumedCapacity'
```

---

## Diagnostic command reference (moved from SKILL.md)

```bash
# 1. Table capacity mode and per-GSI capacity.
aws dynamodb describe-table --table-name <table> \
  --query 'Table.{billing:BillingModeSummary.BillingMode,provisioned:ProvisionedThroughput,gsis:GlobalSecondaryIndexes[*].{name:IndexName,key:KeySchema,provisioned:ProvisionedThroughput,projection:Projection.ProjectionType}}'

# 2. Consumed vs provisioned (reads, 1-min period for burst detection).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ProvisionedReadCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average --output json

# 3. Consumed vs provisioned (writes, 1-min period).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum Average Maximum --output json

# 4. Throttled requests (all operations).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

# 5. Per-GSI throttled requests (the key signal for GSI_HOT_KEY).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

# 6. System errors (distinguish throttling from engine errors).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name SystemErrors \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

# 7. Contributor insights (top partition keys by traffic).
aws dynamodb describe-contributor-insights --table-name <table>

# 8. CloudTrail for Scan / BatchGetItem / BatchWriteItem events.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Scan \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --output json
```
