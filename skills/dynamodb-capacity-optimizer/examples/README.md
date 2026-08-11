# Example usage: dynamodb-capacity-optimizer

A walkthrough showing the skill optimizing an over-provisioned DynamoDB
table with 2 ALL-projection GSIs, no TTL, and expensive Streams
consumers. Demonstrates the capacity-mode crossover math, GSI projection
optimization, TTL activation, and dollar savings estimate with staged
migration.

## Input (user prompt)

> Review this DynamoDB table before our Q3 FinOps review. It's our main
> user events table and the bill has been climbing. Help me optimise
> the capacity cost.

```text
TableName: user-events-prod
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 5000
  WriteCapacityUnits: 2000
AutoScaling:
  Read: target=70, min=1000, max=10000
  Write: target=70, min=500, max=5000
GSIs: 2 (total projected size: 120 GB, both ALL projection)
TTL: not enabled
Table Class: STANDARD
Streams: NEW_AND_OLD_IMAGES
Metrics (last 30 days):
  - ConsumedReadCapacityUnits: avg 850/s, max 1200/s
  - ConsumedWriteCapacityUnits: avg 400/s, max 600/s
  - ThrottledRequests: 12,000 (on Read)
  - SystemErrors: 0

Workload context: high-write user event tracking. 60% of data is
session events that expire after 30 days (no TTL configured). GSI
queries only need 3 attributes but both GSIs use ALL projection.
Streams feeds an audit Lambda that processes every write event.
```

## Skill output

```text
TARGET: user-events-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Provisioned table at 5000 RCU / 2000 WCU consumed at only 17%
  read and 20% write utilization. On-demand evaluated but write-heavy
  ratio makes on-demand 38% MORE expensive. Instead, reduce provisioned
  to 1200 RCU / 600 WCU with autoscaling. GSI with ALL projection
  (120 GB) → INCLUDE (30 GB) saves 75% GSI storage. TTL not enabled
  despite 60% churn; Streams Lambda consuming $238/month.
RECOMMENDATION:
  Current: PROVISIONED 5000 RCU / 2000 WCU, 2 GSIs (ALL, 120 GB), no TTL, Streams on
  Proposed: PROVISIONED 1200 RCU / 600 WCU (autoscaled), 2 GSIs (INCLUDE, 30 GB), TTL on, Streams off
  Dimensions changed: capacity-mode → rcu-wcu-sizing → gsi → ttl-streams
  Dimensions checked: capacity-mode ✓ (provisioned confirmed)  rcu-wcu-sizing → (reduce)
    autoscaling → (retune)  partition-key ✓ (no skew)  gsi → (reduce projection)
    table-class ✓ (Standard, high traffic)  ttl-streams → (enable TTL, disable Streams)
  Confidence: HIGH — 30-day CloudWatch confirms 17% utilization; on-demand
    crossover verified (writes 5x cost make provisioned optimal at this ratio).
ESTIMATED_SAVINGS:
  Current monthly: $2,137.80
    capacity: 5000 RCU × $0.0949 + 2000 WCU × $0.4745 = $1,423.50
    storage: 200 GB × $0.25 = $50.00
    GSI capacity+storage: $332.15 + $30.00 = $362.15
    PITR: 320 GB × $0.20 = $64.00; Streams Lambda: $238.15
  Projected monthly: $571.45
    capacity: 1200 RCU × $0.0949 + 600 WCU × $0.4745 = $398.58
    storage (TTL reduces 60%): 80 GB × $0.25 = $20.00
    GSI capacity+storage (INCLUDE): $123.37 + $7.50 = $130.87
    PITR: 110 GB × $0.20 = $22.00; Streams: $0
  Monthly saving: $1,566.35 ($2,137.80 − $571.45 ✓)
  Annual saving: $18,796.20
MIGRATION_STEPS:
  1. Reduce autoscaling min capacity:
     aws application-autoscaling register-scalable-target \
       --service-namespace dynamodb --resource-id table/user-events-prod \
       --scalable-dimension dynamodb:table:ReadCapacityUnits \
       --min-capacity 1200 --max-capacity 3000
  2. Recreate GSI with INCLUDE projection (swap: create new, verify, delete old):
     aws dynamodb update-table --table-name user-events-prod \
       --global-secondary-index-updates '[{"Create":{"IndexName":"by-type-v2",...}}]'
  3. Enable TTL: aws dynamodb update-time-to-live --table-name user-events-prod \
       --time-to-live-specification '{"Enabled":true,"AttributeName":"expires_at"}'
  4. Disable Streams after confirming no Lambda consumers depend on it.
  5. Monitor ThrottledRequests and ConsumedCapacity for 7 days.
CONFIRM: About to reduce capacity (5000→1200 RCU, 2000→600 WCU), swap GSI,
  enable TTL, disable Streams on user-events-prod. Saving $1,566.35/mo (73.3%).
  Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **On-demand crossover is computed, not assumed.** A generic assistant
   says "switch to on-demand" for a low-utilization table. The skill
   computes the actual crossover: write-heavy workloads (5x read cost)
   make provisioned cheaper even at 17% utilization. The recommendation
   is to right-size provisioned, not switch modes.

2. **GSI projection is quantified per-GB.** The skill identifies ALL
   projection on 120 GB and calculates the exact storage savings from
   switching to INCLUDE (30 GB, saving $22.50/month per GSI). A generic
   assistant says "consider using KEYS_ONLY" without computing the dollar
   impact.

3. **TTL eliminates storage growth.** The skill identifies 60% data churn
   and recommends TTL as a free mechanism to keep storage flat. Without
   TTL, storage grows linearly with writes. A generic assistant rarely
   surfaces TTL as a cost lever.

4. **Streams cost is surfaced.** The skill calculates the Lambda
   consumption from Streams-triggered invocations ($238/month) and
   surfaces it as a cost item. A generic assistant doesn't account for
   the downstream cost of DynamoDB Streams.

5. **GSI swap is staged for safety.** The skill recommends creating new
   GSIs first, verifying queries work, then deleting old GSIs — never
   modifying in place (GSIs can't be modified, only created or deleted).
   A generic assistant might suggest "change the projection" without
   knowing the operational constraint.

6. **Capacity arithmetic is shown explicitly.** The skill shows the
   crossover formula, the per-unit costs, and the total math so the
   operator can verify. A generic assistant says "this should save money"
   without showing the math.

## Slash-command invocation

```
/aws:optimize-dynamodb-capacity
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimise our DynamoDB tables for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: dynamodb-capacity-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new capacity configuration
aws dynamodb describe-table \
  --table-name user-events-prod \
  --profile default --output json | \
  jq '{BillingModeSummary: .BillingModeSummary, ProvisionedThroughput: .ProvisionedThroughput, GlobalSecondaryIndexes: [.GlobalSecondaryIndexes[] | {IndexName, Projection}]}'

# Monitor ThrottledRequests for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=user-events-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Sum --output json

# Verify TTL is deleting items
aws dynamodb describe-time-to-live \
  --table-name user-events-prod \
  --profile default
```

If ThrottledRequests spikes or errors increase, roll back by restoring
the original capacity settings:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/user-events-prod \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5000 --max-capacity 10000
```

## Fleet-wide extension

For a fleet of N DynamoDB tables, run the skill in batch mode:

1. List all tables with `aws dynamodb list-tables`.
2. Filter to tables with > $100/month spend (cost relevance).
3. Pull 14-30 day CloudWatch consumed-capacity for each.
4. Compute on-demand vs provisioned crossover for provisioned tables.
5. Sort by estimated monthly savings (largest first).
6. Slice into batches of 5 tables.
7. For each batch: emit per-table MIGRATION_STEPS, then a single CONFIRM.
8. Verify each batch before proceeding to the next.
9. After capacity tuning, evaluate GSI optimization for tables with
   multiple GSIs.
