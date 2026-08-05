# Baseline (no-skill) response: cost-risk-extended-retention

This file captures what a generic assistant produces WITHOUT the
kinesis-stream-auditor skill loaded.

---

This stream is encrypted with KMS using a customer-managed key, which is
good. The retention period is 720 hours (30 days), which is longer than
the default 24 hours. With 8 shards, this could result in higher storage
costs.

You might want to review whether 30-day retention is necessary for
your consumers. If they only need 24 hours, reducing it would save on
extended retention costs.

The stream has good enhanced monitoring coverage with IteratorAgeMilliseconds
and WriteProvisionedThroughputExceeded enabled.
