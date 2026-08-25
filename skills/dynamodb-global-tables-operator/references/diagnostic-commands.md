# Diagnostic Commands (load on demand) — DynamoDB Global Tables Operator

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight: global table metadata gate — live-account CLI (moved from SKILL.md)

**Live-account pre-flight (skip if offline plan audit):**

```bash
# 1. Global table configuration (replication group members).
aws dynamodb describe-global-table --global-table-name <table> \
  --query 'GlobalTableDescription.{table:GlobalTableName,regions:ReplicationGroup[*].{region:RegionName,status:ReplicaStatus}}'

# 2. Regional table configuration (run in each replica region).
aws dynamodb describe-table --table-name <table> --region <region> \
  --query 'Table.{status:TableStatus,billing:BillingModeSummary.BillingMode,throughput:ProvisionedThroughput,gsis:GlobalSecondaryIndexes[*].IndexName,stream:StreamSpecification,pitr:SSEDescription}'

# 3. PITR status per region.
aws dynamodb describe-continuous-backups --table-name <table> --region <region> \
  --query 'ContinuousBackupsDescription.{continuous:ContinuousBackupsStatus,pitr:PointInTimeRecoveryDescription.PointInTimeRecoveryStatus}'

# 4. ReplicationLatency metric (per region pair).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ReplicationLatency \
  --dimensions Name=TableName,Value=<table> Name=ReceivingRegion,Value=<region> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Maximum --output json

# 5. Autoscaling policies per region.
aws application-autoscaling describe-scaling-policies \
  --service-namespace dynamodb --resource-ids table/<table> --region <region>

# 6. Check for in-progress updates.
aws dynamodb describe-table --table-name <table> --region <region> \
  --query 'Table.TableStatus'
```

---

## Diagnostic command reference (moved from SKILL.md)

```bash
# 1. Global table replication group status.
aws dynamodb describe-global-table --global-table-name <table> \
  --query 'GlobalTableDescription.{table:GlobalTableName,regions:ReplicationGroup[*].{region:RegionName,status:ReplicaStatus}}'

# 2. Global table settings (per-region autoscaling, replica config).
aws dynamodb describe-global-table-settings --global-table-name <table> \
  --query 'GlobalTableSettings.ReplicaGlobalSecondaryIndexSettingsUpdate'

# 3. Regional table status (run per region).
aws dynamodb describe-table --table-name <table> --region <region> \
  --query 'Table.{status:TableStatus,billing:BillingModeSummary.BillingMode,gsis:GlobalSecondaryIndexes[*].IndexName}'

# 4. PITR status per region.
aws dynamodb describe-continuous-backups --table-name <table> --region <region> \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus'

# 5. ReplicationLatency metric (per receiving region).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ReplicationLatency \
  --dimensions Name=TableName,Value=<table> Name=ReceivingRegion,Value=<region> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Maximum --output json

# 6. Consumed capacity per region (check active traffic before removal).
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum --region <region> --output json

# 7. List all global tables in the account.
aws dynamodb list-global-tables --output json

# 8. Autoscaling policies per region.
aws application-autoscaling describe-scaling-policies \
  --service-namespace dynamodb --resource-ids table/<table> --region <region>
```
