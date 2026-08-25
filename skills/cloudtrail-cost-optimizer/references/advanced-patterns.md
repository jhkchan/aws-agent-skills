# Advanced patterns — CloudTrail Cost Optimizer

Expert knowledge, per-step rationale, and recent-feature notes moved out of
SKILL.md for progressive disclosure. Load on demand.

## Quick start — headline rules 1, 3, 4 (moved from SKILL.md)

- **Org trail consolidation is the #1 lever.** A single organization
  trail captures every member-account event across every region. N
  member-account trails each capture (and store, and KMS-encrypt, and
  SNS-notify) the SAME management events for the org's primary account,
  causing pure duplicate volume that scales linearly with account count.
  Replacing 10 member trails with 1 org trail removes ~90% of management-
  event log volume for the org-management account.
- **Data events are 10x costlier than management events.** Management
  events are free on the first trail per region; data events (S3, Lambda,
  DynamoDB, etc.) bill at $0.10 per 100,000 events. Always curate data
  event sources to high-value buckets/functions only.
- **S3 lifecycle is a one-click ~80% cut.** CloudTrail log files are
  write-once-read-rarely. Transition to Glacier Instant Retrieval after
  90 days and Deep Archive after 180 days for ~80% storage cost reduction
  without losing audit-query ability.

## Mindset — governance vs spend and the four principles (moved from SKILL.md)

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

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **The first management-event trail per region is free.** Additional
  management-event trails in the same region bill per-event. Org trail +
  one member trail in the same region is the #1 cost trap.
- **Org trail is automatically multi-region.** Single-region org trails
  don't exist; any per-region trail duplicates at least the in-region
  events.
- **Data events bill per 100,000 events regardless of trail count.** Two
  trails each capturing S3 data events on the same bucket bill the
  events TWICE — no deduplication across trails.
- **S3 lifecycle affects all objects in the prefix.** A rule on the
  CloudTrail prefix also transitions digest files. Deep Archive digest
  files take 12 hours to restore — verify your audit RTO first.
- **CloudTrail Lake ingestion is one-time per event.** Each EDS ingests
  independently; multiple EDSs on the same events double-ingest and
  double-charge.
- **CloudWatch Logs ingestion bills by bytes, not events.** Lambda data
  events ingested into Logs costs ~5x the same events in S3.
- **KMS request pricing is per-call.** Each log file triggers one
  GenerateDataKey. At 1.4M files/month (large org), ~$4.20/month — small
  but multiplied by N trails with N keys.
- **Insights bills per 100k management events analyzed, not per finding.**
  An account with 500M management events/month pays $2,500 regardless of
  whether any anomalous pattern fires.
- **Requester Pays on the log bucket shifts cost to the reader.** Useful
  for cross-account audit access; harmful if the reader is another
  monitored account (double-counts your bill).
- **Athena full-table scans on CloudTrail logs are the #1 hidden cost.**
  Without partition projection, a single exploratory query scans all
  historical logs — potentially terabytes at $5/TB scanned.
- **Log file integrity validation doubles S3 PUT requests.** Each digest
  is an extra PUT. At scale, PUT fees alone justify disabling validation
  when S3 Object Lock (COMPLIANCE mode) provides equivalent tamper-
  evidence.
- **EventBridge as a CloudTrail consumer bills per event published**
  ($1.00/million) — useful for real-time response but never free.

## Step 1 — consolidation rationale (moved from SKILL.md)

Trail consolidation is the primary cost lever because the per-trail
fixed costs (KMS, SNS, log file PUT fees) and the duplicate management-
event volume scale linearly with trail count.

For orgs with data events, the duplicate cost compounds because data
events are billed per trail per event — not deduplicated.

**Finding the consolidation opportunity: AWS Organizations.** Verify the
account is the org management account, then create the org trail before
deleting member trails.

## Step 6 — SNS consolidation and Insights gating (moved from SKILL.md)

**SNS consolidation:**
- Each trail can notify one SNS topic. Multiple trails in one account
  can share a topic. SNS charges $0.50 per million publishes.
- Recommendation: consolidate all trails in an account to a single SNS
  topic with a Lambda filter for high-severity events only.

**Insights gating:** Insights bills $0.50 per 100k management events
analyzed. For 500M events/month that's $2,500/month regardless of
whether any anomalous pattern fires. Enable Insights only on the org-
management account (always) and member accounts with privileged role
assumption activity or prior anomalous findings.

## Step 7 — Athena partition projection for cost analysis (moved from SKILL.md)

Athena queries on CloudTrail logs without partition projection scan the
entire historical log set — potentially terabytes at $5/TB scanned.
Partition projection moves pruning client-side: only the matching
account/region/date partitions are scanned, no Glue Data Catalog
partitions needed. The full DDL and storage location template are in
`references/cloudtrail-pricing-and-inventory.md`.

**Query cost reduction (us-east-1 example):**
```
Without projection:  exploratory query scans 2 TB     @ $5/TB    = $10.00
With projection:     same query scans 3 matching days @ $5/TB    = $0.04
Saving per query:    $9.96 (99.6% per exploratory query)
```

Apply the partition projection table DDL once per Athena workgroup;
all subsequent queries on `cloudtrail_logs` inherit the projection.

## Recent AWS features (2024-2026, moved from SKILL.md)

- **CloudTrail Lake enhancements (2024-2025):** federated queries across
  EDSs; event-category filtering at ingest time; delegated administrator
  isolates audit ops from org management account.
- **CloudTrail advanced event selectors (2024 GA):** field-level
  filtering (readOnly, resources.type, resources.ARN prefix matching)
  enables granular data-event curation.
- **S3 Glacier Instant Retrieval (mature 2024-2025):** ms-latency
  access at 19% of Standard cost; default recommendation for CloudTrail
  logs after 90 days. Object Lock + lifecycle coexist for tamper-evident
  archive without log file integrity validation overhead.
- **CloudTrail Insights for data events (2024-2025):** coverage extended
  to data event anomalies; bills per data event analyzed — opt in
  carefully. Athena partition projection is now standard for CloudTrail
  log analytics.
