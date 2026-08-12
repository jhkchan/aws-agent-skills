# Baseline (no-skill) — multi-region-inventory

> This is the response a model produces **without** the skill
> definition. It lists certificates in only one region (missing the
> multi-region aspect), does not check service attachment, and omits
> the OPERATION_COMPLETED report format. Generated for with-skill-vs-
> baseline comparison.

---

List your certificates:

```bash
aws acm list-certificates --region us-east-1
```

Check each one with describe-certificate. You might want to do this
in each region separately.
