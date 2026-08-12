# Baseline (no-skill) — athena-lake-formation-integration

> This is the response a model produces **without** the skill
> definition. It points Athena at an S3 path (wrong — S3 Tables
> requires the Iceberg REST catalog), misses Lake Formation grants
> entirely, uses standard S3 APIs instead of s3tables, and does not
> emit the READY_TO_DEPLOY checklist. Generated for with-skill-vs-
> baseline comparison.

---

Create the bucket, then point Athena at the S3 path:

```bash
aws s3api create-bucket --bucket bi-tables --region us-east-1
```

In Athena, create an external table pointing at
`s3://bi-tables/reporting/daily_revenue/`.
