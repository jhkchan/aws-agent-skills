# Baseline (no-skill) — multi-account-organizations-report

> This is the response a model produces **without** the skill
> definition. It does not address multi-account coverage via
> Organizations, misses the ALL_ACCOUNTS_IN_ORG setting, and does not
> emit the AUTOMATION_DEPLOYED checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create a report plan:

```bash
aws backup create-report-plan --report-plan-name "org-report"
```

It should cover your accounts.
