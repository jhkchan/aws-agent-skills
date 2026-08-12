# Baseline (no-skill) — basic-s3-oac

> This is the response a model produces **without** the skill
> definition. It creates the OAC but misses the S3 bucket policy
> requirement (the cloudfront.amazonaws.com principal with
> AWS:SourceArn condition — the #1 forgotten step), the
> always-sign vs never-sign signing behavior decision, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the OAC:

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{"Name":"oac","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}'
```

Then attach it to the distribution origin.
