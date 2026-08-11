# Baseline (no-skill) — instance-based-ssm-discovery

> This is the response a model produces **without** the skill
> definition. It creates a license configuration but misses the
> Instance counting type requirement, the SSM inventory enablement
> for on-premises discovery, and the soft-limit flag. Does not emit
> a READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the license config:

```bash
aws license-manager create-license-configuration \
  --name "middleware" \
  --license-count 50
```

Then associate with your instances.
