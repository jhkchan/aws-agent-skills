# Baseline (no-skill) — custom-data-identifier-regex

> This is the response a model produces **without** the skill definition.
> It omits the proximity keywords (which causes massive false positives),
> the ignore words (test data not excluded), the maximum match distance,
> and the severity levels. It misses the VERDICT/PRE_CHECKS output
> contract. Generated for with-skill-vs-baseline comparison.

---

To create a custom data identifier:

```bash
aws macie2 create-custom-data-identifier \
  --name employee-id-pattern \
  --regex "EMP[0-9]{6}"
```

That will detect any employee ID in your data.
