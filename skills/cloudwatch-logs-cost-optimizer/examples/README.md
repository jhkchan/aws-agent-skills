# Example usage: cloudwatch-logs-cost-optimizer

A walkthrough showing the skill optimizing a Lambda log group with
Never-expire retention and frequent Logs Insights queries, demonstrating
the retention sweep, the query-to-metric-filter migration, the dollar
savings math, and the staged cutover with verification.

## Input (user prompt)

> We're doing a Q3 FinOps audit of our observability spend. This Lambda
> log group is costing us over $900/month and I'm not sure why. Help me
> optimize it.

```text
LogGroupName: /aws/lambda/order-processor-prod
RetentionInDays: 0 (Never expire)
Region: us-east-1
StoredBytes: 10,080 GB (12 months accumulated)

Metrics (last 30 days):
  - IncomingBytes avg: 28 GB/day (840 GB/month)
  - IncomingLogEvents avg: 12,000,000/day

Cost Explorer (last month, AmazonCloudWatch):
  - Logs ingestion: $420.00
  - Logs storage: $302.40
  - Logs Insights: $270.00
  - Total: $992.40/month

Logs Insights usage (CloudTrail StartQuery events):
  - Queries/month: 450
  - Average GB scanned per query: 120 GB
  - Query patterns:
    1. count ERROR messages per minute (200 queries/month)
    2. count TIMEOUT messages per 5 min (100 queries/month)
    3. count Exception by service (80 queries/month)
    4. avg response_time by endpoint (40 queries/month)
    5. count 5xx status codes (30 queries/month)

Workload context: Lambda application logs for an order processing
service. Operational debugging window is 7-14 days. No compliance
mandate requiring long retention. All 5 query patterns are simple
count/avg aggregations.
```

## Skill output

```text
TARGET: /aws/lambda/order-processor-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Lambda log group with Never-expire retention accumulating
  10,080 GB over 12 months. Storage is $302.40/month and growing.
  Combined with 450 Logs Insights queries/month scanning 120 GB each
  ($270/month that converts to free metric filters). Retention to 30
  days caps storage; query migration eliminates the scan charge.
RECOMMENDATION:
  Current: Never expire, 840 GB/month ingested, 10,080 GB stored, 450 Insights queries/month
  Proposed: 30 days, 840 GB/month ingested, 840 GB stored (steady), 0 Insights queries (5 metric filters)
  Dimensions changed: retention (Step 1) + queries (Step 2)
  Dimensions checked: retention → (Never to 30d)  queries → (Insights to filters)
    agent ✓ (Lambda, no agent)  cold-storage ✓ (30d under S3 crossover)
    subscription ✓ (none)  destination ✓ (Lambda logs)  data-protection ✓
  Confidence: HIGH — describe-log-groups confirms RetentionInDays absent;
    CloudTrail StartQuery events confirm 450 queries/month scanning 120 GB each.
ESTIMATED_SAVINGS:
  Current monthly: $992.40
    ingestion: 840 GB × $0.50 = $420.00
    storage: 10,080 GB × $0.03 = $302.40
    insights: 450 × 120 GB × $0.005 = $270.00
  Projected monthly: $445.20
    ingestion: 840 GB × $0.50 = $420.00 (unchanged)
    storage: 840 GB × $0.03 = $25.20 (steady-state at 30-day retention)
    insights: 5 metric filters × $0.00 = $0.00 (free)
  Monthly saving: $547.20 ($992.40 − $445.20)
  Annual saving: $6,566.40
MIGRATION_STEPS:
  1. Set retention to 30 days:
     aws logs put-retention-policy
       --log-group-name /aws/lambda/order-processor-prod
       --retention-in-days 30
  2. Create 5 metric filters for the frequent Insights query patterns:
     aws logs put-metric-filter
       --log-group-name /aws/lambda/order-processor-prod
       --filter-name ErrorCount --filter-pattern '"ERROR"'
       --metric-transformations
       metricName=ErrorCount,metricNamespace=AppMetrics,metricValue=1,defaultValue=0
  3. Verify retention applied and old logs being deleted within 24 hours.
  4. Verify metric filters emitting data via CloudWatch metrics console.
CONFIRM: About to put-retention-policy on /aws/lambda/order-processor-prod
  (Never → 30 days). This will delete logs older than 30 days within hours.
  Saving $547.20/month (55.1%). Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Retention change is retroactive for existing stored logs.** A
   generic assistant says "set retention to 30 days" without warning
   that this will delete 10,080 GB of existing logs within hours. The
   skill surfaces the data-loss implication in the CONFIRM gate.

2. **Storage cost grows linearly at Never-expire.** A generic assistant
   treats the $302.40/month storage as static. The skill identifies that
   storage grows by $25.20/month (28 GB/day × 30 days × $0.03/GB-month)
   and will reach $600+/month within a year if unchecked.

3. **Logs Insights charges by GB scanned, not by result.** A generic
   assistant may suggest "optimize your queries." The skill identifies
   that ALL 5 query patterns are metric-filter-compatible (count/avg
   aggregations), eliminating the entire $270/month scan charge.

4. **Metric filter syntax verification.** A generic assistant says "use
   metric filters" without checking whether the query patterns are
   expressible in the CWL metric filter pattern language. The skill
   verifies each of the 5 patterns before recommending conversion.

5. **Full seven-dimension coverage.** The skill checks retention,
   queries, agent, cold-storage, subscription, destination, and data
   protection — confirming each has no additional finding. A generic
   assistant focuses only on the obvious retention issue.

6. **Dollar arithmetic is shown explicitly.** The skill shows the
   formula for each cost component (`840 GB × $0.50 = $420.00`) so the
   operator can verify. A generic assistant says "this should save
   money" without showing the math.

## Slash-command invocation

```
/aws:optimize-cloudwatch-logs-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our CloudWatch Logs spend for the Q3 FinOps audit"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: cloudwatch-logs-cost-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new retention landed
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/order-processor-prod \
  --query 'logGroups[0].{LogGroupName: logGroupName, RetentionInDays: retentionInDays, StoredBytes: storedBytes}' \
  --output json

# Confirm metric filters are created
aws logs describe-metric-filters \
  --log-group-name /aws/lambda/order-processor-prod \
  --output table

# Monitor StoredBytes for 7 days post-change (should drop then stabilize)
aws cloudwatch get-metric-statistics --namespace AWS/Logs \
  --metric-name IncomingBytes \
  --dimensions Name=LogGroupName,Value=/aws/lambda/order-processor-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Verify Cost Explorer shows the reduction
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"Service","Values":["AmazonCloudWatch"]}}' \
  --group-by Type=DIMENSION,Key=UsageType
```

If StoredBytes does not drop within 24 hours of the retention change,
verify the retention policy was applied correctly and check for any
subscription filters that may be re-ingesting deleted logs.

## Account-wide retention sweep

For an account with many log groups, run the skill in sweep mode:

1. List all log groups with Never-expire retention:
   ```bash
   aws logs describe-log-groups --output json | \
     jq '.logGroups[] | select(.retentionInDays == null) |
         {logGroupName, storedBytes}' | \
     jq -s 'sort_by(.storedBytes) | reverse'
   ```
2. Sort by `storedBytes` (largest first) to prioritize by dollar impact.
3. For each group, verify no compliance mandate requires long retention.
4. Slice into batches of 10 log groups.
5. For each batch: emit per-group MIGRATION_STEPS, then a single CONFIRM
   for the batch.
6. Verify each batch before proceeding to the next.
7. After the retention sweep, evaluate Insights query patterns across
   all groups for metric-filter migration eligibility.
8. For groups with compliance-mandated long retention, evaluate the
   Firehose → S3 cold-storage migration (Step 4).
