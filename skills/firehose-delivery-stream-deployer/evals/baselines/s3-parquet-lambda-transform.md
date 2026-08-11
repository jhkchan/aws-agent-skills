# Baseline (no-skill) — s3-parquet-lambda-transform

> This is the response a model produces **without** the skill
> definition. It creates the stream but uses default buffering hints
> (5MB, producing many tiny Parquet files), a flat S3 prefix (no
> Hive-style partitioning for Athena), and misses the format
> conversion Glue schema dependency. Generated for with-skill-vs-
> baseline comparison.

---

Create the delivery stream:

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name events-to-s3-parquet \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration RoleARN=...,BucketARN=...,Prefix=data/
```

Then configure transformation and destination.
