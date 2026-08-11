# Baseline (no-skill) — policy-size-limit-exceeded

> This is the response a model produces **without** the skill
> definition. It attempts to apply the 24 KB policy directly,
> which will fail with `MalformedPolicy` at put-bucket-policy time.
> It does not flag the 20 KB limit or recommend Access Points as a
> mitigation. Generated for with-skill-vs-baseline comparison.

---

To attach the policy:

```bash
aws s3api put-bucket-policy \
  --bucket large-policy-bucket \
  --policy file://policy.json
```

This will apply your 24 KB policy with all 15 team statements to
the bucket.
