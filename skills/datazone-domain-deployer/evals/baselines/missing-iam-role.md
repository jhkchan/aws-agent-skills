# Baseline (no-skill) — missing-iam-role

> This is the response a model produces **without** the skill
> definition. It creates the domain and data source referencing an
> IAM role that does not exist without verifying the role exists first.
> The data source crawl will fail at runtime with Access Denied. Does
> not emit a PREREQUISITES_MISSING verdict. Generated for with-skill-
> vs-baseline comparison.

---

Sure, here's the domain:

```bash
aws datazone create-domain --name new-domain
aws datazone create-data-source --name my-data-bucket --type S3 \
  --role-arn arn:aws:iam::222222222222:role/NonExistentRole
```

Then add the project and connect the data source.
