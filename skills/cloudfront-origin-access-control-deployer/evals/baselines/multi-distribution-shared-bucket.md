# Baseline (no-skill) — multi-distribution-shared-bucket

> This is the response a model produces **without** the skill
> definition. It creates OACs for each distribution but misses that
> the bucket policy must list ALL distribution ARNs in the
> AWS:SourceArn condition (a single ARN would block the other
> distributions), and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create an OAC for each distribution:

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{"Name":"oac-shared","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}'
```

Update the bucket policy to allow CloudFront:

```json
{
  "Principal": {"Service": "cloudfront.amazonaws.com"},
  "Action": "s3:GetObject"
}
```

Then attach the OAC to each distribution.
