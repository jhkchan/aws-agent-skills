# Worked Examples (load on demand) — DynamoDB Table Deployer

Secondary worked examples moved verbatim from SKILL.md; the primary session-store example remains inline in SKILL.md. Loaded on demand.

---

## Worked example — provisioned table with GSI + autoscaling (moved from SKILL.md)

A high-throughput events table with a GSI for lookup by userId, using
PROVISIONED capacity with autoscaling on BOTH the base table and the GSI.
This is the critical pattern the eval flagged — the earlier session-store
example used on-demand and skipped GSI autoscaling registration.

```bash
# 1. Create table with GSI in a single create-table call
aws dynamodb create-table \
  --table-name prod-events \
  --attribute-definitions \
    AttributeName=eventId,AttributeType=S \
    AttributeName=userId,AttributeType=S \
    AttributeName=createdAt,AttributeType=N \
  --key-schema \
    AttributeName=eventId,KeyType=HASH \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5000,WriteCapacityUnits=2000 \
  --global-secondary-indexes '[
    {
      "IndexName": "gsi_by_userId",
      "KeySchema": [
        {"AttributeName":"userId","KeyType":"HASH"},
        {"AttributeName":"createdAt","KeyType":"RANGE"}
      ],
      "Projection": {"ProjectionType":"KEYS_ONLY"},
      "ProvisionedThroughput": {"ReadCapacityUnits":2000,"WriteCapacityUnits":1000}
    }
  ]' \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/prod-dynamodb-key \
  --deletion-protection-enabled

# 2. Wait for table + GSI to reach ACTIVE
aws dynamodb wait table-exists --table-name prod-events
aws dynamodb describe-table --table-name prod-events \
  --query 'Table.GlobalSecondaryIndexes[0].[IndexName,IndexStatus]'

# 3. Register autoscaling on BASE TABLE (reads)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 1000 --max-capacity 20000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'

# 4. Register autoscaling on BASE TABLE (writes)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 500 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-write-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBWriteCapacityUtilization"}}'

# 5. Register autoscaling on GSI (reads) — THIS IS THE STEP MOST COMMONLY MISSED
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --min-capacity 500 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-gsi-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'

# 6. Register autoscaling on GSI (writes)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:WriteCapacityUnits \
  --min-capacity 200 --max-capacity 5000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-gsi-write-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBWriteCapacityUtilization"}}'

# 7. Enable PITR
aws dynamodb update-continuous-backups --table-name prod-events \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# 8. Enable TTL
aws dynamodb update-time-to-live --table-name prod-events \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt

# 9. Enable Streams for CDC (Aurora zero-ETL / OpenSearch sync)
aws dynamodb update-table --table-name prod-events \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# 10. Verify everything
aws dynamodb describe-table --table-name prod-events
aws dynamodb describe-continuous-backups --table-name prod-events
aws dynamodb describe-time-to-live --table-name prod-events
aws application-autoscaling describe-scaling-policies --service-namespace dynamodb \
  --query 'ScalingPolicies[?contains(ResourceId,`prod-events`)].[PolicyName,ResourceId,ScalableDimension]'
```

The checklist for this table:

```text
TABLE: prod-events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Partition key: eventId (String) — UUID v4, high-cardinality (> 10k distinct)
  [✓] Sort key: None (event-level lookup by partition key)
  [✓] LSIs: None (no range queries on alternate sort within same partition)
  [✓] GSIs: gsi_by_userId (userId→createdAt, KEYS_ONLY projection, sparse)
  [✓] Capacity mode: PROVISIONED (autoscaling: table ✓ read+write, gsi ✓ read+write)
  [✓] Encryption: SSE-KMS customer CMK (alias/prod-dynamodb-key)
  [✓] PITR: Enabled (35-day window)
  [✓] TTL: Enabled (attribute: expiresAt — 90-day retention, 48h lag acceptable)
  [✓] Streams: NEW_AND_OLD_IMAGES (Aurora zero-ETL consumer)
  [✓] Table class: STANDARD (actively queried)
  [✓] Deletion protection: Enabled
  [✓] Resource-based policy: None (single-account)
  [✓] Global Tables: Single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws dynamodb describe-table --table-name prod-events
  aws dynamodb describe-continuous-backups --table-name prod-events
  aws dynamodb describe-time-to-live --table-name prod-events
  aws application-autoscaling describe-scaling-policies --service-namespace dynamodb
  aws kms describe-key --key-id alias/prod-dynamodb-key
```
