# Baseline (no-skill) — data-events-eds-with-selectors

> This is the response a model produces **without** the skill
> definition. It creates the EDS but does not configure advanced event
> selectors (ingesting ALL S3 data events = huge cost), misses the
> event type immutability, and does not emit the READY_TO_DEPLOY
> checklist. Generated for with-skill-vs-baseline comparison.

---

Create the EDS:

```bash
aws cloudtrail create-event-data-store --name "s3-audit-eds"
```

Add S3 data events to it.
