# Baseline (no-skill) — macie-not-enabled-blocked

> This is the response a model produces **without** the skill definition.
> It fails to check whether Macie is enabled before emitting the
> classification job CLI, which would fail at runtime. It misses the
> pre-flight gate entirely. Generated for with-skill-vs-baseline
> comparison.

---

To create the classification job:

```bash
aws macie2 create-classification-job \
  --name pii-scan-2026-08 \
  --job-type ONE_TIME \
  --s3-job-definition bucketDefinitions='[{accountId=123456789012,buckets=[sensitive-data-prod]}]' \
  --managed-data-identifier-selector-ids USA_SOCIAL_SECURITY_NUMBER CREDIT_CARD_NUMBER
```

The job should start scanning right away.
