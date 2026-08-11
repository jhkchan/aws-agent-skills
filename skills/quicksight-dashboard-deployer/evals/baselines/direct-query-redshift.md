# Baseline (no-skill) — direct-query-redshift

> This is the response a model produces **without** the skill
> definition. It uses Direct Query but misses the explicit SPICE vs
> Direct Query decision (Redshift is an analytical store so Direct
> Query is acceptable), the refresh-schedule-not-applicable note, the
> user provisioning step for sharing, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

To create a QuickSight dashboard with Redshift:

1. Connect to your Redshift cluster.
2. Use Direct Query for real-time data.
3. Build visuals and publish.

```bash
aws quicksight create-data-source --type REDSHIFT
aws quicksight create-dashboard --name "exec-dashboard"
```

Share with readers via the console.
