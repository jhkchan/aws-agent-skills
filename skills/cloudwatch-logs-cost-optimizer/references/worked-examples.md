# Worked Examples — CloudWatch Logs Cost Optimizer

Full worked examples covering retention sweeps, Insights-to-metric-filter
migration, Firehose cold-storage pipelines, agent buffer tuning,
already-optimized log groups, NEED_MORE_INFO, and an end-to-end
optimisation walkthrough. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — retention sweep (Never expire to 30 days)

```text
TARGET: /aws/lambda/order-processor-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Lambda log group with Never-expire retention has accumulated
  10,080 GB over 12 months. Storage cost is $302.40/month and growing
  by $25.20/month as new data arrives. No compliance mandate requires
  retention beyond 30 days (operational debugging only).
RECOMMENDATION:
  Current: Never expire, 840 GB/month ingested, 10,080 GB stored
  Proposed: 30 days, 840 GB/month ingested, 840 GB stored (steady-state)
  Dimensions changed: retention (Step 1)
  Dimensions checked: retention → (Never to 30d)  queries ✓ (ad-hoc only)
    agent ✓ (Lambda, no agent)  cold-storage ✓ (30d under S3 crossover)
    subscription ✓ (none)  destination ✓ (Lambda logs)  data-protection ✓
  Confidence: HIGH — describe-log-groups confirms RetentionInDays absent
    and storedBytes=10,080 GB; Cost Explorer confirms $302.40/month storage.
ESTIMATED_SAVINGS:
  Current monthly: $722.40
    ingestion: 840 GB × $0.50 = $420.00
    storage: 10,080 GB × $0.03 = $302.40
  Projected monthly: $445.20
    ingestion: 840 GB × $0.50 = $420.00 (unchanged)
    storage: 840 GB × $0.03 = $25.20 (steady-state at 30-day retention)
  Monthly saving: $277.20 ($722.40 − $445.20)
  Annual saving: $3,326.40
MIGRATION_STEPS:
  1. Set retention to 30 days:
     aws logs put-retention-policy
       --log-group-name /aws/lambda/order-processor-prod
       --retention-in-days 30
  2. Verify retention applied:
     aws logs describe-log-groups
       --log-group-name-prefix /aws/lambda/order-processor-prod
       --query 'logGroups[0].retentionInDays'
  3. Confirm old logs being deleted (StoredBytes should drop within 24h).
CONFIRM: About to put-retention-policy on /aws/lambda/order-processor-prod
  (Never → 30 days). This will delete logs older than 30 days within
  hours. Saving $277.20/month (38.4%). Proceed? (yes/no)
```

**Key nuance:** retention changes delete existing stored data beyond the
new retention window. The operator must confirm no investigation or
compliance need exists for older logs. This is irreversible.

## Worked example — Insights-to-metric-filter migration

```text
TARGET: /app/microservice-logs
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Application log group has 450 Logs Insights queries/month
  scanning 120 GB each ($270/month). All 5 query patterns are count/avg
  aggregations expressible as metric filters (free). Converting eliminates
  $270/month with zero functional loss.
RECOMMENDATION:
  Current: 14 days retention, 450 Insights queries/month scanning 120 GB each
  Proposed: 14 days retention, 0 Insights queries (5 metric filters)
  Dimensions changed: queries (Step 2)
  Dimensions checked: retention ✓ (14d is operational minimum)
    queries → (Insights to filters)  agent ✓ (N/A serverless)
    cold-storage ✓ (14d under S3 crossover)  subscription ✓ (none)
    destination ✓ (app logs)  data-protection ✓
  Confidence: HIGH — CloudTrail StartQuery events confirm 450 queries/mo;
    all 5 patterns verified as metric-filter-compatible (count + value
    extraction only).
ESTIMATED_SAVINGS:
  Current monthly: $701.76
    ingestion: 840 GB × $0.50 = $420.00
    storage: 392 GB × $0.03 = $11.76
    insights: 450 × 120 GB × $0.005 = $270.00
  Projected monthly: $431.76
    ingestion: $420.00 (unchanged)
    storage: $11.76 (unchanged)
    insights: 5 metric filters × $0.00 = $0.00
  Monthly saving: $270.00 ($701.76 − $431.76)
  Annual saving: $3,240.00
MIGRATION_STEPS:
  1. Create metric filters for each query pattern:
     aws logs put-metric-filter --log-group-name /app/microservice-logs
       --filter-name ErrorCount --filter-pattern '"ERROR"'
       --metric-transformations
       metricName=ErrorCount,metricNamespace=AppMetrics,metricValue=1,defaultValue=0
  2. Create dashboard panels on the new metrics to replace scheduled queries.
  3. Verify metric data appears in CloudWatch within 5 minutes of log arrival.
  4. Once dashboard is validated, remove any scheduled Insights query
     automation (CloudWatch Alarms, Lambda schedulers).
CONFIRM: About to create 5 metric filters on /app/microservice-logs
  and migrate dashboard panels from Insights to metric queries.
  Saving $270.00/month (38.5%). Proceed? (yes/no)
```

## Worked example — Firehose cold-storage migration

```text
TARGET: /audit/soc2-compliance-logs
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: SOC2 compliance log group with 2-year (730-day) retention in
  CloudWatch Logs. Storage at 12,000 GB costs $360/month and grows.
  Migrating to Firehose → S3 (Glacier lifecycle) reduces archive cost
  94% while meeting the same 2-year compliance requirement. CW Logs
  retention reduced to 30 days for operational queries; S3 for archive.
RECOMMENDATION:
  Current: 730 days retention, 500 GB/month ingested, 12,000 GB stored
  Proposed: 30 days CW Logs + Firehose → S3 (GIR 90d → Glacier Deep Archive 2yr)
  Dimensions changed: retention (Step 1) + cold-storage (Step 4)
  Dimensions checked: retention → (730d to 30d + S3)
    queries ✓ (ad-hoc via Athena)  agent ✓ (N/A)
    cold-storage → (CW Logs to S3)  subscription ✓ (none)
    destination ✓ (audit logs)  data-protection ✓
  Confidence: HIGH — Cost Explorer confirms $610/month current;
    Firehose pricing $0.029/GB + S3 GIR $0.012/GB-month verified;
    team confirmed Athena meets audit query needs.
ESTIMATED_SAVINGS:
  Current monthly: $610.00
    ingestion: 500 GB × $0.50 = $250.00
    storage: 12,000 GB × $0.03 = $360.00
  Projected monthly (steady-state, month 24+): $440.00
    ingestion (CW Logs): 500 GB × $0.50 = $250.00 (unchanged — still ingest to CW Logs for 30d queries)
    storage (CW Logs): 500 GB × $0.03 = $15.00 (30-day steady-state)
    firehose delivery: 500 GB × $0.029 = $14.50
    s3 standard (0-90d): 1,500 GB × $0.023 = $34.50 (steady-state at 500 GB/mo × 3mo)
    s3 GIR (90-730d): 10,500 GB × $0.012 = $126.00 (steady-state at 500 GB/mo × 21mo)
  Monthly saving: $170.00 ($610.00 − $440.00)
  Annual saving: $2,040.00
  Note: savings are smaller in months 1-12 (S3 storage hasn't accumulated
  to steady-state). Year 2+ reflects the full $170/month saving.
MIGRATION_STEPS:
  1. Create S3 bucket for compliance archive with lifecycle policy:
     aws s3api create-bucket --bucket soc2-log-archive-2026 --region us-east-1
     aws s3api put-bucket-lifecycle-configuration --bucket soc2-log-archive-2026
       --lifecycle-configuration file://lifecycle.json
  2. Create Firehose delivery stream to the S3 bucket:
     aws firehose create-delivery-stream --delivery-stream-name soc2-archive
       --s3-destination-configuration ...
  3. Create subscription filter from CW Logs to Firehose:
     aws logs put-subscription-filter --log-group-name /audit/soc2-compliance-logs
       --filter-name ArchiveToFirehose --filter-pattern ""
       --destination-arn <firehose-arn>
  4. Verify Firehose receiving data (check S3 for log objects within 5 min).
  5. After confirming S3 delivery, reduce CW Logs retention to 30 days.
  6. Run first Athena query to validate S3 logs are queryable.
CONFIRM: About to create Firehose stream + subscription filter + reduce
  CW Logs retention from 730 to 30 days on /audit/soc2-compliance-logs.
  Compliance archive retained in S3 for 2 years (lifecycle-managed).
  Saving $170.00/month at steady-state. Proceed? (yes/no)
```

**Key nuance:** the S3 storage cost builds over time. At month 1, only
500 GB is in S3; by month 24, the full 12,000 GB accumulates. The
steady-state saving reflects the long-term equilibrium. Always state
whether the projected cost is initial or steady-state.

## Worked example — agent buffer tuning

```text
TARGET: /ec2/fleet-app-logs (100-host fleet)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: EC2 fleet running CloudWatch agent with default batch_count=1000,
  generating 209M PutLogEvents requests/month ($83.40/month). Increasing
  batch_count to 10000 reduces request count 10x, saving $75.06/month
  fleet-wide. Data-loss tolerance confirmed acceptable.
RECOMMENDATION:
  Current: batch_count=1000, 209M PutLogEvents requests/month
  Proposed: batch_count=10000, ~20.9M PutLogEvents requests/month
  Dimensions changed: agent (Step 3)
  Dimensions checked: retention ✓ (14d)  queries ✓ (no Insights)
    agent → (batch_count tuning)  cold-storage ✓ (14d)
    subscription ✓ (none)  destination ✓ (EC2 app logs)  data-protection ✓
  Confidence: HIGH — Cost Explorer confirms $83.40/month PutLogEvents charges;
    60-second data-loss window acceptable (events also in downstream aggregator).
ESTIMATED_SAVINGS:
  Current monthly: $509.28
    ingestion: $420.00
    storage: $5.88
    PutLogEvents requests: 209M / 1M × $0.40 = $83.40
  Projected monthly: $434.22
    ingestion: $420.00 (unchanged)
    storage: $5.88 (unchanged)
    PutLogEvents requests: 20.9M / 1M × $0.40 = $8.36
  Monthly saving: $75.06 ($509.28 − $434.22)
  Annual saving: $900.72
MIGRATION_STEPS:
  1. Update CloudWatch agent config on all hosts (SSM or config management):
     Set batch_count: 10000, batch_wait_time: 30 in the logs section.
  2. Restart the agent fleet-wide:
     systemctl restart amazon-cloudwatch-agent (via SSM Run Command)
  3. Verify PutLogEvents request count drops within 1 hour via Cost Explorer
     or CloudTrail.
  4. Confirm no log delivery delays exceed acceptable threshold.
CONFIRM: About to update CloudWatch agent batch_count from 1000 to 10000
  across 100 EC2 hosts. Data-loss window increases to ~60 seconds on
  agent failure. Saving $75.06/month (14.7%). Proceed? (yes/no)
```

## Worked example — already optimized

```text
TARGET: /app/well-managed-logs
VERDICT: OPTIMIZED
REASON: Application log group with 14-day retention, 4 metric filters
  replacing all scheduled Insights queries, Firehose S3 export for
  compliance archive with Glacier lifecycle, agent batch_count=10000,
  and account-level data protection policy enabled. All seven
  optimization dimensions pass. No further cost reduction possible.
RECOMMENDATION:
  Current: 14 days retention, 84 GB/month ingested, 4 metric filters,
    Firehose S3 export (GIR 90d → Deep Archive 2yr), agent batch_count=10000
  Dimensions checked: retention ✓ (14d)  queries ✓ (3 ad-hoc Insights only)
    agent ✓ (batch_count=10000)  cold-storage ✓ (S3 + lifecycle)
    subscription ✓ (Firehose only)  destination ✓ (app logs)
    data-protection ✓ (account policy enabled)
  Confidence: HIGH — all dimensions verified against describe-log-groups,
    describe-metric-filters, CloudTrail query history, agent config, and
    Cost Explorer.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate if ingestion volume changes or at
    quarterly FinOps review.
```

## Worked example — NEED_MORE_INFO (metrics absent)

```text
TARGET: /app/new-service-logs
VERDICT: NEED_MORE_INFO
REASON: IncomingBytes metric is absent for the requested 30-day window.
  The log group may be newly created with no ingested data, or the IAM
  role may deny cloudwatch:GetMetricStatistics. Cannot make a cost
  optimization recommendation without baseline ingestion data.
RECOMMENDATION:
  Current: RetentionInDays unknown, ingestion volume unknown
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the log group is receiving data:
     aws logs describe-log-streams --log-group-name /app/new-service-logs
       --order-by LastEventTime --descending --max-items 5
  2. Verify IAM permissions for CloudWatch:
     aws iam simulate-principal-policy --policy-source-arn <role-arn>
       --action-names logs:DescribeLogGroups logs:GetMetricData
  3. Wait 14-30 days for representative observation.
  4. Re-evaluate with IncomingBytes + IncomingLogEvents data.
  Do NOT optimize based on assumed metrics.
```

## End-to-end optimisation walkthrough

This example walks through the complete workflow: analyse metrics,
identify waste via the decision tree, calculate savings, and provide
migration steps.

**Log group profile:**
- Log group: `/app/api-gateway-access-logs`
- Retention: Never expire (`RetentionInDays` absent)
- Region: us-east-1
- StoredBytes: 8,400 GB (12 months accumulated)
- IncomingBytes: 28 GB/day (840 GB/month)
- IncomingLogEvents: 12M/day
- Logs Insights queries: 300/month scanning 200 GB each
- Agent: N/A (API Gateway native log delivery)

**Step 1 — Analyse current cost:**
```
Ingestion: 840 GB × $0.50 = $420.00/month
Storage:   8,400 GB × $0.03 = $252.00/month
Insights:  300 × 200 GB × $0.005 = $300.00/month
Total: $972.00/month ($11,664/year)
```

**Step 2 — Route through the retention decision tree:**
- RetentionInDays absent → Never expire → highest-priority finding.
- No compliance mandate for access logs beyond 30 days.
- Set retention to 30 days.

**Step 3 — Route through the query migration tree:**
- 300 queries/month, all scanning 200 GB. All are count-by-status-code
  and avg-latency-by-endpoint aggregations.
- All 4 patterns are expressible as metric filters.
- Convert to 4 metric filters → eliminates $300/month.

**Step 4 — Calculate projected cost:**
```
Ingestion: 840 GB × $0.50 = $420.00 (unchanged)
Storage:   840 GB × $0.03 = $25.20 (steady-state at 30d)
Insights:  4 metric filters × $0.00 = $0.00
Total: $445.20/month
```

**Step 5 — Savings summary:**
```
Monthly saving: $972.00 − $445.20 = $526.80 (54.2%)
Annual saving: $6,321.60
```

**Step 6 — Emit the output block:**
```text
TARGET: /app/api-gateway-access-logs
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: API Gateway access log group with Never-expire retention
  accumulating 8,400 GB. Combined with 300 Logs Insights queries/month
  scanning 200 GB each ($300/month). Retention to 30 days + query
  migration to metric filters eliminates 54% of monthly cost.
RECOMMENDATION:
  Current: Never expire, 840 GB/month ingested, 8,400 GB stored, 300 Insights queries/month
  Proposed: 30 days, 840 GB/month ingested, 840 GB stored (steady), 0 Insights queries (4 metric filters)
  Dimensions changed: retention (Step 1) + queries (Step 2)
  Dimensions checked: retention → (Never to 30d)  queries → (Insights to filters)
    agent ✓ (API Gateway native)  cold-storage ✓ (30d under S3 crossover)
    subscription ✓ (none)  destination ✓ (access logs)  data-protection ✓
  Confidence: HIGH — describe-log-groups confirms Never expire;
    CloudTrail confirms 300 queries/month; all query patterns verified
    as metric-filter-compatible.
ESTIMATED_SAVINGS:
  Current monthly: $972.00
    ingestion: 840 GB × $0.50 = $420.00
    storage: 8,400 GB × $0.03 = $252.00
    insights: 300 × 200 GB × $0.005 = $300.00
  Projected monthly: $445.20
    ingestion: 840 GB × $0.50 = $420.00
    storage: 840 GB × $0.03 = $25.20
    insights: 4 metric filters × $0.00 = $0.00
  Monthly saving: $526.80 ($972.00 − $445.20)
  Annual saving: $6,321.60
MIGRATION_STEPS:
  1. Set retention to 30 days:
     aws logs put-retention-policy
       --log-group-name /app/api-gateway-access-logs --retention-in-days 30
  2. Create 4 metric filters:
     aws logs put-metric-filter --log-group-name /app/api-gateway-access-logs
       --filter-name Status5xxCount --filter-pattern '" 5"'
       --metric-transformations
       metricName=Status5xx,metricNamespace=APIGateway,metricValue=1,defaultValue=0
  3. Create dashboard panels on the new metrics.
  4. Verify retention applied and old logs deleted within 24 hours.
  5. Verify metric data within 5 minutes of log arrival.
CONFIRM: About to put-retention-policy (Never → 30 days) and create 4
  metric filters on /app/api-gateway-access-logs. Saving $526.80/month
  (54.2%). Proceed? (yes/no)
```

---

## Logs Insights cost estimation (moved from SKILL.md Step 2)

**Logs Insights cost estimation:**
```
insights_monthly_cost = queries_per_month × avg_GB_scanned_per_query × $0.005

Example: 450 queries/month × 120 GB/query × $0.005 = $270.00/month
         Converting to 5 metric filters: $0.00/month (metric filters are free)
         Net saving: $270.00/month
```

---

## PutLogEvents request saving from buffer tuning (moved from SKILL.md Step 3)

**PutLogEvents request saving from buffer tuning:**
```
old_requests = log_events_per_hour / old_batch_count
new_requests = log_events_per_hour / new_batch_count
monthly_saving = (old_requests - new_requests) × 730 × $0.40/1,000,000

Example: 12M events/hour, batch_count 1000 → 10000:
  old_requests: 12,000/hour; new_requests: 1,200/hour
  Monthly saving: (12,000 - 1,200) × 730 × $0.40/1M = $3.16/host/month
  For a fleet of 100 hosts: $316/month
```

---

## Firehose S3 vs CloudWatch Logs cost comparison (moved from SKILL.md Step 4)

**Cost comparison (500 GB/month ingested, 2-year retention):**
```
CloudWatch Logs only:
  Ingestion:   500 GB × $0.50 = $250.00/month
  Storage:     500 × 24 months × $0.03 = $360.00/month (grows over time)
  Total at 24 months: ~$610/month → $14,640 over 2 years

Firehose → S3 (Glacier Instant Retrieval after 90 days):
  Firehose:    500 GB × $0.029 = $14.50/month
  S3 Standard:  500 GB × $0.023 = $11.50/month (first 90 days)
  S3 GIR:       500 GB × $0.012 = $6.00/month (after 90 days)
  Athena (queries on demand): ~$5.00/month
  Total steady-state: ~$37/month → $888 over 2 years
  Saving: $13,752 over 2 years (94% reduction)
```

---

## Impact estimation formula (moved from SKILL.md Step 8)

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (monthly_ingested_GB × $0.50)
  + (monthly_stored_GB × $0.03)
  + (monthly_putlogevents_requests / 1M × $0.40)
  + (monthly_insights_GB_scanned × $0.005)

projected_monthly_cost =
  (projected_ingested_GB × $0.50)
  + (projected_stored_GB × $0.03)
  + (projected_putlogevents_requests / 1M × $0.40)
  + (projected_insights_GB_scanned × $0.005)
  + (firehose_GB × $0.029 if S3 export added)
  + (s3_stored_GB × $0.023 if S3 export added)

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly ingestion volume, current vs projected
retention, Logs Insights query volume, pricing region, agent fleet size.

---

## Minimal output template (moved from SKILL.md Output format)

```text
TARGET: <log-group-name or account-level>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <retention> days, <ingested GB>/month, <Insights queries>/month, <agent batch_count>
  Proposed: <retention> days, <ingested GB>/month, <Insights queries>/month, <agent batch_count>
  Dimensions changed: <retention | queries | agent | cold-storage | subscription | destination | data-protection>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (ingestion volume, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <log-group-name> in <region>.
  Proceed? (yes/no)"
```
