# Baseline (no-skill) — export-job-s3

> This is the response a model produces **without** the skill
> definition. It lists the create-job command but misses that export
> data is pre-loaded by AWS before shipping, does not mention the NFS
> interface for offloading data, and omits the READY_TO_DEPLOY
> checklist. Generated for with-skill-vs-baseline comparison.

---

Create the Snowball export job:

```bash
aws snowball create-job \
  --job-type EXPORT \
  --resources S3Resources='[{BucketArn=arn:aws:s3:::my-export-bucket}]' \
  --address-id addr-export01 \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --shipping-option NEXT_DAY
```

When the device arrives, copy the data off it.
