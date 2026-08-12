# Baseline (no-skill) response: cloudtrail-lake-scoping

This file captures what a generic assistant produces WITHOUT the
cloudtrail-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, event-category filter CLI,
ingestion-vs-retention cost breakdown, EDS export safety step).

---

Your CloudTrail Lake event data store is ingesting 100 GB per month of
both management and data events, but you only need management events
for IAM access analysis. Since data events are 92% of your ingestion,
filtering them out should save a lot.

Your current ingestion cost is about $75/month (100 GB × $0.75) plus
retention storage. Filtering to management-only would drop ingestion to
8 GB/month, saving around $69/month on ingestion alone.

You can update your event data store with an event-category filter:

```
aws cloudtrail update-event-data-store \
  --event-data-store 7a7b8c9d-0e1f-2345-6789-0123456789ab \
  --advanced-event-selectors '[...]'
```
