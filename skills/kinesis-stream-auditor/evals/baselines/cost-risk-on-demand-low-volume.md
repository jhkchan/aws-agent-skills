# Baseline (no-skill) response: cost-risk-on-demand-low-volume

This file captures what a generic assistant produces WITHOUT the
kinesis-stream-auditor skill loaded.

---

This on-demand stream is encrypted with a customer-managed KMS key and
has enhanced monitoring enabled, which is good. At 80 MB/day of ingest,
the stream is fairly low volume.

On-demand mode is convenient for bursty workloads, but at this low data
volume you might want to evaluate whether provisioned mode would be more
cost-effective. The retention period of 24 hours is the default and
should be fine.

The stream has 1 consumer and 4 shards (the on-demand default).
