# Baseline (no-skill) — cross-account-directory-sharing

> This is the response a model produces **without** the skill
> definition. It shares the directory but misses the accepter-side
> acceptance step requirement, the constraint that only Managed
> Microsoft AD can be shared, the unsharing breakage warning, and
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Share the directory:

```bash
aws ds share-directory \
  --directory-id d-aaa111222 \
  --share-target Id=999999999999,Type=ACCOUNT
```

Done.
