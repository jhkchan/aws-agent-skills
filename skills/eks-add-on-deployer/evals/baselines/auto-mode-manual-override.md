# Baseline (no-skill) — auto-mode-manual-override

> This is the response a model produces **without** the skill
> definition. It does not recognize that Auto Mode manages vpc-cni
> automatically and gives instructions that would be silently reverted.
> The skill correctly identifies this as PREREQUISITES_MISSING.

---

To update vpc-cni on your Auto Mode cluster:

```bash
aws eks update-addon --cluster-name auto-mode-cluster \
  --addon-name vpc-cni \
  --addon-version v1.19.0-eksbuild.1 \
  --configuration-values '{"env":{"ENABLE_IPv6":"true"}}'
```

That should work fine.
