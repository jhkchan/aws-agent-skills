# Baseline (no-skill) — mgmt-eds-with-data-protection

> This is the response a model produces **without** the skill
> definition. It creates the EDS but misses the data protection policy
> (PII masking), the per-GB billing model, the cloudtrail-data API
> distinction, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the EDS:

```bash
aws cloudtrail create-event-data-store --name "mgmt-events-eds"
```

You can query it later with Athena.
