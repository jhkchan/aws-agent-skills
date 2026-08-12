# Baseline (no-skill) — website-endpoint-mismatch

> This is the response a model produces **without** the skill
> definition. It creates the OAC without flagging that the S3 bucket
> has static website hosting enabled — OAC only supports the S3 origin
> type, not the Website Endpoint. The distribution would appear to
> configure successfully but CloudFront would receive 403 errors
> because the Website Endpoint does not process SigV4-signed requests.
> Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Create the OAC:

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{"Name":"oac-website","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}'
```

Attach it to the distribution origin pointing at the bucket's website endpoint.
