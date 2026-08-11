# Baseline (no-skill) response: table-bucket-iceberg-ready

This file captures what a generic assistant produces WITHOUT the
s3-directory-bucket-deployer skill loaded — the contrast that proves
the skill routes table buckets to the correct s3tables API instead of
the generic create-directory-bucket.

---

To store Iceberg tables in S3, create a bucket:

```bash
aws s3api create-directory-bucket \
  --bucket events-iceberg-tables--use1-az1--x-s3 \
  --data-redundancy SingleAvailabilityZone
```

Then configure your Spark/Athena to read from this bucket.
