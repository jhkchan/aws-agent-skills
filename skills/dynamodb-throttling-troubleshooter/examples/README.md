# End-to-end usage scenario: dynamodb-throttling-troubleshooter

A walkthrough showing the skill diagnosing a DynamoDB throttling incident
caused by a GSI hot key on a low-cardinality `status` field. This
exercises Step 1 (symptom identification), Step 3 (write throttling),
Step 4 (GSI hot key), the capacity-vs-GSI distinction, and the
remediation workflow.

## Input (user prompt)

> Our `orders-prod` table in `us-east-1` keeps throwing
> `ProvisionedThroughputExceededException` on PutItem. The table is
> provisioned at 10,000 WCU but `ConsumedWriteCapacityUnits` is only
> 8,000. We already raised it from 10k to 20k and it did not help.
> There's a GSI `status-index` on the `status` field. CloudWatch shows
> `ThrottledRequests` on the GSI too. Contributor Insights says
> `status=ACTIVE` is 60% of the GSI traffic.

## Skill output

```text
TABLE: orders-prod in us-east-1
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: GSI_HOT_KEY — the GSI "status-index" has partition key
  "status" with only 4 distinct values (PENDING, ACTIVE, SHIPPED,
  DELIVERED). 60% of writes have status=ACTIVE, concentrating on one
  GSI partition. The GSI throttles, which propagates to the base table
  write path in provisioned mode.
THROTTLE_TYPE: GSI_HOT_KEY
EVIDENCE:
  - CloudWatch ThrottledRequests (base table, PutItem): sustained > 0
    for 30 minutes
  - CloudWatch ThrottledRequests (GSI status-index): sustained > 0,
    correlated with base table throttles
  - CloudWatch ConsumedWriteCapacityUnits (base table): 8,000 WCU/min,
    below the 10,000 provisioned — base table capacity is ample
  - describe-table: GSI status-index KeySchema [{AttributeName: status,
    KeyType: HASH}]
  - Contributor Insights: top key "status=ACTIVE" = 60% of GSI traffic
  - Prior remediation: raising WriteCapacityUnits 10k → 20k did not
    resolve — confirms the cause is the GSI, not base table capacity
ROOT_CAUSE_CATALOG: #2 (GSI hot key)
REMEDIATION:
  1. Immediate: switch the table to on-demand to stop the throttling:
     aws dynamodb update-table --table-name orders-prod \
       --billing-mode PAY_PER_REQUEST
  2. Permanent: redesign the GSI partition key to a composite of
     status + orderId hash suffix:
     - Create a new GSI "status-shard-index" with partition key
       "statusShard" (= status + "#" + (orderId % 10))
     - Update the application to populate statusShard on writes
     - Query the new GSI with all 10 shards and merge (fan-out read)
     - Delete the old "status-index" GSI
  3. Monitor CloudWatch ThrottledRequests for 15 minutes after the
     on-demand switch; expect 0 throttles.
```

## What the skill caught that a generic assistant misses

1. **The GSI-vs-base-table distinction.** A generic assistant sees "write
   throttling" and recommends raising `WriteCapacityUnits`. The skill
   recognises that base-table consumed capacity (8,000) is below
   provisioned (10,000), so raising capacity cannot fix the throttle —
   the cause is elsewhere (the GSI).

2. **The propagation rule.** A generic assistant treats GSI throttling
   and base-table throttling as separate issues. The skill knows that in
   provisioned mode, a hot GSI propagates throttle to the base table
   write path, because DynamoDB updates the GSI atomically with the base
   item.

3. **The "raising capacity did not help" signal.** The operator already
   raised capacity 10k to 20k with no effect. A generic assistant would
   recommend raising further. The skill interprets this as confirmation
   that the cause is NOT aggregate capacity — it is the GSI key
   distribution.

4. **The composite-key fix.** A generic assistant recommends "fix the
   GSI" without specifics. The skill specifies the exact redesign:
   composite the `status` with an `orderId % 10` shard suffix, query all
   10 shards for reads, and delete the old GSI.

## Slash-command invocation

```
/aws:troubleshoot-dynamodb-throttling
```

Or via the orchestrator:

```
/aws:pipeline
You: "orders-prod is throttling on PutItem, ConsumedWriteCapacityUnits is below provisioned"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
dynamodb-throttling-troubleshooter]` and hands off to this skill for the
VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "DynamoDB throttling on PutItem, GSI hot key suspected"
# [Phase: Troubleshoot | Skills routed: dynamodb-throttling-troubleshooter]
```

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the failing account:

```bash
# Check base-table vs GSI throttle metrics.
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=orders-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=orders-prod Name=GlobalSecondaryIndexName,Value=status-index \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum --output json

# Check Contributor Insights for the GSI key distribution.
aws dynamodb describe-contributor-insights --table-name orders-prod \
  --index-name status-index
```

If the per-GSI `ThrottledRequests` is > 0 while base-table consumed
capacity is below provisioned, the diagnosis is confirmed as GSI_HOT_KEY
without needing further probes. The fix is to redesign the GSI key (or
switch to on-demand for immediate relief).
