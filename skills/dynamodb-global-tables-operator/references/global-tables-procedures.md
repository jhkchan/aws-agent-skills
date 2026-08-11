# Global Tables Procedures Reference

Supplementary reference for the DynamoDB Global Tables Operator skill.
Documents the canonical operation procedures for each global table
lifecycle operation, with pre-checks, command sequences, post-
verification, and rollback notes.

## Decision tree — which operation

| Scenario | Use | Why |
|---|---|---|
| New multi-region table | **create-global-table** | Create empty tables in each region, then link |
| Expand to a new region | **add-replica** | `update-global-table` with Create |
| Decommission a region | **remove-replica** | `update-global-table` with Delete |
| Regional outage | **failover (application-level)** | SDK/DNS switch; DynamoDB does not failover |
| Enable continuous backups | **enable-pitr (per region)** | Independent per replica region |
| Monitor replication health | **verify-replication** | Check ReplicationLatency, ReplicaStatus |

## Pre-checks (run before any operation)

**ALL operations:**
1. All existing replicas are `ACTIVE` (no `CREATING` or `DELETING`).
2. `describe-global-table` returns valid replication group.
3. IAM caller has `dynamodb:DescribeGlobalTable`, plus the operation-
   specific permissions.

**For create-global-table:** identical empty tables exist in all target
regions with the same key schema and billing mode.

**For add-replica:** target region does NOT already have a replica.

**For remove-replica:** target region has near-zero traffic
(CloudWatch ConsumedReadCapacityUnits / ConsumedWriteCapacityUnits).

## Create global table procedure

**When to use:** new multi-region table from scratch.

```bash
# 1. Create identical empty tables in each target region.
aws dynamodb create-table \
  --table-name orders-prod \
  --attribute-definitions AttributeName=orderId,AttributeType=S \
  --key-schema AttributeName=orderId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

aws dynamodb create-table \
  --table-name orders-prod \
  --attribute-definitions AttributeName=orderId,AttributeType=S \
  --key-schema AttributeName=orderId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1

# 2. Wait for both tables to become ACTIVE.
aws dynamodb wait table-exists --table-name orders-prod --region us-east-1
aws dynamodb wait table-exists --table-name orders-prod --region eu-west-1

# 3. Create the global table linking them.
aws dynamodb create-global-table \
  --global-table-name orders-prod \
  --replication-group '[{"RegionName":"us-east-1"},{"RegionName":"eu-west-1"}]'

# 4. Verify replication group.
aws dynamodb describe-global-table --global-table-name orders-prod \
  --query 'GlobalTableDescription.ReplicationGroup[*].{region:RegionName,status:ReplicaStatus}'
```

**Post-verification:**
- All replicas show `ReplicaStatus: ACTIVE`.
- Write a test item in us-east-1, read it in eu-west-1 (within 1 second).
- Enable PITR in each region independently.

## Add replica procedure

**When to use:** expand an existing global table to a new region.

```bash
# 1. Add the new replica (DynamoDB creates the table automatically).
aws dynamodb update-global-table \
  --global-table-name orders-prod \
  --replica-updates '[{"Create":{"RegionName":"ap-southeast-1"}}]'

# 2. Poll for ACTIVE status (minutes to hours depending on table size).
aws dynamodb describe-global-table --global-table-name orders-prod \
  --query 'GlobalTableDescription.ReplicationGroup[?RegionName==`ap-southeast-1`].ReplicaStatus'

# 3. Enable PITR in the new region.
aws dynamodb update-continuous-backups \
  --table-name orders-prod --region ap-southeast-1 \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# 4. Register autoscaling (if PROVISIONED mode).
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/orders-prod \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 --max-capacity 1000 --region ap-southeast-1
```

**Common failure modes:**
- `ReplicaAlreadyExistsException` — the region already has a replica.
- `ResourceInUseException` — a table with the same name already exists
  in the target region (and is not empty). Delete it first.
- Timeout — large tables take hours. Poll, do not re-trigger.

## Remove replica procedure

**When to use:** decommission a region from the global table.

**WARNING:** This deletes the table and ALL data in the removed region.

```bash
# 1. PRE-CHECK: Verify no active traffic.
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=orders-prod \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum --region us-west-2 --output json

# 2. Remove the replica.
aws dynamodb update-global-table \
  --global-table-name orders-prod \
  --replica-updates '[{"Delete":{"RegionName":"us-west-2"}}]'

# 3. Poll for deletion to complete.
aws dynamodb describe-global-table --global-table-name orders-prod \
  --query 'GlobalTableDescription.ReplicationGroup[?RegionName==`us-west-2`]'

# 4. Verify table is deleted in the removed region.
aws dynamodb describe-table --table-name orders-prod --region us-west-2
# Should return ResourceNotFoundException
```

## Failover procedure (application-level)

**When to use:** regional outage or planned DR drill.

DynamoDB does NOT automatically failover. The application must switch:

1. **SDK-level failover (recommended):** configure the DynamoDB client
   with multiple regions and a retry policy that detects regional
   failures and retries in the next region.
2. **Route 53 health check:** health-check the DynamoDB regional
   endpoint; Route 53 fails over the DNS record.
3. **Manual switch:** update the application config to point to the
   new region's DynamoDB endpoint.

```bash
# Verify the target region is ready.
aws dynamodb describe-global-table --global-table-name orders-prod \
  --query 'GlobalTableDescription.ReplicationGroup[?RegionName==`us-west-2`].ReplicaStatus'

aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ReplicationLatency \
  --dimensions Name=TableName,Value=orders-prod Name=ReceivingRegion,Value=us-west-2 \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --output json

# Application SDK switches to us-west-2 endpoint:
# Endpoint: https://dynamodb.us-west-2.amazonaws.com
# Table ARN: arn:aws:dynamodb:us-west-2:<account>:table/orders-prod
```

**Post-failover notes:**
- When the degraded region recovers, replication resumes automatically.
- LWW conflicts: writes during the outage in the new primary win over
  stale writes in the recovered region (later timestamp).
- Do NOT remove the degraded region's replica.
