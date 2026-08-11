# Baseline (no-skill) — import-job-s3

> This is the response a model produces **without** the skill
> definition. It lists the create-job command but misses the data flow
> explanation (device must be returned before AWS uploads to S3), does
> not mention NFS interface setup after unlock, and omits the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the Snowball import job:

```bash
aws snowball create-job \
  --job-type IMPORT \
  --resources S3Resources='[{BucketArn=arn:aws:s3:::my-migration-bucket}]' \
  --address-id addr-aaaabbbb \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --shipping-option NEXT_DAY
```

Then wait for the device to arrive and copy your data to it.
