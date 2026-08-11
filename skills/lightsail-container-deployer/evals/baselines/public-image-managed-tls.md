# Baseline (no-skill) — public-image-managed-tls

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the power-scale-vs-node-
> count distinction, the managed TLS auto-provisioning, the health check
> path configuration, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the container service:

```bash
aws lightsail create-container-service \
  --service-name web-frontend --power small --scale 2
```

Then deploy nginx.
