# Baseline (no-skill) — ecr-private-with-auth

> This is the response a model produces **without** the skill
> definition. It creates the service but misses the ECR credential
> requirement, the managed TLS auto-provisioning, the health check
> customization, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the service and deploy:

```bash
aws lightsail create-container-service \
  --service-name api-service --power medium --scale 3
```

Then add the ECR image.
