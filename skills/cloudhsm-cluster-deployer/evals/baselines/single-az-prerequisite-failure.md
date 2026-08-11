# Baseline (no-skill) — single-az-prerequisite-failure

> This is the response a model produces **without** the skill
> definition. It creates the single-AZ cluster without flagging the
> missing HA prerequisite. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Sure:

```bash
aws cloudhsmv2 create-cluster \
  --hsm-type hsm1.medium \
  --subnet-ids subnet-aaa
```

Done.
