# Baseline (no-skill) response: lifecycle-policy-gap

This file captures what a generic assistant produces WITHOUT the
s3-storage-class-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-TB savings math,
lifecycle template, CONFIRM gate, Batch Operations plan).

---

Your S3 bucket has 45 TB of data with most of it in Standard storage.
Since you said the data is rarely accessed after 90 days, you should
set up lifecycle policies to move old data to cheaper storage classes.

You could move data older than 90 days to Glacier and data older than
a year to Deep Archive. That would save a lot since Deep Archive is
much cheaper than Standard.

Here's how to create a lifecycle policy:

```
aws s3api put-bucket-lifecycle-configuration \
  --bucket bucket-lifecycle-policy-gap \
  --lifecycle-configuration file://lifecycle.json
```

You'll need to write the lifecycle JSON configuration. This should
reduce your S3 bill significantly.
