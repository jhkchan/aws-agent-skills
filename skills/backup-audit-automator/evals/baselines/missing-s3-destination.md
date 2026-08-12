# Baseline (no-skill) — missing-s3-destination

> This is the response a model produces **without** the skill
> definition. It creates the report plan without flagging the missing
> S3 destination as a prerequisite failure. Reports would not be
> delivered. Does not emit a REVIEW_REQUIRED verdict. Generated for
> with-skill-vs-baseline comparison.

---

Create the report plan:

```bash
aws backup create-report-plan --report-plan-name "pending-report"
```

You can add the S3 bucket later.
