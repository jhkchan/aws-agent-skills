# Baseline (no-skill) — access-point-and-lifecycle

> This is the response a model produces **without** the skill
> definition. It tries to create a lifecycle rule with Glacier
> transition (not supported on Outpost), misses the endpoint requirement,
> and does not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the bucket and add lifecycle:

```bash
aws s3 mb s3://lifecycle-bucket
aws s3api put-bucket-lifecycle-configuration \
  --bucket lifecycle-bucket \
  --lifecycle-configuration '{"Rules":[{"Status":"Enabled","Transitions":[{"Days":30,"StorageClass":"GLACIER"}]}]}'
```
