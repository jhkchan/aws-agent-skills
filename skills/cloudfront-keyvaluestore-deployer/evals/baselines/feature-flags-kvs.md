# Baseline (no-skill) — feature-flags-kvs

> This is the response a model produces **without** the skill
> definition. It lists generic steps but misses the cloudfront-js-2.0
> runtime requirement, the read-only constraint from within functions,
> the flat key-value schema recommendation, the etag-based concurrency,
> and the READY_TO_DEPLOY checklist format.

---

Here's how to set up feature flags with CloudFront KVS:

1. Create a KeyValueStore.
2. Add your flag keys to it.
3. Create a CloudFront Function to read the flags.
4. Attach to your distribution.

Use the CLI to toggle flags by updating the KVS values.
