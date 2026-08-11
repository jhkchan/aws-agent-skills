# Baseline (no-skill) — version-conflict-resolution

> This is the response a model produces **without** the skill
> definition. It creates the EKS add-on but does not address the
> conflict resolution strategy, does not export the self-managed config
> first, and does not re-apply customizations via --configuration-values.
> The skill correctly handles the full migration pattern.

---

To migrate from self-managed to EKS-managed vpc-cni:

```bash
aws eks create-addon --cluster-name migration-cluster \
  --addon-name vpc-cni
```

Then re-apply your settings.
