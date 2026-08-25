# Diagnostic Commands (load on demand) — DynamoDB Throttling Optimizer

Pre-flight and diagnostic command listings, moved verbatim from SKILL.md.


---

## Pre-flight data gate — required data sources (moved from SKILL.md)

**Required data sources** (summarized):
1. Table config: `aws dynamodb describe-table`
2. ThrottledRequests (14-30 day window): `aws cloudwatch get-metric-statistics`
3. ConsumedWriteCapacityUnits, ConsumedReadCapacityUnits
4. GSI configuration: `aws dynamodb describe-table --query 'GlobalSecondaryIndexes'`
5. Scaling policies: `aws application-autoscaling describe-scaling-policies`
6. CloudTrail events for throttling: `aws cloudtrail lookup-events`
7. Account limits: `aws dynamodb describe-limits`

---

## Step 1: Hot partition detection commands (moved from SKILL.md)

**Hot partition detection:**
```bash
# Check ThrottledRequests by table
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -d '-30 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json

# Check write distribution via CloudTrail (look for concentrated keys)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<table> \
  --start-time $(date -d '-1 day' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --max-results 50
```

---

## Step 4: GSI hot partition diagnosis commands (moved from SKILL.md)

**GSI hot partition diagnosis:**
```bash
# Check if throttling correlates with GSI writes
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table>,Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json
```
