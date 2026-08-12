# Baseline (no-skill) — cloudfront-custom-domain

> This is the response a model produces **without** the skill
> definition. It creates the function URL but does not address
> CloudFront custom domain setup, DefaultTTL configuration, query
> string forwarding, or the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the function URL:

```bash
aws lambda create-function-url-config \
  --function-name my-edge-handler \
  --auth-type NONE \
  --invoke-mode BUFFERED
```

Then point your domain at it.
