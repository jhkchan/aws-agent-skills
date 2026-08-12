# Baseline (no-skill) — multi-account-payer-rollout

> This is the response a model produces **without** the skill
> definition. It enables the Hub on the payer but does not
> call out --include-member-accounts, the Compute Optimizer
> enrollment requirement for right-size recommendations, or
> the OPTIMIZED / FURTHER_OPTIMIZATION_AVAILABLE verdict
> format. Generated for with-skill-vs-baseline comparison.

---

Run this on the payer:

```bash
aws cost-optimization-hub update-enrollment-status --status ACTIVE
```

That should cover the org. You can also look at Cost Explorer
for RI/SP gaps.
