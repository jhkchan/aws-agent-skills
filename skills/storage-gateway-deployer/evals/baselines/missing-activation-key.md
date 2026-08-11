# Baseline (no-skill) — missing-activation-key

> This is the response a model produces **without** the skill
> definition. It proceeds with the deployment commands despite the
> missing activation key, which will fail at runtime. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Here is how to deploy the gateway:

```bash
aws storagegateway activate-gateway \
  --activation-key <your-key> \
  --gateway-name prod-s3-gateway \
  --gateway-region us-east-1 \
  --gateway-type FILE_S3
```

Just generate the activation key from the VM console and plug it in.
