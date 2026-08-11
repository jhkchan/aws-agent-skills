# Baseline (no-skill) — splunk-http-endpoint

> This is the response a model produces **without** the skill
> definition. It creates the stream but misses the S3 backup for
> failed documents and uses default buffering hints (too large for
> low-latency SIEM ingestion). Generated for with-skill-vs-baseline
> comparison.

---

Create the delivery stream:

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name security-to-splunk \
  --delivery-stream-type DirectPut \
  --http-endpoint-destination-configuration RoleARN=...,EndpointConfiguration.Url=https://splunk.example.com:8088/...
```

Then configure S3 backup.
