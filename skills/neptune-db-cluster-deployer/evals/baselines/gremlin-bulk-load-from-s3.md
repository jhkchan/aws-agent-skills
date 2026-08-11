# Baseline (no-skill) — gremlin-bulk-load-from-s3

> This is the response a model produces **without** the skill
> definition. It creates the cluster but misses the same-region S3
> requirement for the Neptune Loader, the IAM role trust policy
> (rds.amazonaws.com), the loader HTTP endpoint format, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to create a Neptune cluster and load data:

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier analytics-graph \
  --engine neptune \
  --db-instance-class db.r6g.4xlarge

aws neptune create-db-instance \
  --db-instance-identifier analytics-graph-1 \
  --db-cluster-identifier analytics-graph
```

Then load the data from S3 with a script that adds vertices one by
one via Gremlin. Something like:

```python
for row in read_s3_csv("s3://graph-data-bucket/v1/"):
    g.addV(row.label).property("name", row.name).iterate()
```

That should work.
