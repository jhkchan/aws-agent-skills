# Baseline (no-skill) — hsm-degradation-recovery

> This is the response a model produces **without** the skill
> definition. It deletes the degraded HSM before creating a
> replacement, dropping the cluster below the HA threshold. Does
> not flag the create-replacement-first ordering. Generated for
> with-skill-vs-baseline comparison.

---

Delete the degraded HSM:

```bash
aws cloudhsmv2 delete-hsm \
  --cluster-id cluster-abc123def \
  --hsm-id hsm-degraded111
```

Then create a new one if you need it.
