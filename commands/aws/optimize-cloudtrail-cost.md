---
description: Optimise CloudTrail spend through trail consolidation (single org trail replaces N member trails), data-event curation (curate high-volume S3/Lambda data event sources), S3 lifecycle (Glacier Instant Retrieval at 90 days), CloudTrail Lake event-data-store scoping, CloudWatch Logs delivery elimination, KMS/SNS/Insights consolidation, and Athena partition projection — with monthly savings estimates.
nl_triggers:
  - "optimise CloudTrail cost"
  - "CloudTrail trail consolidation"
  - "CloudTrail org trail vs member trail"
  - "CloudTrail data event volume"
  - "CloudTrail S3 lifecycle"
  - "CloudTrail log file Glacier transition"
  - "CloudTrail Lake event data store cost"
  - "CloudTrail CloudWatch Logs delivery cost"
  - "CloudTrail KMS key per trail"
  - "CloudTrail Insights event cost"
  - "CloudTrail log file integrity validation"
  - "CloudTrail SNS notification cost"
  - "CloudTrail organizational trail deduplication"
  - "CloudTrail Athena partition projection"
  - "CloudTrail FinOps savings"
  - "CloudTrail monthly savings estimate"
  - "reduce CloudTrail bill"
  - "governance cost review"
  - "CloudTrail duplicate events"
routes_to: cloudtrail-cost-optimizer
---

# /aws:optimize-cloudtrail-cost

Activate the `cloudtrail-cost-optimizer` skill and optimize a
CloudTrail configuration's cost across seven dimensions: trail
consolidation, data-event curation, S3 lifecycle, CloudTrail Lake,
CloudWatch Logs delivery, KMS/SNS/Insights, and Athena partition
projection.

## What it does

Reads a trail's configuration, event selectors, Insights selectors,
S3 lifecycle policy, CloudTrail Lake EDS inventory, KMS key policy,
and Cost Explorer CloudTrail line, then applies the ordered optimization
logic:

1. **Pre-flight** — data sufficiency gate. If trail inventory or Cost
   Explorer data is absent, emits NEED_MORE_INFO. If the trail Status
   is not RUNNING, emits BLOCKED.
2. **Trail consolidation** — verify org trail exists and is RUNNING.
   Recommend deletion of redundant member trails after verifying org-
   trail coverage of all member-account events.
3. **Data event curation** — classify S3/Lambda data event sources by
   audit value. Recommend curating All-Buckets selectors to high-value
   bucket lists.
4. **S3 lifecycle** — add Glacier Instant Retrieval transition at 90
   days, Deep Archive at 180 days, expiration at the compliance SLA.
5. **CloudTrail Lake** — audit EDS scope against use case. Apply
   event-category filters to narrow ingestion.
6. **CloudWatch Logs delivery** — eliminate dual-publishing when only
   S3 consumers exist.
7. **KMS / SNS / Insights** — consolidate per-trail CMKs to a shared
   CMK; consolidate SNS topics; gate Insights to high-risk accounts.
8. **Athena partition projection** — apply partition projection table
   DDL to prevent full-table scans of CloudTrail logs.
9. **Impact estimation** — monthly + annual savings, assumptions
   documented.
10. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
    recommendation), OPTIMIZED (applied and verified this session, or
    all dimensions pass), or NEED_MORE_INFO.

Emits a deterministic optimization block per trail:

```text
TARGET: <trail-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <trail inventory + data events + storage class + Lake + Logs>
  Proposed: <consolidated inventory + curated events + Glacier + Lake scope>
  Dimensions changed: <consolidation | data_events | lifecycle | lake | logs | kms_sns_insights | athena>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a CloudTrail configuration and ask any of:

- "optimise this CloudTrail setup for cost"
- "should we consolidate these trails into an org trail?"
- "are these member trails duplicating events?"
- "should we curate S3 data events to specific buckets?"
- "should we add a lifecycle policy to our CloudTrail log bucket?"
- "is our CloudTrail Lake ingestion cost justified?"
- "should we disable CloudTrail Insights on low-risk accounts?"
- "CloudTrail fleet cost optimization review"

A bare trail name + any optimization verb ("optimize this trail",
"cost review") also routes here via the orchestrator.

## Inputs

- Trail metadata: name, IsOrganizationTrail, IsMultiRegionTrail,
  IncludeManagementEvents, Status, region.
- Event selectors (basic or advanced): management events, S3 data
  events, Lambda data events, DynamoDB data events.
- Insights selectors: enabled categories (ApiCallRateInsight,
  ApiCallErrorInsight).
- CloudTrail Lake EDS inventory: name, ID, retention, monthly
  ingestion, event categories ingested.
- S3 log bucket: name, lifecycle policy, Object Lock configuration,
  storage size breakdown by storage class.
- KMS key configuration: key ID, key policy, rotation status.
- Cost Explorer CloudTrail line (last 30-90 days).
- Organization context: management account, member account count.
- Optional: workload context (compliance retention SLA, data
  residency requirements, audit RTO).

## Outputs

- One optimization block per trail (or per account for consolidation
  cases).
- Confidence level with rationale (HIGH requires verified org-trail
  coverage + deterministic math + clear thresholds).
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (delete-trail,
  put-event-selectors, put-bucket-lifecycle-configuration,
  update-event-data-store, update-trail, stop-insights-logging).
- Snapshot-before-delete safety workflow (never delete a trail
  without `describe-trails` output saved).
- Verification cadence (24-hour lookup-events test, 7-day Cost
  Explorer re-query, 30-day S3 storage metrics check).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for governance audit-logging cost).
- `/aws:audit-cloudtrail-org-trail` to verify org-trail coverage
  before consolidation (the prerequisite check).
- `/aws:troubleshoot-cloudtrail-missing-events` for functional
  debugging (events absent from logs — not cost optimization).
- `/aws:operate-cloudtrail-lake` for CloudTrail Lake query authoring
  (not cost optimization).
