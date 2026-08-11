# Baseline (no-skill) — partial-asdd-only-coverage-gap

> This is the response a model produces **without** the skill
> definition. It notes some issues (no scheduled jobs, Security Hub
> disabled) but misses the critical coverage gap calculation (35
> unmonitored buckets), the custom identifier regex risk assessment
> (\d{1,19} as catastrophic false-positive generator), the ASDD-
> vs-job-scope deep-scan gap (7/12 high-sensitivity buckets on
> sampling only), and the PARTIALLY_CLASSIFIED verdict format.
> Generated for with-skill-vs-baseline comparison.

---

Macie is enabled but there are some gaps. There are only one-time
jobs, no scheduled jobs, so coverage is not ongoing. Security Hub
export is disabled so findings may not reach the SOC team. The
custom identifier regex looks broad. You should enable Security
Hub export and create scheduled jobs.

```bash
aws macie2 get-macie-session --region us-east-1
aws macie2 list-classification-jobs --region us-east-1
```
