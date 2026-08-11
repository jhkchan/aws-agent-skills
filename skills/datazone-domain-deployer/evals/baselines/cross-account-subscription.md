# Baseline (no-skill) — cross-account-subscription

> This is the response a model produces **without** the skill
> definition. It creates the domain and data source but misses the
> three-account topology IAM role chaining (domain → source →
> consumer), the consumer account IAM role requirement, the
> subscription workflow request-approve model, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the domain and add the S3 data source:

```bash
aws datazone create-domain --name shared-analytics
aws datazone create-data-source --name shared-data-lake --type S3
```

Then the consumer can subscribe to the assets. Data sharing should
work across accounts automatically.
