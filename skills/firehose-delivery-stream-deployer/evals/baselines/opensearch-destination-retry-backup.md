# Baseline (no-skill) — opensearch-destination-retry-backup

> This is the response a model produces **without** the skill
> definition. It creates the stream but misses the
> FailedDocumentsOnly backup configuration, uses default buffering
> hints (too large for OpenSearch), and does not configure retry
> duration. Generated for with-skill-vs-baseline comparison.

---

Create the delivery stream:

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name logs-to-opensearch \
  --delivery-stream-type DirectPut \
  --elasticsearch-destination-configuration RoleARN=...,DomainARN=...,IndexName=logs
```

Then configure S3 backup.
