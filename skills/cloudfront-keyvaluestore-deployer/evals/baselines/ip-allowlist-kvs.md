# Baseline (no-skill) — ip-allowlist-kvs

> This is the response a model produces **without** the skill
> definition. It suggests KVS for IP blocking but misses the
> cloudfront-js-2.0 runtime requirement, the 1 MB store limit, the
> eventual consistency propagation window (critical for security), the
> WAF-vs-KVS tradeoff, and the READY_TO_DEPLOY checklist format.

---

You can block IPs using CloudFront KVS:

1. Create a KVS and add the blocked IPs as keys.
2. Write a CloudFront Function that checks the viewer IP.
3. Return 403 if the IP is in the blocklist.

```bash
aws cloudfront create-key-value-store --name ip-blocklist-kvs
aws cloudfront-keyvaluestore put-key --kvs-arn <arn> --key "192.168.1.10" --value "blocked"
```
