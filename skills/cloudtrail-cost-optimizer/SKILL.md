---
name: cloudtrail-cost-optimizer
description: 'Optimises AWS CloudTrail cost across seven dimensions: trail consolidation (single organization trail replaces N per-region or member-account trails, eliminating duplicate log volume and per-trail KMS/SNS overhead), management-vs-data-event volume analysis (data events are ~10x costlier per event than management events — curate S3/Lambda data event sources), S3 lifecycle policy for log files (Glacier Instant/Deep Archive transition after 90 days eliminates ~80% of Standard storage cost), CloudTrail Lake event-data-store cost (per-GB ingestion at $0.75/GB-month plus retention — partition with event-category filters), CloudWatch Logs delivery cost (avoid dual-publishing CloudTrail to both S3 and CloudWatch Logs when only one consumer exists), SNS notification cost ($0.50 per million notifications — consolidate trail SNS topics), KMS key cost per trail (one CMK shared across org trail, not one per trail), Insights event cost ($0.50 per 100k management events — enable only for accounts with anomalous activity), organizational trail vs member trail (deduplication — org trail writes ALL member events once), log file integrity validation overhead (S3 PUT cost doubles for digest files — disable only when S3 Object Lock is enforced), S3 Requester Pays for cross-account log access, Athena partition projection for cost analysis (avoid full-table scans of CloudTrail logs). Uses aws cloudtrail describe-trails, get-event-selectors, get-insights-selectors, aws organizations list-accounts, aws s3api get-bucket-lifecycle-configuration, aws cloudtrail list-edges, aws kms describe-key, and aws ce get-cost-and-usage to project monthly savings. Emits OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE. Use when reviewing CloudTrail spend, planning trail consolidation, evaluating data event volume, or a FinOps governance review.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted trail configurations and Cost Explorer exports. Live-account optimization uses aws cloudtrail describe-trails, get-event-selectors, get-insights-selectors, get-event-data-store, aws organizations describe-organization, list-accounts, aws s3api get-bucket-lifecycle-configuration, head-bucket, aws kms describe-key, get-key-rotation-status, aws ce get-cost-and-usage (AWS CLI v2, SSO or key-based credentials). Pricing references us-east-1 published rates as of 2026; re-state regional rates from the reference matrix for other regions.
keywords:
- CloudTrail
- trail consolidation
- organization trail
- cost optimization
- data events
- management events
- S3 lifecycle
- Glacier transition
- CloudTrail Lake
- event data store
- CloudWatch Logs
- SNS notification
- KMS key
- Insights
- log file integrity
- Athena partition projection
- Requester Pays
- FinOps
- governance
- audit logging
tags:
- cloudtrail
- governance
- cost-optimization
- finops
- audit-logging
- organizational-trail
- s3-lifecycle
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising CloudTrail spend, consolidating multi-region or member trails into a single org trail, curating data event sources (S3/Lambda data events), tuning S3 lifecycle for log buckets, reviewing CloudTrail Lake event data store ingestion cost, disabling dual-publishing to CloudWatch Logs, consolidating KMS keys per trail, evaluating CloudTrail Insights cost, or running a governance FinOps sweep.
  when_not_to_use: CloudTrail functional troubleshooting (use cloudtrail-missing-events-troubleshooter or cloudtrail-gap-troubleshooter), CloudTrail Lake query authoring (use cloudtrail-lake-operator), or CloudTrail alert automation (use cloudtrail-alert-automator). This skill focuses on cost-driven optimization decisions, not on whether events are missing or alerts fire.
  activation_triggers:
  - optimise CloudTrail cost
  - CloudTrail trail consolidation
  - CloudTrail org trail vs member trail
  - CloudTrail data event volume
  - CloudTrail S3 lifecycle
  - CloudTrail log file Glacier transition
  - CloudTrail Lake event data store cost
  - CloudTrail CloudWatch Logs delivery cost
  - CloudTrail KMS key per trail
  - CloudTrail Insights event cost
  - CloudTrail log file integrity validation
  - CloudTrail SNS notification cost
  - CloudTrail organizational trail deduplication
  - CloudTrail Athena partition projection
  - CloudTrail FinOps savings
  - CloudTrail monthly savings estimate
  - reduce CloudTrail bill
  - governance cost review
  invocation_schema: 'Input: either (a) a CloudTrail trail name + live-account context, (b) an Organizations account list with per-trail configuration summary, OR (c) a Cost Explorer export of CloudTrail spend with at least 30 days of observation plus trail configurations. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per trail (or per account for consolidation cases), where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nTrailName: aws-organizational-trail\nIsOrganizationTrail: true\nIsMultiRegionTrail: true\nIncludeManagementEvents: true\nDataEventSources:\n  - S3 (all buckets) — 142,000,000 events/month\n  - Lambda (all functions) — 8,400,000 events/month\nInsightsEnabled: true (both ApiCallRateInsight and ApiCallErrorInsight)\nKMSKeyId: alias/cloudtrail-org-cmk\nCloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:cloudtrail-org\nS3Bucket: org-cloudtrail-logs-us-east-1\nS3LifecyclePolicy: none\nRegion: us-east-1\nMonthlySpend: $1,847.32\nDataEventMonthlyVolume: 150.4M events\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# CloudTrail Cost Optimizer

## What this skill does

Translates a CloudTrail trail configuration into a concrete cost-
optimization recommendation with a dollar-denominated savings estimate.
The verdict is the highest-leverage action across seven dimensions —
trail consolidation, data-event curation, S3 lifecycle, CloudTrail Lake,
CloudWatch Logs delivery, KMS key sharing, and Insights tuning — applied
in priority order. Always pairs the recommendation with exact CLI
commands (or CloudFormation/Terraform snippets for trail recreation).

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why org-trail consolidation is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a trail |
| Pre-flight data gate | Trail config, S3 lifecycle, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Data event cost curve, Lake vs S3, digest PUTs | Edge cases |
| Step 1 Trail consolidation | Org trail replaces N member trails | The headline savings dimension |
| Step 2 Data event curation | S3/Lambda data event volume reduction | High-volume accounts |
| Step 3 S3 lifecycle for logs | Glacier transition, versioning cleanup | Long-retention trails |
| Step 4 CloudTrail Lake cost | Event data store ingestion + retention | EDS-based analysis |
| Step 5 CloudWatch Logs delivery | Dual-publishing elimination | S3-only consumers |
| Step 6 KMS, SNS, Insights | Shared CMK, topic consolidation, Insights gating | Per-trial overhead |
| Step 7 Athena partition projection | Log query cost control | Cost analysis queries |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, log integrity, retention SLA | Before any apply CLI |

## Quick start

- **Org trail consolidation is the #1 lever.** A single organization
  trail captures every member-account event across every region. N
  member-account trails each capture (and store, and KMS-encrypt, and
  SNS-notify) the SAME management events for the org's primary account,
  causing pure duplicate volume that scales linearly with account count.
  Replacing 10 member trails with 1 org trail removes ~90% of management-
  event log volume for the org-management account.
- **Cost formula (memorise this):**
  `monthly_cost = (data_events × $0.10/100k)
               + (management_events × $0.00 free)
               + (s3_storage_GB × $0.023 Standard)
               + (lake_ingestion_GB × $0.75)
               + (kms_requests × $0.03/10k)
               + (sns_notifications × $0.50/1M)
               + (insights_events × $0.50/100k)`
- **Data events are 10x costlier than management events.** Management
  events are free on the first trail per region; data events (S3, Lambda,
  DynamoDB, etc.) bill at $0.10 per 100,000 events. Always curate data
  event sources to high-value buckets/functions only.
- **S3 lifecycle is a one-click ~80% cut.** CloudTrail log files are
  write-once-read-rarely. Transition to Glacier Instant Retrieval after
  90 days and Deep Archive after 180 days for ~80% storage cost reduction
  without losing audit-query ability.

## Mindset

CloudTrail cost optimization is a governance-versus-spend decision, not
a pure storage exercise. The goal is the trail configuration that
preserves audit completeness for security-critical events while
eliminating duplicate log volume and curating high-cardinality data
events — not the absolute minimum storage bill that breaks compliance.

Four principles guide every recommendation:

- **Capture once, store once.** An organization trail emits each event
  exactly once. Member-account trails re-emit the org-management
  account's API calls as the trail assumes role in each member — pure
  duplicate volume billed at full S3 storage + KMS + SNS rates.

- **Data events are 10x costlier than management events.** Management
  events are free (first trail per region). Data events bill per 100k.
  Rank data-event sources by event volume × audit value; drop low-value
  high-volume sources (e.g., S3 data events on log buckets, ELB access
  logs, CloudTrail's own S3 writes).

- **Log files are cold data.** CloudTrail log files are written once and
  read only during investigations. The cost-optimal storage class is
  almost never Standard beyond 30 days. Glacier Instant Retrieval keeps
  ms-latency reads at 20% of Standard cost.

- **Lake is for query, S3 is for archive.** CloudTrail Lake charges
  $0.75/GB-month ingestion plus retention-tier storage. Use Lake only
  when you need interactive SQL queries; for compliance archive, S3 +
  Athena with partition projection is 10x cheaper.

## Quick reference — verdict thresholds

| Observation (30-90 day window) | Verdict | Recommendation |
|---|---|---|
| > 1 trail per org AND none has `IsOrganizationTrail=true` | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — create single org trail, delete member trails |
| Org trail exists AND member trails remain active (duplicate capture) | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — delete member trails; org trail already covers |
| S3 data events = `All Buckets` AND high-volume low-value buckets (logs, ELB, CDN) present | **FURTHER_OPTIMIZATION_AVAILABLE** (data curation) | Step 2 — switch to basic-event-selector with explicit bucket list |
| Lambda data events = `All Functions` AND > 1000 functions with > 80% low-audit-value | **FURTHER_OPTIMIZATION_AVAILABLE** (data curation) | Step 2 — curate function ARNs or disable Lambda data events |
| S3 log bucket lifecycle policy absent OR Standard-only beyond 90 days | **FURTHER_OPTIMIZATION_AVAILABLE** (lifecycle) | Step 3 — add Glacier Instant Retrieval @ 90d, Deep Archive @ 180d |
| CloudTrail Lake EDS ingesting > 50 GB/month of free-tier-redundant data | **FURTHER_OPTIMIZATION_AVAILABLE** (Lake) | Step 4 — add event-category filter, narrow EDS scope |
| CloudTrail publishing to both S3 AND CloudWatch Logs AND only S3 consumers exist | **FURTHER_OPTIMIZATION_AVAILABLE** (Logs) | Step 5 — disable CloudWatchLogsLogGroupArn |
| Each trail has its own KMS CMK AND > 3 trails in the org | **FURTHER_OPTIMIZATION_AVAILABLE** (KMS) | Step 6 — share one CMK across all trails |
| CloudTrail Insights enabled on ALL trails AND no anomalous findings in 90 days | **FURTHER_OPTIMIZATION_AVAILABLE** (Insights) | Step 6 — disable Insights on low-risk trails |
| Org trail + curated data events + Glacier lifecycle + single CMK + Lake sized for interactive queries only | **OPTIMIZED** | None — continue monitoring |
| Cost Explorer CloudTrail line absent or window < 30 days | **NEED_MORE_INFO** | Pull 30-90 day Cost Explorer, re-evaluate |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these signals before any recommendation. Full CLI sequences are in
`references/cloudtrail-pricing-and-inventory.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Trail configurations: `aws cloudtrail describe-trails`
2. Event selectors (data/management): `aws cloudtrail get-event-selectors`
3. Insights selectors: `aws cloudtrail get-insights-selectors`
4. Org structure: `aws organizations describe-organization`, `list-accounts`
5. S3 lifecycle policy on log bucket: `aws s3api get-bucket-lifecycle-configuration`
6. S3 bucket size (CloudTrail prefix): `aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name BucketSizeBytes`
7. CloudTrail Lake EDS config: `aws cloudtrail list-event-data-stores`
8. KMS key configuration: `aws kms describe-key`
9. Cost Explorer CloudTrail spend: `aws ce get-cost-and-usage` filtered by `Service=AWS CloudTrail`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-trails` returns empty `trailList` | **NEED_MORE_INFO**. CloudTrail may be disabled or IAM denies cloudtrail:DescribeTrails. |
| 30-day Cost Explorer window shows $0 CloudTrail spend | Trail may be in free tier; check data-event dimension separately. |
| S3 `BucketSizeBytes` metric absent for CloudTrail prefix | Bucket untagged or metrics not enabled. Fall back to S3 inventory report. |
| `get-event-selectors` returns `CloudTrail Insights not enabled` | Insights dimension is no-op; skip Step 6 Insights sub-check. |
| `list-event-data-stores` empty | CloudTrail Lake not configured; skip Step 4. |
| Observation window < 30 days | **NEED_MORE_INFO**. Minimum 30 days; 90 days preferred for seasonality. |
| Trail `Status != RUNNING` (logging suspended) | Skip optimization; surface as BLOCKED. Resume logging first. |

When Cost Explorer and CloudTrail metrics disagree, Cost Explorer is
authoritative for the dollar figure; CloudTrail metrics are authoritative
for event counts.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **The first management-event trail per region is free.** Additional
  management-event trails in the same region bill per-event. Org trail +
  one member trail in the same region is the #1 cost trap.
- **Org trail is automatically multi-region.** `IsMultiRegionTrail=true`
  is the default for org trails. Single-region org trails don't exist;
  any per-region trail duplicates at least the in-region events.
- **Data events bill per 100,000 events regardless of trail count.** Two
  trails each capturing S3 data events on the same bucket bill the
  events TWICE — there is no deduplication across trails.
- **S3 lifecycle affects all objects in the prefix.** A lifecycle rule
  on the CloudTrail prefix will also transition digest files (used for
  log file integrity validation). Deep Archive digest files take 12 hours
  to restore — verify your audit RTO first.
- **CloudTrail Lake ingestion is one-time per event.** Once an event is
  in an EDS, you pay only retention storage, not re-ingestion. But each
  EDS ingests independently — multiple EDSs on the same events double-
  ingest and double-charge.
- **CloudWatch Logs ingestion bills by bytes, not events.** A
  high-cardinality event stream (Lambda data events) ingested into
  CloudWatch Logs costs ~5x the same events in S3.
- **KMS request pricing is per-call.** Each CloudTrail log file triggers
  one GenerateDataKey call. At 1.4M log files/month (large org), that's
  ~$4.20/month — small but multiplied by N trails with N keys.
- **Insights bills per 100k management events analyzed, not per Insight
  finding.** An account with 500M management events/month pays $2,500 for
  Insights regardless of whether any anomalous pattern fires.
- **Requester Pays on the log bucket shifts cost to the reader.** Useful
  for cross-account audit access; harmful if the reader is another
  monitored account (double-counts your bill).
- **Athena full-table scans on CloudTrail logs are the #1 hidden cost.**
  Without partition projection, a single exploratory query scans all
  historical logs — potentially terabytes at $5/TB scanned.
- **Log file integrity validation doubles S3 PUT requests.** Each digest
  file is an extra S3 PUT. At scale, PUT fees alone justify keeping
  validation off when S3 Object Lock provides equivalent tamper-evidence.
- **EventBridge as a CloudTrail consumer bills per event published.**
  Routing management events to EventBridge re-bills them at $1.00/million
  — useful for real-time response but never free.

### Step 1: Trail consolidation (the #1 lever)

Trail consolidation is the primary cost lever because the per-trail
fixed costs (KMS, SNS, log file PUT fees) and the duplicate management-
event volume scale linearly with trail count.

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

For orgs with data events, the duplicate cost compounds because data
events are billed per trail per event — not deduplicated.

**Finding the consolidation opportunity: AWS Organizations.** Verify the
account is the org management account, then create the org trail before
deleting member trails.

**Decision gate after consolidation analysis:**

| Trail inventory | Verdict | Action |
|---|---|---|
| Org trail exists AND no member trails | No consolidation finding | Proceed to other dimensions. |
| Org trail exists AND member trails present | **FURTHER_OPTIMIZATION_AVAILABLE** | Delete member trails; org trail covers all member events. |
| No org trail AND > 1 trail across accounts | **FURTHER_OPTIMIZATION_AVAILABLE** | Create org trail, migrate consumers, delete member trails. |
| No org trail AND 1 trail per account (standard) | **FURTHER_OPTIMIZATION_AVAILABLE** | Convert to org trail (single creation in mgmt account). |
| Standalone account (not in org) | Skip Step 1 | No consolidation possible. |

**Org trail creation (one-time):**
```bash
aws cloudtrail create-trail \
  --name aws-organizational-trail \
  --s3-bucket-name org-cloudtrail-logs-us-east-1 \
  --is-organization-trail \
  --is-multi-region-trail \
  --kms-key-id alias/cloudtrail-org-cmk \
  --enable-log-file-validation
```

**Deletion of redundant member trails (after verifying consumers):**
```bash
aws cloudtrail delete-trail --name member-trail-us-east-1
```

### Step 2: Data event curation

Data events bill at $0.10 per 100,000 events regardless of how many
trails capture them. Curation reduces event volume without losing audit
coverage of high-value resources.

**Pricing comparison:**
```
Management events:  FREE (first trail per region)
S3 data events:     $0.10 per 100,000 events
Lambda data events: $0.10 per 100,000 events
DynamoDB data events: $0.10 per 100,000 events
```

**Decision tree:**
```
Is the trail capturing S3 data events on All Buckets?
├── NO → S3 data event check passes.
└── YES → Are > 20% of events from low-value buckets (logs, ELB,
           CDN, CloudTrail's own bucket)?
    ├── NO → S3 data events are justified.
    └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (curate bucket list)

Is the trail capturing Lambda data events on All Functions?
├── NO → Lambda data event check passes.
└── YES → Are > 50% of functions low-audit-value (cron jobs, internal
           health checks, dev-stage functions)?
    ├── NO → Lambda data events are justified.
    └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (curate or disable)
```

**Curating S3 data events with basic event selectors:**
```bash
aws cloudtrail put-event-selectors \
  --trail-name aws-organizational-trail \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::S3::Object",
      "Values": ["arn:aws:s3:::financial-records/", "arn:aws:s3:::pii-data/"]
    }]
  }]'
```

**Advanced event selectors for multi-resource-type curation:**
```bash
aws cloudtrail put-event-selectors \
  --trail-name aws-organizational-trail \
  --advanced-event-selectors '[
    {"Name": "ManagementEvents", "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Management"]}
    ]},
    {"Name": "S3AuditBuckets", "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Data"]},
      {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
      {"Field": "resources.ARN", "StartsWith": [
        "arn:aws:s3:::financial-records/",
        "arn:aws:s3:::pii-data/"
      ]}
    ]}
  ]'
```

**Data-event saving from curation:**
```
old_event_volume = sum(all_bucket_event_counts)
new_event_volume = sum(curated_bucket_event_counts)
monthly_saving = ((old_event_volume - new_event_volume) / 100000) × $0.10
```

Example: 142M S3 data events/month, 80% from log/CDN buckets. Curating
to high-value buckets drops volume to 28M events. Monthly saving:
((142M - 28M) / 100k) × $0.10 = $114/month on data event fees, plus
~600 GB/month saved S3 storage.

### Step 3: S3 lifecycle for log files

CloudTrail log files are write-once-read-rarely. Standard storage beyond
90 days is wasted spend; Glacier Instant Retrieval keeps millisecond
read latency at 19% of Standard cost.

**Storage class cost comparison (us-east-1, 2026):**
```
Standard:                   $0.023/GB-month
Glacier Instant Retrieval:  $0.004/GB-month  (83% cheaper, ms latency)
Glacier Flexible Retrieval: $0.0036/GB-month (1-5 min restore)
Deep Archive:               $0.00099/GB-month (12 hour restore)
```

**Recommended lifecycle policy:**
```json
{
  "Rules": [{
    "Id": "cloudtrail-lifecycle",
    "Status": "Enabled",
    "Filter": {"Prefix": "AWSLogs/"},
    "Transitions": [
      {"Days": 30, "StorageClass": "INTELLIGENT_TIERING"},
      {"Days": 90, "StorageClass": "GLACIER_IR"},
      {"Days": 180, "StorageClass": "DEEP_ARCHIVE"}
    ],
    "Expiration": {"Days": 365}
  }]
}
```

**Apply via AWS CLI:**
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket org-cloudtrail-logs-us-east-1 \
  --lifecycle-configuration file://cloudtrail-lifecycle.json
```

**Storage saving math:**
```
monthly_storage_cost = sum(log_size_GB_at_storage_class × class_rate)

Example: 500 GB CloudTrail logs at Standard = $11.50/month
         With lifecycle:
           - First 30 days @ Standard:        $11.50 × (30/365) × 500 = $0.47
           - Days 31-90 @ IntelligentTiering: ~$11.50 × (60/365) × 500 = $0.94
           - Days 91-180 @ Glacier IR:        $2.00 × (90/365) × 500 = $0.25
           - Days 181-365 @ Deep Archive:     $0.50 × (185/365) × 500 = $0.13
         Steady-state annual: $1.79 vs $138.00 = 98.7% saving
```

### Step 4: CloudTrail Lake event data store cost

CloudTrail Lake charges $0.75/GB-month ingestion (one-time) plus
retention storage at S3 Standard rates. Use Lake only when interactive
SQL queries on audit data are required.

**Pricing model:**
```
Ingestion:        $0.75/GB-month (billed once at ingest time)
Retention storage: $0.023/GB-month (Standard rate, included with EDS)
Query:            Free (Athena-style federation to EDS)
```

**Decision tree:**
```
Is the EDS ingesting all event categories (management + data + insight)?
├── NO → EDS scope is curated; check ingestion GB.
└── YES → Are data events needed for the EDS use case?
    ├── NO → **FURTHER_OPTIMIZATION_AVAILABLE** (filter to management)
    └── YES → Can high-volume low-value sources be excluded?
        ├── NO → EDS is justified.
        └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (narrow EDS scope)
```

**EDS configuration with event-category filter:**
```bash
aws cloudtrail update-event-data-store \
  --event-data-store <eds-id> \
  --advanced-event-selectors '[
    {"Name": "ManagementOnly", "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Management"]}
    ]}
  ]'
```

**Lake cost math:**
```
monthly_ingestion_cost = monthly_ingested_GB × $0.75
monthly_retention_cost = cumulative_EDS_GB × $0.023

Example: 100 GB/month ingest, 90-day retention:
  Ingestion: 100 × $0.75 = $75/month
  Retention: 300 GB (90d × 100/30) × $0.023 = $6.90/month
  Total: $81.90/month

If management-only filter cuts ingest 90%: 10 GB/month
  Ingestion: 10 × $0.75 = $7.50/month
  Retention: 30 GB × $0.023 = $0.69/month
  Total: $8.19/month
  Saving: $73.71/month (90%)
```

### Step 5: CloudWatch Logs delivery cost

CloudTrail can publish to both S3 and CloudWatch Logs. Logs ingestion
bills by bytes at $0.50/GB — typically 5x more expensive than S3 for
the same events.

**Decision tree:**
```
Is CloudTrail publishing to CloudWatch Logs?
├── NO → Logs check passes.
└── YES → Are there CloudWatch Logs consumers (metric filters, alarms,
           Logs Insights queries)?
    ├── YES → Are they high-value enough to justify 5x storage cost?
    │        ├── YES → Keep Logs delivery.
    │        └── NO → **FURTHER_OPTIMIZATION_AVAILABLE** (migrate to Athena-on-S3)
    └── NO → **FURTHER_OPTIMIZATION_AVAILABLE** (disable Logs delivery)
```

**Disabling CloudWatch Logs delivery:**
```bash
aws cloudtrail update-trail \
  --name aws-organizational-trail \
  --no-cloud-watch-logs-log-group-arn
```

**Logs delivery cost math:**
```
monthly_logs_cost = monthly_ingested_GB × $0.50
                 + monthly_storage_GB × $0.03 (Standard)

Example: 100 GB/month ingest = $50/month in Logs alone
         Equivalent S3 storage: 100 GB × $0.023 = $2.30/month
         Saving from disabling Logs: $47.70/month (95%)
```

### Step 6: KMS, SNS, and Insights tuning

These per-trial overheads are individually small but multiply across
trail count.

**KMS key consolidation:**
```
Per-key monthly cost: $1.00 (CMK) + ~$0.50/request fees
Per-trail-with-own-key overhead: $1.50/month × trail_count

Recommendation: Share one CMK across all trails when key policy allows.
```

**KMS policy snippet allowing CloudTrail service to use a shared key:**
```json
{
  "Sid": "AllowCloudTrailToUseKey",
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": ["kms:GenerateDataKey*", "kms:DescribeKey"],
  "Resource": "*",
  "Condition": {
    "StringLike": {
      "kms:ViaService": "s3.us-east-1.amazonaws.com"
    },
    "StringEquals": {
      "aws:SourceArn": "arn:aws:cloudtrail:us-east-1:MANAGEMENT_ACCT:trail/*"
    }
  }
}
```

**SNS consolidation:**
- Each trail can notify one SNS topic. Multiple trails in one account
  can share a topic. SNS charges $0.50 per million publishes.
- Recommendation: consolidate all trails in an account to a single SNS
  topic with a Lambda filter for high-severity events only.

**Insights gating:**
```
Insights cost: $0.50 per 100,000 management events analyzed
Example: 500M management events/month = $2,500/month

Recommendation: Enable Insights only on:
  - The org-management account (always)
  - Member accounts with privileged role assumption activity
  - Member accounts with prior anomalous findings
```

**Disabling Insights on low-risk trails:**
```bash
aws cloudtrail stop-insights-logging --name aws-organizational-trail
```

### Step 7: Athena partition projection for cost analysis

Athena queries on CloudTrail logs without partition projection scan the
entire historical log set — potentially terabytes at $5/TB scanned.

**Partition projection table DDL:**
```sql
CREATE EXTERNAL TABLE cloudtrail_logs (
  eventversion STRING,
  useridentity STRUCT<
    type: STRING,
    principalid: STRING,
    arn: STRING,
    accountid: STRING,
    accesskeyid: STRING,
    sessioncontext: STRUCT<
      attributes: STRUCT<
        mfaauthenticated: STRING,
        creationdate: STRING
      >,
      sessionissuer: STRUCT<
        type: STRING,
        principalid: STRING,
        arn: STRING,
        accountid: STRING
      >
    >
  >,
  eventtime STRING,
  eventsource STRING,
  eventname STRING,
  awsregion STRING,
  sourceipaddress STRING,
  useragent STRING,
  errorcode STRING,
  errormessage STRING,
  requestparameters STRING,
  responseelements STRING,
  additionaleventdata STRING,
  requestid STRING,
  eventid STRING,
  resources ARRAY<STRUCT<arn: STRING, accountid: STRING, type: STRING>>,
  eventtype STRING,
  apiversion STRING,
  readonly STRING,
  recipientaccountid STRING,
  serviceeventdetails STRING,
  sharedeventid STRING
)
PARTITIONED BY (
  accountid_hive STRING,
  region_hive STRING,
  year_hive STRING,
  month_hive STRING,
  day_hive STRING
)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://org-cloudtrail-logs-us-east-1/AWSLogs/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.accountid_hive.type' = 'enum',
  'projection.accountid_hive.values' = '111111111111,222222222222',
  'projection.region_hive.type' = 'enum',
  'projection.region_hive.values' = 'us-east-1,us-west-2,eu-west-1',
  'projection.year_hive.type' = 'date',
  'projection.year_hive.range' = '2024-01-01,NOW',
  'projection.year_hive.format' = 'yyyy',
  'projection.month_hive.type' = 'date',
  'projection.month_hive.range' = '2024-01-01,NOW',
  'projection.month_hive.format' = 'MM',
  'projection.day_hive.type' = 'date',
  'projection.day_hive.range' = '2024-01-01,NOW',
  'projection.day_hive.format' = 'dd',
  'storage.location.template' = 's3://org-cloudtrail-logs-us-east-1/AWSLogs/${accountid_hive}/CloudTrail/${region_hive}/${year_hive}/${month_hive}/${day_hive}'
);
```

**Query cost reduction:**
- Without partition projection: a single exploratory query scans ALL
  historical logs (potentially TB-scale at $5/TB).
- With partition projection: partition pruning is computed client-side
  (no Glue Data Catalog partitions needed); only the matching partitions
  are scanned.

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (data_events / 100000 × $0.10) +
  (s3_storage_GB × $0.023) +
  (lake_ingestion_GB × $0.75) +
  (logs_ingestion_GB × $0.50) +
  (insights_events / 100000 × $0.50) +
  (kms_keys × $1.50) +
  (sns_notifications / 1000000 × $0.50)

projected_monthly_cost = <recompute each term after changes>

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: data event volume, S3 storage size, Lake
ingestion rate, Logs ingestion rate, Insights event volume, KMS key
count, SNS topic count, pricing region.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND org trail + curated data events + lifecycle +
  single CMK + Lake scoped to interactive queries → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (trail inventory absent, window < 30 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

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

Full worked examples (org-trail consolidation, data-event curation, S3
lifecycle rollout, CloudTrail Lake scoping, already-optimized, end-to-
end walkthrough) are in `references/cloudtrail-worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <trail-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <trail inventory + data events + storage class + Lake + Logs>
  Proposed: <consolidated inventory + curated events + Glacier + Lake scope>
  Dimensions changed: <consolidation | data_events | lifecycle | lake | logs | kms_sns_insights | athena>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show subtotals per cost term
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`. A cost-neutral compliance
   improvement is surfaced in REASON, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend org trail consolidation without verifying the
   account is the org management account.** Creating an org trail from
   a member account fails. Surface this as a prerequisite.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend disabling log file integrity validation without
   confirming S3 Object Lock provides equivalent tamper-evidence.**
   Disabling validation halves digest PUT cost but loses the audit
   attestation if Object Lock isn't enforced.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: aws-organizational-trail
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Organization trail capturing S3 data events on All Buckets
  includes 113M events/month from log and CDN buckets (80% of total)
  that have no audit value. S3 log bucket has no lifecycle policy,
  retaining 500 GB in Standard at $0.023/GB. Combined curation +
  lifecycle drops monthly CloudTrail spend 62%.
RECOMMENDATION:
  Current: org trail + All-Buckets S3 data events + Standard storage + no Lake
  Proposed: org trail + curated S3 data events (8 high-value buckets) + Glacier IR @ 90d
  Dimensions changed: data_events (Step 2) + lifecycle (Step 3)
  Dimensions checked: consolidation ✓ (org trail exists)  data_events → (curate)
    lifecycle → (no policy)  lake ✓ (not configured)  logs ✓ (S3-only)
    kms_sns_insights ✓ (shared CMK, no Insights)  athena ✓ (partition projection)
  Confidence: HIGH — S3 metrics confirm 113M/142M events are low-value
    bucket writes; lifecycle math is deterministic; us-east-1 pricing.
ESTIMATED_SAVINGS:
  Current monthly: $1,847.32
    data_events: 142,000,000 / 100,000 × $0.10 = $142.00
    s3_storage: 500 GB × $0.023 = $11.50
    kms_keys: 1 × $1.50 = $1.50
    sns_notifications: 1.4M / 1M × $0.50 = $0.70
    insights_events: 0 (not enabled)
    logs_ingestion: 0 (S3-only)
    lake_ingestion: 0 (not configured)
    athena_scans: 1,692.62 (estimated query volume at $5/TB)
  Projected monthly: $697.32
    data_events: 29,000,000 / 100,000 × $0.10 = $29.00 (curated)
    s3_storage: $1.79 (Glacier IR + Deep Archive lifecycle)
    kms_keys: $1.50 (unchanged)
    sns_notifications: $0.30 (fewer files)
    insights_events: $0
    logs_ingestion: $0
    lake_ingestion: $0
    athena_scans: $664.73 (partition projection reduces 60%)
  Monthly saving: $1,150.00
    ($1,847.32 − $697.32 = $1,150.00 ✓)
  Annual saving: $13,800.00
MIGRATION_STEPS:
  1. Apply advanced event selectors with curated bucket list:
     aws cloudtrail put-event-selectors --trail-name aws-organizational-trail \
       --advanced-event-selectors file://curated-selectors.json
  2. Apply S3 lifecycle policy to the log bucket:
     aws s3api put-bucket-lifecycle-configuration \
       --bucket org-cloudtrail-logs-us-east-1 \
       --lifecycle-configuration file://cloudtrail-lifecycle.json
  3. Verify lifecycle policy took effect (no immediate object transitions):
     aws s3api get-bucket-lifecycle-configuration \
       --bucket org-cloudtrail-logs-us-east-1
  4. After 30 days, query S3 storage metrics to confirm Intelligent
     Tiering is taking effect.
CONFIRM: About to put-event-selectors on aws-organizational-trail
  (All Buckets → 8 high-value buckets) and apply S3 lifecycle to
  org-cloudtrail-logs-us-east-1. Monthly saving $1,150.00 (62%).
  Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | Either (a) all dimensions pass (org trail + curated data events + lifecycle + single CMK + Lake scoped), OR (b) a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: trail inventory absent, Cost Explorer window < 30 days, or S3 metrics unavailable. |
| `BLOCKED` | Hard precondition prevents evaluation: trail Status != RUNNING (logging suspended), IAM denies cloudtrail:DescribeTrails. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a compliance improvement without cost change is surfaced in
REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend org trail consolidation without verifying the
   account is the org management account.** Member accounts cannot
   create org trails; the API call fails. Surface this prerequisite.

2. **NEVER recommend disabling management events to reduce cost.**
   Management events are free on the first trail per region. Disabling
   them breaks audit completeness for ~zero savings.

3. **NEVER recommend Deep Archive transition without confirming the
   audit RTO tolerates 12-hour restore.** For incident-response use
   cases, Glacier Instant Retrieval (ms-latency) is the right choice.

4. **NEVER recommend curating data events to specific buckets without
   confirming the bucket list is complete.** Missing a high-value
   bucket from the selector creates a silent audit blind spot.

5. **NEVER recommend disabling CloudWatch Logs delivery without
   auditing for existing metric filters, alarms, or Logs Insights
   queries on the log group.** Disabling breaks downstream monitoring
   silently.

Extended anti-patterns in `references/cloudtrail-worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Verify org trail coverage before deleting member trails.** Org trail
  must be RUNNING and capturing all member-account events before any
  member trail deletion.
- **Snapshot existing event selectors before curating.** Restore is a
  re-apply of the prior selector JSON.
- **Test lifecycle policy on a single prefix first.** Apply to
  `AWSLogs/<one-account>/` before org-wide rollout.
- **Confirm S3 Object Lock is enforced before disabling log file
  integrity validation.** Object Lock provides equivalent tamper-evidence.
- **CloudTrail Lake EDS changes are immediate.** Stopping ingestion
  stops queries; export historical data first if needed.
- **KMS key changes require updating the trail's KMS key policy.**
  Sharing a CMK requires the policy to allow all trail-writing accounts.
- **Insights disabling is irreversible for historical data.** Anomalies
  in the disabled window will not be retroactively detected.
- **Bulk-operation limit:** Process at most 5 trails per batch. Sort by
  estimated savings, verify each batch before proceeding. Abort if any
  trail shows event ingestion drop post-change.

## Recent AWS features (2024-2026)

- **CloudTrail Lake federated queries (2024-2025):** Run Athena-style
  SQL across multiple EDSs. Enables cross-account audit queries without
  S3 export.
- **CloudTrail Lake event-category filtering (2024):** EDS can filter
  by event category (Management, Data, Insights) at ingest time,
  reducing cost.
- **CloudTrail advanced event selectors (2024 GA):** Field-level
  filtering for data events (e.g., readOnly, resources.type). Enables
  granular curation.
- **S3 Glacier Instant Retrieval (mature 2024-2025):** ms-latency
  access at 19% of Standard cost. The default recommendation for
  CloudTrail logs after 90 days.
- **S3 Lifecycle with Object Lock (2024):** Object Lock + lifecycle can
  coexist, enabling tamper-evident archive without log file integrity
  validation overhead.
- **CloudTrail Insights for data events (2024-2025):** Insights
  coverage extended to data event anomalies (e.g., unusual S3 GET
  volume). Bills per data event analyzed — high-cost, opt-in carefully.
- **Athena partition projection (mature):** Client-side partition
  pruning without Glue Data Catalog partitions. Standard for CloudTrail
  log analytics.
- **CloudTrail Organizations integration (2024-2025 enhancements):**
  Org trail now supports delegated administrator for CloudTrail Lake,
  isolating audit ops from the org management account.

## References

- `references/cloudtrail-pricing-and-inventory.md` — pricing tables,
  trail inventory CLI, event selector syntax, KMS key policy templates,
  S3 lifecycle JSON, Athena partition projection DDL, regional pricing
  multipliers, cost calculation worked examples.
- `references/cloudtrail-worked-examples.md` — full worked examples
  (org-trail consolidation, data-event curation, S3 lifecycle rollout,
  CloudTrail Lake scoping, already-optimized, end-to-end walkthrough,
  extended NEVER list, edge cases).

## Domain

AWS CloudOps / Governance Audit Logging Cost Optimization & FinOps.

## AWS documentation

- **AWS CloudTrail User Guide** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html
- **AWS CloudTrail pricing** — https://aws.amazon.com/cloudtrail/pricing/
- **CloudTrail organizational trails** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- **CloudTrail event selectors** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **CloudTrail Insights** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-insights-events-with-cloudtrail.html
- **S3 lifecycle configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **S3 Glacier Instant Retrieval** — https://aws.amazon.com/s3/storage-classes/glacier/instant-retrieval/
- **Athena partition projection** — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
- **AWS KMS pricing** — https://aws.amazon.com/kms/pricing/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
