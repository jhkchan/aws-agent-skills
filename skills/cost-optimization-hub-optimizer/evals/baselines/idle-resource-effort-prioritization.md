# Baseline (no-skill) — idle-resource-effort-prioritization

> This is the response a model produces **without** the skill
> definition. It lists the idle-resource recommendations but
> does not prioritize by effort level, does not annualize the
> savings, and does not emit the FURTHER_OPTIMIZATION_AVAILABLE
> verdict. Generated for with-skill-vs-baseline comparison.

---

Here are the idle resources:

```bash
aws cost-optimization-hub get-recommendations \
  --filter '{"action":"Stop"}'
```

Total savings ~$2,140/month. Start with the EIPs since those
are easy.
