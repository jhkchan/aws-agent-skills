# Worked Examples — DynamoDB Capacity Optimizer

Full worked examples covering capacity mode crossover, auto-scaling
tuning, GSI optimization, hot partition, already-optimal, NEED_MORE_INFO,
and end-to-end walkthrough. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — provisioned to on-demand crossover

```text
TARGET: batch-report-processor-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Provisioned table at 5000 RCU / 2000 WCU consumed at only 15%
  utilization (avg 750 RCU/s of 5000, 300 WCU/s of 2000). Traffic is
  sporadic (bursts every 4h). Computed crossover shows on-demand costs
  $1,971/mo vs provisioned $1,423.50/mo at current consumption — provisioned
  is still cheaper. Instead, reduce provisioned to 1200 RCU / 500 WCU with
  auto-scaling (max 3000 RCU / 1000 WCU) to handle bursts while cutting
  idle cost.
RECOMMENDATION:
  Current: PROVISIONED, 5000 RCU / 2000 WCU (static), 1 GSI (KEYS_ONLY)
  Proposed: PROVISIONED, 1200 RCU / 500 WCU with autoscaling (max 3000/1000)
  Dimensions changed: rcu-wcu-sizing (Step 2) + autoscaling (Step 3)
  Dimensions checked: capacity-mode ✓ (provisioned confirmed by crossover)
    rcu-wcu-sizing → (reduce)  autoscaling → (enable range)
    partition-key ✓ (no skew)  gsi ✓ (KEYS_ONLY)  table-class ✓  ttl-streams ✓
  Confidence: HIGH — 30-day CloudWatch consumed-capacity confirms 15%
    utilization; crossover math verified (provisioned wins at this ratio).
ESTIMATED_SAVINGS:
  Current monthly: $1,513.50
    capacity: (5000 × $0.0949) + (2000 × $0.4745) = $1,423.50
    storage: 150 GB × $0.25 = $37.50
    GSI storage: 20 GB × $0.25 = $5.00 (KEYS_ONLY, minimal)
    PITR: 170 GB × $0.20 = $34.00
    Streams: disabled → $0
  Projected monthly: $471.80
    capacity: (1200 × $0.0949) + (500 × $0.4745) = $113.88 + $237.25 = $351.13
    storage: $37.50 (unchanged)
    GSI: $5.00 (unchanged)
    PITR: $34.00 (unchanged)
    Auto-scaling overhead during bursts: ~$44.17 (estimated 10h/day at max)
  Monthly saving: $1,041.70 (68.8%)
  Annual saving: $12,500.40
MIGRATION_STEPS:
  1. Enable auto-scaling range:
     aws application-autoscaling register-scalable-target \
       --service-namespace dynamodb --resource-id table/batch-report-processor-prod \
       --scalable-dimension dynamodb:table:ReadCapacityUnits \
       --min-capacity 1200 --max-capacity 3000
  2. Repeat for WriteCapacityUnits (min 500, max 1000).
  3. Verify no throttling during next burst cycle (4 hours).
  4. Monitor for 7 days.
CONFIRM: About to reduce provisioned capacity (5000→1200 RCU, 2000→500 WCU)
  with auto-scaling on batch-report-processor-prod. Monthly saving $1,041.70
  (68.8%). Proceed? (yes/no)
```

**Key nuance:** The 30% rule initially suggests on-demand, but the write-
heavy ratio (1.25:0.25 = 5x) means on-demand is MORE expensive even at
15% utilization. The skill computes the actual crossover rather than
blindly applying the rule of thumb.

## Worked example — auto-scaling target tuning

```text
TARGET: mobile-api-backend-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Auto-scaling target at 90% is too aggressive for bursty traffic
  (CV=0.8). 145,000 throttled reads in 30 days. Lowering target to 60%
  and raising max capacity to 8000 gives more headroom for spikes while
  keeping average cost manageable.
RECOMMENDATION:
  Current: PROVISIONED, target=90%, max=5000 RCU, ThrottledRequests=145K
  Proposed: PROVISIONED, target=60%, max=8000 RCU
  Dimensions changed: autoscaling (Step 3)
  Dimensions checked: capacity-mode ✓  rcu-wcu-sizing ✓  autoscaling → (retune)
    partition-key ✓ (uniform)  gsi ✓  table-class ✓  ttl-streams ✓
  Confidence: HIGH — 30-day CloudWatch shows CV=0.8 and 145K throttles.
ESTIMATED_SAVINGS:
  Current monthly: $569.40
    capacity avg: ~3000 RCU × $0.0949 + ~1500 WCU × $0.4745 = $284.70 + $711.75
    But auto-scaling oscillates. Actual CE shows ~$569.40
  Projected monthly: $617.85
    Higher max means more spend during bursts, BUT eliminates throttling.
    Target=60% → capacity averages higher (~3600 RCU avg).
    Net cost INCREASE of $48.45/month is justified by eliminating $X in
    throttling-related business impact.
  Monthly saving: -$48.45 (cost increase for eliminating throttling)
  Annual delta: -$581.40
  Note: This is a cost-performance trade-off, not pure savings. Throttling
  was causing user-visible errors on the mobile API.
MIGRATION_STEPS:
  1. Update auto-scaling policy:
     aws application-autoscaling put-scaling-policy \
       --policy-name mobile-api-read-scaling \
       --service-namespace dynamodb --resource-id table/mobile-api-backend-prod \
       --scalable-dimension dynamodb:table:ReadCapacityUnits \
       --policy-type TargetTrackingScaling \
       --target-tracking-scaling-policy-configuration '{"TargetValue":60.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":120}'
  2. Raise max: register-scalable-target --max-capacity 8000
  3. Monitor ThrottledRequests for 7 days — target should reach 0.
CONFIRM: About to lower auto-scaling target (90%→60%) and raise max (5000→8000)
  on mobile-api-backend-prod. Cost increase $48.45/mo but eliminates 145K
  throttles/mo. Proceed? (yes/no)
```

## Worked example — GSI projection optimization

```text
TARGET: ecommerce-orders-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 3 GSIs all using ALL projection totaling 300 GB storage. Only
  gsi-by-status (5K queries/day) needs 5 attributes — INCLUDE is optimal.
  gsi-by-category (200/d) and gsi-by-date (50/d) need only keys →
  KEYS_ONLY. Total GSI storage drops from 300 GB to ~25 GB.
RECOMMENDATION:
  Current: 3 GSIs (ALL projection), 300 GB GSI storage
  Proposed: gsi-by-status → INCLUDE (5 attributes, ~20 GB);
    gsi-by-category → KEYS_ONLY (~3 GB); gsi-by-date → KEYS_ONLY (~2 GB)
  Dimensions changed: gsi (Step 5)
  Dimensions checked: capacity-mode ✓ (on-demand)  rcu-wcu-sizing ✓
    autoscaling ✓ (N/A, on-demand)  partition-key ✓  gsi → (reduce projection)
    table-class ✓  ttl-streams ✓
  Confidence: HIGH — GSI query patterns verified via CloudTrail.
ESTIMATED_SAVINGS:
  Current monthly: $325.00
    GSI storage: 300 GB × $0.25 = $75.00
    GSI on-demand writes: ~$155.00 (3 GSIs consume write capacity)
    PITR: (200+300) GB × $0.20 = $100.00
    Streams: $0 (NEW_IMAGES writes factored into on-demand)
  Projected monthly: $139.25
    GSI storage: 25 GB × $0.25 = $6.25
    GSI writes: ~$58.00 (smaller GSIs, less write amplification)
    PITR: (200+25) GB × $0.20 = $45.00
    Streams: ~$30.00
  Monthly saving: $185.75 (57.2%)
  Annual saving: $2,229.00
MIGRATION_STEPS:
  1. Create new GSIs with correct projections (GSI swap pattern):
     aws dynamodb update-table --table-name ecommerce-orders-prod \
       --global-secondary-index-updates '[{"Create":{"IndexName":"by-status-v2","Projection":{"ProjectionType":"INCLUDE","NonKeyAttributes":["total","customer_id","created_at","tracking_number"]}}}]'
  2. Wait for new GSIs to become ACTIVE (can take minutes to hours).
  3. Update application queries to use the new GSI names.
  4. Delete old ALL-projection GSIs:
     aws dynamodb update-table --table-name ecommerce-orders-prod \
       --global-secondary-index-updates '[{"Delete":{"IndexName":"by-status"}}]'
  5. Monitor query latency and cost for 7 days.
CONFIRM: About to recreate 3 GSIs with optimized projections on
  ecommerce-orders-prod (300 GB → 25 GB GSI storage). Monthly saving $185.75
  (57.2%). Proceed? (yes/no)
```

## Worked example — hot partition remediation

```text
TARGET: order-processing-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 890,000 throttled requests despite 36% consumed capacity.
  Partition key "status" creates extreme skew: 80% of traffic to the
  "active" partition. Fix: redesign partition key to distribute traffic
  evenly (order_id as partition key, status as GSI sort key for queries).
RECOMMENDATION:
  Current: PK=status (hot: "active" gets 80%), ThrottledRequests=890K
  Proposed: PK=order_id (uniform), GSI on status for status-based queries
  Dimensions changed: partition-key (Step 4) + gsi (Step 5, add status GSI)
  Dimensions checked: capacity-mode ✓  rcu-wcu-sizing ✓  autoscaling ✓ (disabled)
    partition-key → (redesign)  gsi → (add status GSI)  table-class ✓  ttl-streams ✓
  Confidence: HIGH — CloudWatch confirms throttling despite low utilization.
    Partition key distribution analysis confirms 80% skew.
ESTIMATED_SAVINGS:
  Current monthly: $1,183.60
    capacity: (5000 × $0.0949) + (3000 × $0.4745) = $474.50 + $1,423.50 = $1,898.00
    But wasted — throttling means the table can't use the capacity.
    Effective capacity wasted: ~$700/month in throttled-but-provisioned capacity.
    Storage: 120 GB × $0.25 = $30.00
  Projected monthly: $543.50
    After redesign: 2000 RCU / 1000 WCU (sufficient with even distribution)
    capacity: (2000 × $0.0949) + (1000 × $0.4745) = $189.80 + $474.50 = $664.30
    New GSI storage: ~10 GB × $0.25 = $2.50
    Storage: $30.00 (unchanged)
  Monthly saving: $640.10 (54.1%) — from reduced capacity + eliminated throttling
  Annual saving: $7,681.20
MIGRATION_STEPS:
  1. Create new table with order_id as partition key:
     aws dynamodb create-table --table-name order-processing-v2 ...
  2. Backfill data from old table (Data Pipeline or script).
  3. Create GSI on status for status-based queries.
  4. Cutover application to new table.
  5. Monitor for 7 days, then decommission old table.
CONFIRM: Partition key redesign requires full table migration (new table +
  backfill + cutover). This is NOT a one-CLI-command change. Monthly saving
  $640.10 (54.1%) + eliminates 890K throttles/mo. Proceed with planning?
  (yes/no)
```

## Worked example — already optimal

```text
TARGET: session-store-prod
VERDICT: ALREADY_OPTIMAL
REASON: On-demand table with unpredictable spikes (correct billing mode),
  GSI with INCLUDE projection (3 attributes, 8 GB), TTL enabled (30-day
  expiry keeps storage flat), uniform partition distribution, zero
  throttling. No dimension has positive savings.
RECOMMENDATION:
  Current: PAY_PER_REQUEST, 1 GSI (INCLUDE, 8 GB), TTL active, Standard class
  Dimensions checked: capacity-mode ✓ (on-demand confirmed)  rcu-wcu-sizing ✓
    autoscaling ✓ (N/A)  partition-key ✓ (uniform)  gsi ✓ (INCLUDE)
    table-class ✓ (Standard, high traffic)  ttl-streams ✓ (active)
  Confidence: HIGH — 30-day CloudWatch confirms no throttling and correct
    on-demand sizing. TTL eliminates 80% of items at 30-day boundary.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate quarterly or if access pattern changes.
```

## Worked example — NEED_MORE_INFO

```text
TARGET: legacy-data-table
VERDICT: NEED_MORE_INFO
REASON: ConsumedReadCapacityUnits and ConsumedWriteCapacityUnits metrics
  are absent for the requested 30-day window. The table may be dormant,
  or the IAM role may deny cloudwatch:GetMetricStatistics. Cannot make a
  capacity optimization recommendation without baseline metrics.
RECOMMENDATION:
  Current: PROVISIONED, 1000 RCU / 500 WCU — pending data
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the table is receiving traffic:
     aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
       --metric-name ConsumedReadCapacityUnits \
       --dimensions Name=TableName,Value=legacy-data-table \
       --start-time $(date -d '-30 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
       --period 3600 --statistics Sum --output json
  2. Verify IAM permissions for CloudWatch.
  3. Wait 14-30 days for representative data.
  4. Re-evaluate.
  Do NOT optimize based on assumed metrics.
```

## End-to-end optimisation walkthrough (over-provisioned provisioned table)

**Table profile:**
- Table: `user-events-prod`
- Billing mode: PROVISIONED (5000 RCU / 2000 WCU)
- Auto-scaling: disabled (static)
- GSI: 2 with ALL projection (120 GB)
- TTL: not enabled
- Streams: NEW_AND_OLD_IMAGES

**Step 1 — Compute utilization:**
```
Consumed: 850 RCU/s (17%), 400 WCU/s (20%) → well below 30% rule.
But write-heavy ratio means on-demand may not be cheaper.
Crossover: on-demand reads $558.50 + writes $1,313.75 = $1,872.25
Provisioned: $1,423.50
Provisioned wins. But right-size to 1200 RCU / 600 WCU.
```

**Step 2 — Evaluate GSI:** ALL projection on 120 GB → INCLUDE (30 GB).

**Step 3 — Evaluate TTL:** 60% data churn → enable TTL.

**Step 4 — Evaluate Streams:** Lambda consuming ~$238/month → evaluate necessity.

**Step 5 — Calculate savings:**
```
Current: $2,137.80/month
Projected: $571.45/month
Saving: $1,566.35/month (73.3%), $18,796.20/year
```

**Step 6 — Emit the output block** (see SKILL.md perfect example).
