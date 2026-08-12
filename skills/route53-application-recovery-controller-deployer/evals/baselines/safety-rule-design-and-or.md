# Baseline (no-skill) — safety-rule-design-and-or

> This is the response a model produces **without** the skill
> definition. It does not distinguish AND from OR safety rule types,
> misses the mutual exclusion (AND) vs minimum serving (OR) semantics,
> and does not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create a safety rule:

```bash
aws route53-recovery-control-config create-safety-rule \
  --rule-config '{"Type":"OR","Threshold":1}'
```

That should cover it.
