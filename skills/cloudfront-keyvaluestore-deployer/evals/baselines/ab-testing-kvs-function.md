# Baseline (no-skill) — ab-testing-kvs-function

> This is the response a model produces **without** the skill
> definition. It mentions KVS and functions but misses the
> cloudfront-js-2.0 runtime requirement, the KVS-function linkage
> mechanism, the eventual consistency model, the etag-based
> concurrency, the read-only constraint, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To set up A/B testing with CloudFront KeyValueStore:

1. Create a KVS:
```bash
aws cloudfront create-key-value-store --name ab-testing-kvs
```

2. Add a key for the split:
```bash
aws cloudfront-keyvaluestore put-key --kvs-arn <arn> --key split --value "50"
```

3. Create a function that reads the KVS and routes traffic.

4. Attach it to your distribution.

That should work.
