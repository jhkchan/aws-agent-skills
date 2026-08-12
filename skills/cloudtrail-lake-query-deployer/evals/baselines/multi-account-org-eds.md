# Baseline (no-skill) — multi-account-org-eds

> This is the response a model produces **without** the skill
> definition. It does not address the Organization-level ingestion
> flag, misses the multi-account query patterns, and does not emit the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the EDS:

```bash
aws cloudtrail create-event-data-store --name "org-mgmt-eds"
```

It should cover your accounts.
