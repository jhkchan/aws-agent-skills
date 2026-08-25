# Worked Examples — CloudTrail Cost Optimizer

Full worked examples covering org-trail consolidation, data-event
curation, S3 lifecycle rollout, CloudTrail Lake scoping, already-
optimized configurations, NEED_MORE_INFO, and an end-to-end
optimisation walkthrough. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — org-trail consolidation (redundant member trails)

```text
TARGET: aws-organizational-trail-primary
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Organization with 13 trails (1 org + 12 member) — each member
  trail duplicates management events already captured by the org trail.
  Per-trail KMS, SNS, and PUT overhead multiplies linearly across the
  redundant 12 trails. Consolidating to the single org trail eliminates
  100% of duplicate volume.
RECOMMENDATION:
  Current: 1 org trail + 12 member trails, 13 KMS keys, 13 SNS topics
  Proposed: 1 org trail + 1 shared CMK + 1 SNS topic
  Dimensions changed: consolidation (Step 1) + kms_sns_insights (Step 6)
  Confidence: HIGH — org trail is RUNNING and confirmed multi-region;
    each member trail captures a subset of the org trail's events.
ESTIMATED_SAVINGS:
  Current monthly: $174.60
    S3 PUT (duplicate): 12 × 1,400,000 × $0.005/1000 = $84.00
    S3 storage (duplicate): 200 GB × $0.023 = $4.60
    KMS requests: 12 × 1,400,000 × $0.03/10000 = $50.40
    KMS key monthly: 12 × $1.00 = $12.00
    SNS publishes: 12 × 1,400,000 × $0.50/1M = $8.40
    Insights events: 0 (not enabled)
    CloudWatch Logs: 0 (S3-only)
    Lake ingestion: 0 (not configured)
  Projected monthly: $14.51
    S3 PUT (org trail only): 1,400,000 × $0.005/1000 = $7.00
    S3 storage: 17 GB × $0.023 = $0.39
    KMS requests: 1,400,000 × $0.03/10000 = $4.20
    KMS key: $1.00
    SNS: 1,400,000 × $0.50/1M = $0.70
    Insights: $0
    CloudWatch Logs: $0
    Lake ingestion: $0
  Monthly saving: $160.09
    ($174.60 − $14.51 = $160.09 ✓)
  Annual saving: $1,921.08
MIGRATION_STEPS:
  1. Verify org trail is RUNNING and capturing all member events:
     aws cloudtrail get-trail --name aws-organizational-trail-primary
     aws cloudtrail list-trails --query 'Trails[*].{Name: TrailARN, Region: HomeRegion}'
  2. For each member account, verify recent log delivery from the org
     trail before deletion:
     aws cloudtrail lookup-events --start-time $(date -u -d '-24 hours' +%FT%TZ) \
       --end-time $(date -u +%FT%TZ) \
       --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole
  3. Snapshot existing member trail configurations (rollback safety):
     aws cloudtrail describe-trails > member-trail-snapshots.json
  4. Delete member trails one at a time, verifying org-trail coverage
     after each:
     aws cloudtrail delete-trail --name member-trail-acct-2
     # ... iterate through acct-3 .. acct-13
  5. After all deletions, re-query Cost Explorer at 7 days to confirm
     CloudTrail line dropped:
     aws ce get-cost-and-usage --time-period Start=$(date -d '-7 days' +%F),End=$(date +%F) \
       --granularity DAILY --metrics BlendedCost \
       --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS CloudTrail"]}}'
CONFIRM: About to delete 12 member trails (member-trail-acct-2 through
  member-trail-acct-13). The org trail aws-organizational-trail-primary
  is RUNNING and multi-region. Monthly saving $160.09 (92% on overhead).
  Proceed? (yes/no)
```

**Key nuance:** org trail coverage must be verified before any member
trail deletion. If the org trail has a regional gap, member trails may
be the only source for that region.

## Worked example — data event curation (high-volume low-value buckets)

```text
TARGET: aws-organizational-trail-data-event-volume-curation
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Trail captures S3 data events on All Buckets including 117.8M
  events/month (83%) from low-audit-value buckets (cdn-access-logs,
  elb-access-logs, cloudtrail-logs, backup-prod, audit-archive). Data
  events bill at $0.10/100k regardless of trail count; curating to the
  three high-value buckets drops data event fees 83%.
RECOMMENDATION:
  Current: All-Buckets S3 data events, 142.5M events/month
  Proposed: Advanced event selectors with 3 high-value buckets, 24.7M events/month
  Dimensions changed: data_events (Step 2)
  Confidence: HIGH — S3 access logs identify low-value buckets; advanced
    event selectors support ARN prefix matching.
ESTIMATED_SAVINGS:
  Current monthly: $142.50
    Data events: 142,500,000 / 100,000 × $0.10 = $142.50
  Projected monthly: $24.70
    Data events: 24,700,000 / 100,000 × $0.10 = $24.70
  Monthly saving: $117.80
    ($142.50 − $24.70 = $117.80 ✓)
  Annual saving: $1,413.60
MIGRATION_STEPS:
  1. Snapshot current event selectors (rollback safety):
     aws cloudtrail get-event-selectors --trail-name aws-organizational-trail-data-event-volume-curation \
       > event-selectors-backup.json
  2. Apply advanced event selectors with curated bucket list:
     aws cloudtrail put-event-selectors \
       --trail-name aws-organizational-trail-data-event-volume-curation \
       --advanced-event-selectors '[
         {"Name":"ManagementEvents","FieldSelectors":[
           {"Field":"eventCategory","Equals":["Management"]}
         ]},
         {"Name":"CuratedS3Audit","FieldSelectors":[
           {"Field":"eventCategory","Equals":["Data"]},
           {"Field":"resources.type","Equals":["AWS::S3::Object"]},
           {"Field":"resources.ARN","StartsWith":[
             "arn:aws:s3:::financial-records/",
             "arn:aws:s3:::pii-data/",
             "arn:aws:s3:::transaction-logs/"
           ]}
         ]}
       ]'
  3. After 24 hours, verify high-value events are still captured:
     aws cloudtrail lookup-events --start-time $(date -u -d '-24 hours' +%FT%TZ) \
       --end-time $(date -u +%FT%TZ) \
       --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::S3::Object
  4. After 7 days, verify data event volume dropped in Cost Explorer.
CONFIRM: About to replace All-Buckets S3 data events with curated list
  (3 high-value buckets). Data event volume drops 83%. Monthly saving
  $117.80. Proceed? (yes/no)
```

## Worked example — S3 lifecycle rollout

```text
TARGET: trail-s3-lifecycle-glacier-transition
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: CloudTrail log bucket has 850 GB in Standard storage with no
  lifecycle policy. CloudTrail logs are write-once-read-rarely (42 GETs
  in 90 days). Transition to Glacier IR at 90 days and Deep Archive at
  180 days preserves audit readability while cutting storage 80%+.
RECOMMENDATION:
  Current: 850 GB Standard, no lifecycle
  Proposed: 30d → Intelligent-Tiering, 90d → Glacier IR, 180d → Deep Archive, 365d → Expire
  Dimensions changed: lifecycle (Step 3)
  Confidence: HIGH — storage math is deterministic; read volume is
    negligible so retrieval latency is not a concern.
ESTIMATED_SAVINGS:
  Current monthly: $19.55
    S3 Standard: 850 GB × $0.023 = $19.55
  Projected monthly: $3.78 (steady-state at 850 GB distributed across tiers)
    Standard (first 30 days, ~95 GB): 95 × $0.023 = $2.19
    Intelligent-Tiering (31-90 days, ~190 GB): 190 × $0.0025 = $0.48
    Glacier IR (91-180 days, ~285 GB): 285 × $0.004 = $1.14
    Deep Archive (181-365 days, ~280 GB): 280 × $0.00099 = $0.28
  Monthly saving: $15.77
    ($19.55 − $3.78 = $15.77 ✓)
  Annual saving: $189.24
MIGRATION_STEPS:
  1. Apply lifecycle policy to CloudTrail prefix:
     aws s3api put-bucket-lifecycle-configuration \
       --bucket cloudtrail-logs-standalone-us-east-1 \
       --lifecycle-configuration file://cloudtrail-lifecycle.json
  2. Verify the policy took effect:
     aws s3api get-bucket-lifecycle-configuration \
       --bucket cloudtrail-logs-standalone-us-east-1
  3. After 24 hours, query S3 storage metrics to confirm transitions:
     aws cloudwatch get-metric-statistics --namespace AWS/S3 \
       --metric-name BucketSizeBytes \
       --dimensions Name=BucketName,Value=cloudtrail-logs-standalone-us-east-1 \
                     Name=StorageType,Value=GlacierInstantRetentionStorage \
       --start-time $(date -u -d '-24 hours' +%FT%TZ) \
       --end-time $(date -u +%FT%TZ) --period 86400 --statistics Average
  4. After 30 days, validate full lifecycle rollout.
CONFIRM: About to apply S3 lifecycle to cloudtrail-logs-standalone-us-east-1
  (Intelligent-Tiering 30d, Glacier IR 90d, Deep Archive 180d, Expire 365d).
  Monthly saving $15.77 (81% on storage). Proceed? (yes/no)
```

## Worked example — CloudTrail Lake event data store scoping

```text
TARGET: trail-cloudtrail-lake-scoping
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: CloudTrail Lake EDS ingests 100 GB/month across Management and
  Data event categories, but the use case (IAM access pattern analysis)
  only requires Management events. Data events are 92% of ingestion
  volume and add $69/month in pure ingestion cost without enabling any
  IAM query.
RECOMMENDATION:
  Current: EDS ingesting Management + Data, 100 GB/month
  Proposed: EDS ingesting Management only, 8 GB/month
  Dimensions changed: lake (Step 4)
  Confidence: HIGH — use case is explicitly IAM analysis; IAM events
    are all in the Management event category.
ESTIMATED_SAVINGS:
  Current monthly: $83.07
    Ingestion: 100 GB × $0.75 = $75.00
    Retention (90d, 300 GB): 300 × $0.023 = $6.90
    Queries: $0 (free on Lake)
    Other: ~$1.17
  Projected monthly: $8.59
    Ingestion: 8 GB × $0.75 = $6.00
    Retention (90d, 24 GB): 24 × $0.023 = $0.55
    Queries: $0
    Other: ~$2.04
  Monthly saving: $74.48
    ($83.07 − $8.59 = $74.48 ✓)
  Annual saving: $893.76
MIGRATION_STEPS:
  1. Export current EDS contents (safety backup before filter):
     aws cloudtrail start-query --query-statement \
       "SELECT * FROM <EDS_ID> WHERE eventtime > timestamp '2026-05-11'"
  2. Update EDS with event-category filter for Management only:
     aws cloudtrail update-event-data-store \
       --event-data-store 7a7b8c9d-0e1f-2345-6789-0123456789ab \
       --advanced-event-selectors '[{
         "Name":"ManagementOnly",
         "FieldSelectors":[
           {"Field":"eventCategory","Equals":["Management"]}
         ]
       }]'
  3. After 24 hours, verify ingestion volume dropped:
     aws cloudtrail list-event-data-stores \
       --query 'EventDataStores[*].{SizeBytes: SizeBytes}'
  4. After 7 days, query Cost Explorer to confirm Lake line dropped.
CONFIRM: About to update EDS org-audit-eds to Management-only ingestion.
  Ingestion drops 92%. Monthly saving $74.48 (90%). Proceed? (yes/no)
```

## Worked example — already-optimized org trail

```text
TARGET: trail-already-optimized-org-setup
VERDICT: OPTIMIZED
REASON: Org trail with curated S3 data events on 3 high-value buckets,
  S3 lifecycle (Glacier IR @ 90d, Deep Archive @ 180d), single shared
  CMK, Insights scoped to management account only, no CloudWatch Logs
  delivery, no CloudTrail Lake duplication, Athena partition projection
  enabled. All seven dimensions pass — no FURTHER_OPTIMIZATION_AVAILABLE.
RECOMMENDATION:
  Current: org trail + curated events + lifecycle + shared CMK + Insights on mgmt only
  Proposed: (no change)
  Dimensions changed: (none)
  Dimensions checked: consolidation ✓ (org trail covers all members)
    data_events ✓ (3 high-value buckets curated)  lifecycle ✓ (Glacier IR + Deep Archive)
    lake ✓ (not configured)  logs ✓ (S3-only)  kms_sns_insights ✓ (shared CMK, scoped Insights)
    athena ✓ (partition projection enabled)
  Confidence: HIGH — every dimension matches the OPTIMIZED baseline.
ESTIMATED_SAVINGS:
  Current monthly: $487.30
  Projected monthly: $487.30
  Monthly saving: $0.00
  Annual saving: $0.00
MIGRATION_STEPS: (none — continue monitoring; revisit if data event
  volume grows > 50% or compliance retention SLA changes)
CONFIRM: (no state change; nothing to confirm)
```

## Worked example — NEED_MORE_INFO

```text
TARGET: trail-without-cost-data
VERDICT: NEED_MORE_INFO
REASON: Trail inventory is present but 30-day Cost Explorer window is
  absent and S3 BucketSizeBytes metric is empty. Cannot compute
  projected monthly saving without baseline cost data.
RECOMMENDATION:
  Current: insufficient data to classify
  Proposed: pull 30-90 day Cost Explorer + S3 storage metrics
  Dimensions changed: (none — blocked on data gate)
  Confidence: LOW — needs 30-day baseline.
ESTIMATED_SAVINGS: (cannot compute)
MIGRATION_STEPS:
  1. Pull Cost Explorer for CloudTrail line over 30-90 days:
     aws ce get-cost-and-usage \
       --time-period Start=2026-07-11,End=2026-08-11 \
       --granularity MONTHLY --metrics BlendedCost \
       --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS CloudTrail"]}}'
  2. Pull S3 storage metrics for the CloudTrail prefix:
     aws cloudwatch get-metric-statistics --namespace AWS/S3 \
       --metric-name BucketSizeBytes --period 86400 --statistics Average
  3. Re-run the skill with the populated data.
CONFIRM: (no state change)
```

## End-to-end optimisation walkthrough — multi-account org

A FinOps review for an AWS Organization with 50 member accounts.

**Phase 1 — Inventory (Step 0 + data gate):**
1. Run `describe-trails` in each member account (via assumed role) to
   enumerate per-account trails. Identify 47 member trails + 1 org
   trail.
2. Run `get-event-selectors` on each trail. Catalog data event sources.
3. Run `get-bucket-lifecycle-configuration` on each log bucket. Note
   35 buckets have no lifecycle policy.
4. Run `list-event-data-stores` to enumerate Lake EDSs. Identify 3
   redundant EDSs.

**Phase 2 — Consolidation (Step 1):**
1. Verify org trail is RUNNING and multi-region.
2. Snapshot member trail configurations.
3. Delete member trails in batches of 5 accounts at a time, verifying
   org-trail coverage after each batch via `lookup-events` test.
4. Update CloudWatch dashboards that depended on per-account trails.

**Phase 3 — Data event curation (Step 2):**
1. List all S3 buckets with data event volume via CloudTrail Lake
   query.
2. Classify each bucket as HIGH/MEDIUM/LOW audit value based on data
   sensitivity (tags, classification labels).
3. Apply advanced event selectors with the curated bucket list.
4. Verify data event volume dropped in Cost Explorer at 7 days.

**Phase 4 — Lifecycle rollout (Step 3):**
1. Apply the standard CloudTrail lifecycle policy to each log bucket.
2. Verify via S3 storage metrics at 30 days.

**Phase 5 — Lake scoping (Step 4):**
1. For each EDS, audit the use case (IAM analysis, threat detection,
   compliance archive).
2. Apply event-category filters to match the use case.
3. Decommission redundant EDSs after exporting historical data.

**Phase 6 — KMS/SNS/Insights tuning (Step 6):**
1. Consolidate member-account CMKs to a single shared CMK (with
   appropriate cross-account policy).
2. Disable Insights on low-risk member accounts.

**Phase 7 — Reporting:**
1. Re-run Cost Explorer at 30 days post-changes.
2. Compute cumulative annual savings.
3. Document residual CloudTrail spend by dimension.

Typical outcomes for a 50-account org:
- Consolidation: $1,500-$3,000/year saved
- Data event curation: $2,000-$15,000/year saved
- Lifecycle: $500-$2,000/year saved
- Lake scoping: $1,000-$5,000/year saved
- Total: $5,000-$25,000/year (10-30% of CloudTrail spend)

## Extended NEVER list

6. **NEVER delete a trail without snapshotting its configuration.**
   `describe-trails` output is the rollback document.

7. **NEVER recommend S3 Object Lock as a tamper-evidence replacement
   for log file integrity validation without confirming the lock is
   COMPLIANCE mode (not GOVERNANCE).** Governance mode can be bypassed
   by root.

8. **NEVER recommend Requester Pays on a log bucket read by another
   monitored account in the same org.** It double-counts the org's
   bill.

9. **NEVER recommend disabling CloudTrail Insights on the org
   management account.** That account is the highest-risk surface for
   privilege escalation anomalies.

10. **NEVER recommend Lake federated queries across EDSs without
    auditing the query cost.** Cross-EDS queries scan all matched
    partitions at Athena rates.

11. **NEVER delete an Event Data Store without first exporting its
    contents.** `start-query` to S3 is the only backup path; EDS
    deletion is irreversible.

12. **NEVER recommend increasing retention without recomputing the
    storage budget.** Each additional 30 days of retention at 100
    GB/month ingest adds ~$70/year in storage.

## Operational edge cases

### CloudTrail in standalone (non-org) accounts

For accounts not in an AWS Organization, Step 1 consolidation is N/A.
Focus shifts to data event curation, lifecycle, and Lake scoping.

### Multi-region data residency requirements

For workloads with data residency requirements (e.g., EU data stays in
EU), the org trail may not be sufficient. Recommendation: regional
trails with non-overlapping event selectors, no consolidation possible.

### CloudTrail alongside AWS Config

AWS Config consumes CloudTrail events for configuration history. Verify
Config aggregators don't depend on per-account trails before deletion.

### Detective / GuardDuty integrations

Both consume CloudTrail events indirectly via AWS service internals;
they don't depend on customer trails. Trail deletion is safe.

### CloudTrail Lake delegated administrator

For orgs using delegated administrator for CloudTrail Lake, EDS
management is isolated from the org management account. Verify the
delegated admin account before any EDS changes.

## Output format (per operation) — full spec (moved from SKILL.md)

```text
TARGET: <trail-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <trail inventory + data events + storage class + Lake + Logs>
  Proposed: <consolidated inventory + curated events + Glacier + Lake scope>
  Dimensions changed: <consolidation | data_events | lifecycle | lake | logs | kms_sns_insights | athena>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (event volumes, storage size, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <trail-name> in <region>.
  Proceed? (yes/no)"
```

## Step 1 — the consolidation math (moved from SKILL.md)

**The consolidation math:**
```
duplicate_management_event_cost =
  (extra_trail_count × log_files_per_month × per_file_overhead)

per_file_overhead =
  S3 PUT ($0.005/1000) +
  KMS GenerateDataKey ($0.03/10000) +
  SNS publish ($0.50/1000000) ≈ $0.0000056/file

Example: 10 member trails, 1.4M log files/month each:
  duplicate cost = 9 × 1,400,000 × $0.0000056 = $70.56/month in overhead
  + duplicate storage: 9 × 1.4M × 4KB avg = 50.4 GB × $0.023 = $1.16/month
```

## Step 2 — data-event saving from curation (moved from SKILL.md)

**Data-event saving from curation:** Monthly saving equals
`(old_volume − curated_volume) / 100000 × $0.10`. Example: 142M
events/month with 80% low-value buckets; curating drops volume to 28M.
Monthly saving: `((142M − 28M) / 100k) × $0.10 = $114/month` on data
event fees plus ~600 GB/month saved S3 storage.

## Step 3 — storage saving math (moved from SKILL.md)

**Storage saving math (500 GB example):**
```
Standard only:        500 × $0.023 = $11.50/month steady-state
With lifecycle:       ~$1.79/month steady-state (98.7% saving on archive tier)
Note: Glacier IR retrieves cost $0.03/GB but reads are rare (audit queries).
```

## Step 4 — Lake cost math (moved from SKILL.md)

**Lake cost math (100 GB/month ingest, 90-day retention):**
```
Before: ingestion 100 × $0.75 + retention 300 GB × $0.023 = $81.90/month
After (mgmt-only, 90% cut): ingestion 10 × $0.75 + 30 GB × $0.023 = $8.19/month
Saving: $73.71/month (90%)
```

## Step 5 — Logs delivery cost math (moved from SKILL.md)

**Logs delivery cost math:**
```
monthly_logs_cost = monthly_ingested_GB × $0.50
                 + monthly_storage_GB × $0.03 (Standard)

Example: 100 GB/month ingest = $50/month in Logs alone
         Equivalent S3 storage: 100 GB × $0.023 = $2.30/month
         Saving from disabling Logs: $47.70/month (95%)
```

## Step 6 — KMS key consolidation math (moved from SKILL.md)

**KMS key consolidation:**
```
Per-key monthly cost: $1.00 (CMK) + ~$0.50/request fees
Per-trail-with-own-key overhead: $1.50/month × trail_count

Recommendation: Share one CMK across all trails when key policy allows.
```
