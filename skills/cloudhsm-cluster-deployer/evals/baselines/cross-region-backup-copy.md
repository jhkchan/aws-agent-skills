# Baseline (no-skill) — cross-region-backup-copy

> This is the response a model produces **without** the skill
> definition. It performs the copy but treats the destination as a
> hot replica and does not flag that restore creates a NEW
> cluster-id. Generated for with-skill-vs-baseline comparison.

---

Copy the backup:

```bash
aws cloudhsmv2 copy-backup-to-region \
  --backup-id bk-aaa11122 \
  --destination-region us-west-2
```

Now you have a hot replica in us-west-2.
