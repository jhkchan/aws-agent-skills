# Baseline (no-skill) response: prefix-distribution-hot-shard-503-throttling

---

Your S3 bucket is throttled at high request rates. Try:

1. Reduce the request rate from the ingest workers.
2. Batch multiple events into a single PUT.
3. Add retries with exponential backoff to handle 503 responses.
4. Spread writes across multiple buckets.

The 503 SlowDown responses indicate S3 is asking you to slow down.
