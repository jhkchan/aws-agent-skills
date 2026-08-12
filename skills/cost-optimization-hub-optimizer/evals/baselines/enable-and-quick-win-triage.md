# Baseline (no-skill) — enable-and-quick-win-triage

> This is the response a model produces **without** the skill
> definition. It enables the Hub but misses the
> AFTER_DISCOUNT vs BEFORE_DISCOUNT savings mode, the
> Compute Optimizer prerequisite check, the quick-win effort
> filter, and the OPTIMIZED / FURTHER_OPTIMIZATION_AVAILABLE
> checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Enable the Hub:

```bash
aws cost-optimization-hub update-enrollment-status --status ACTIVE
```

Then you can list recommendations in the console.
