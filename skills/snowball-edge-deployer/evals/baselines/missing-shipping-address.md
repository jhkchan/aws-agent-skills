# Baseline (no-skill) — missing-shipping-address

> This is the response a model produces **without** the skill
> definition. It proceeds with the job creation command despite the
> missing shipping address, which will fail at runtime. Does not emit
> a PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Create the import job:

```bash
aws snowball create-job \
  --job-type IMPORT \
  --resources S3Resources='[{BucketArn=arn:aws:s3:::my-import-bucket}]' \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --shipping-option NEXT_DAY
```

Just add the address when you figure it out.
