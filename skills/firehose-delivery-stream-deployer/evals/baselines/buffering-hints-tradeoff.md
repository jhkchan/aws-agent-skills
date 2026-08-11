# Baseline (no-skill) — buffering-hints-tradeoff

> This is the response a model produces **without** the skill
> definition. It creates the stream with default buffering hints
> (5MB), producing many tiny Parquet files that degrade Athena query
> performance. Does not recognize the buffering-vs-Athena-performance
> trade-off. Generated for with-skill-vs-baseline comparison.

---

Create the delivery stream:

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name analytics-parquet \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration RoleARN=...,BucketARN=...,Prefix=data/
```

Default buffering hints (5MB / 300s) are used, producing many small
Parquet files. No tuning for Athena downstream.
