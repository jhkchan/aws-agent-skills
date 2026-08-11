# Baseline (no-skill) — custom-domain-deployment

> This is the response a model produces **without** the skill
> definition. It creates the service but misses the CNAME-to-managed-TLS
> flow, the auto-extension of TLS to custom domains, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the service and add a custom domain:

```bash
aws lightsail create-container-service \
  --service-name app-prod --power large --scale 3
```

Then point app.example.com to it.
