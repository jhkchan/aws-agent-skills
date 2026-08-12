# Baseline (no-skill) — basic-table-bucket-iceberg

> This is the response a model produces **without** the skill
> definition. It provides a create-table-bucket command but misses the
> namespace-before-table hard dependency (the #1 ordering failure), the
> Iceberg v2 format version choice, the schema as structured Iceberg
> metadata, the partition spec with transforms, the default maintenance
> being enabled, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the bucket:

```bash
aws s3api create-bucket --bucket analytics-tables --region us-east-1
```

Then create the table with your schema and partition it by order_date.
