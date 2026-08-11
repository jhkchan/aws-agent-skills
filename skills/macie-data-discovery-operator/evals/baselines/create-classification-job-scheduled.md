# Baseline (no-skill) — create-classification-job-scheduled

> This is the response a model produces **without** the skill definition.
> It misses the Macie-enabled pre-check, the RECOMMENDED selector
> rationale, the SCHEDULED job-type requirement, the finding publish
> frequency context, and the VERDICT/PRE_CHECKS output contract.
> Generated for with-skill-vs-baseline comparison.

---

To create a Macie classification job:

```bash
aws macie2 create-classification-job \
  --name daily-pii-scan \
  --job-type SCHEDULED \
  --s3-job-definition bucketDefinitions='[{buckets=[prod-data-bucket,financial-records]}]' \
  --managed-data-identifier-selector ALL
```

Set it to run daily and you should be good.
