# Baseline (no-skill) — missing-endpoint

> This is the response a model produces **without** the skill
> definition. It creates the bucket without flagging the missing VPC
> endpoint as a prerequisite failure. The bucket would be completely
> inaccessible. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here's the bucket:

```bash
aws s3 mb s3://inaccessible-bucket
```

You can set up networking later.
