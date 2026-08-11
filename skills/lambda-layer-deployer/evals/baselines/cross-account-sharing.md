# Baseline (no-skill) — cross-account-sharing

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the resource-based
> policy requirement for cross-account sharing, the consumer-side
> IAM permission, the compatible runtimes and architectures
> declarations, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

To create and share a Lambda layer:

1. Install numpy and pandas:
```bash
pip install -t python/ numpy pandas
zip -r shared-utils-layer.zip python/
```

2. Publish:
```bash
aws lambda publish-layer-version \
  --layer-name shared-utils-layer \
  --zip-file fileb://shared-utils-layer.zip
```

3. Share with the other account:
```bash
aws lambda add-permission \
  --layer-name shared-utils-layer \
  --statement-id share \
  --action lambda:GetLayerVersion \
  --principal 123456789012
```

They should be able to use it now.
