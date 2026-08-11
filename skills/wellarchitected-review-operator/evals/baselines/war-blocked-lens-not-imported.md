# Baseline (no-skill) response: war-blocked-lens-not-imported

This file captures what a generic assistant produces WITHOUT the
wellarchitected-review-operator skill loaded.

---

To add the Prosperity lens, you can use:

```
aws wellarchitected associate-lenses \
  --workload-id workload-abc123 \
  --lens-aliases wellarchitected-prosperity
```

If the lens is not available, you may need to import it first.
