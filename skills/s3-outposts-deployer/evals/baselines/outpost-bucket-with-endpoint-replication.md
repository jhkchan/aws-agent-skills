# Baseline (no-skill) — outpost-bucket-with-endpoint-replication

> This is the response a model produces **without** the skill
> definition. It creates the bucket but misses the mandatory VPC endpoint
> requirement (the #1 access issue), tries to use standard s3 CLI instead
> of s3control, and does not emit the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Create the bucket:

```bash
aws s3 mb s3://my-outpost-bucket
```

Then add replication rules in the console.
