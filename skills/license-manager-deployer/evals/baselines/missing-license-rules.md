# Baseline (no-skill) — missing-license-rules

> This is the response a model produces **without** the skill
> definition. It creates the license configuration without flagging
> the missing Oracle vendor rules (Tenancy, HonorVcpuOptimization),
> which means the configuration exists but does NOT enforce Oracle-
> specific conditions. Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Here you go:

```bash
aws license-manager create-license-configuration \
  --name "oracle-db" \
  --license-counting-type vCPU \
  --license-count 200 \
  --license-rules-enforce
```

Then associate with your launch template.
