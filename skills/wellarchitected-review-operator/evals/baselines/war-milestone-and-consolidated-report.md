# Baseline (no-skill) response: war-milestone-and-consolidated-report

This file captures what a generic assistant produces WITHOUT the
wellarchitected-review-operator skill loaded.

---

To create a milestone and generate a report, you can use:

```
aws wellarchitected create-milestone \
  --workload-id workload-abc123 \
  --milestone-name 2026-Q3-baseline
```

Then for the report:

```
aws wellarchitected get-consolidated-report \
  --workload-id workload-abc123
```

That should produce the report. You may need to specify the
format if you want PDF.
