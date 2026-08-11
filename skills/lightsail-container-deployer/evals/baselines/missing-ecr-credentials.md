# Baseline (no-skill) — missing-ecr-credentials

> This is the response a model produces **without** the skill
> definition. It attempts to deploy with an ECR image without flagging
> the missing credentials, which will fail at runtime. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's the container service:

```bash
aws lightsail create-container-service \
  --service-name data-processor --power small --scale 1
```

Then deploy the ECR image.
