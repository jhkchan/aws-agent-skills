# Baseline (no-skill) — kvs-size-limit-exceeded

> This is the response a model produces **without** the skill
> definition. It does not flag the 1 MB store limit or the 1 ms
> function execution time constraint for iterating 8000 keys. The
> skill correctly identifies this as PREREQUISITES_MISSING and
> recommends AWS WAF IP sets.

---

To store 8000 IPs in a CloudFront KVS:

1. Create the KVS:
```bash
aws cloudfront create-key-value-store --name big-blocklist-kvs
```

2. Loop through your IPs and add each one:
```bash
for ip in $(cat ips.txt); do
  aws cloudfront-keyvaluestore put-key --kvs-arn <arn> --key "$ip" --value "blocked"
done
```

3. Create a function that checks each request's IP against the KVS.

That should handle your blocklist.
