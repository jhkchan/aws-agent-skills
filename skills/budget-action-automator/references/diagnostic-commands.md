# Diagnostic Commands (load on demand) — Budget Action Automator

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Step 12 — Cost allocation tag activation check (moved from SKILL.md)

Cost allocation tags MUST be activated before any tag-scoped budget
works:

```bash
# Check activated tags
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=env
```

If the result returns no rows or only `$NULL`, the tag is not
activated. Activate:

```bash
aws ce update-cost-allocation-tags-status \
  --tag-keys env team project \
  --status Active
```

Activation takes up to 24 hours to take effect, and historical data
is NOT backfilled — only future spend is matched.
