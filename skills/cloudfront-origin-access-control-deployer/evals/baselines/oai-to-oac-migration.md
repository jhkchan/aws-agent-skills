# Baseline (no-skill) — oai-to-oac-migration

> This is the response a model produces **without** the skill
> definition. It removes the OAI and creates the OAC without the
> zero-downtime migration flow (add OAC alongside OAI first, keep
> both during transition, verify, then remove OAI), causing
> potential downtime during the cutover. Misses the bucket policy
> dual-grant transition and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the new OAC and remove the old OAI:

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{"Name":"oac-migrated","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}'

# Update the distribution to use the new OAC instead of the OAI
aws cloudfront delete-origin-access-identity --id E3OAIID1234
```

Then update the bucket policy.
