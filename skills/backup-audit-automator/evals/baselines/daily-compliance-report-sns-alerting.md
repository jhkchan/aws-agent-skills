# Baseline (no-skill) — daily-compliance-report-sns-alerting

> This is the response a model produces **without** the skill
> definition. It lists some CLI commands but misses the three report
> template types, the S3 bucket policy for backup delivery, the
> framework mapping, and the AUTOMATION_DEPLOYED checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create a backup report plan:

```bash
aws backup create-report-plan --report-plan-name "daily-report"
```

That should cover compliance.
