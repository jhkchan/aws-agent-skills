# Baseline (no-skill) response: idle-cluster-detection

This file captures what a generic assistant produces WITHOUT the
redshift-cluster-optimizer skill loaded.

---

It looks like your dev Redshift cluster hasn't had any connections or
queries in 22 days. If this cluster isn't being used, you might want to
consider deleting it to save on costs.

You can delete it with:

```bash
aws redshift delete-cluster \
  --cluster-identifier dev-sandbox-cluster \
  --final-cluster-snapshot-identifier final-snapshot-dev-sandbox
```

Make sure to take a final snapshot before deleting so you can restore it
later if needed. Since it's a data sharing consumer, make sure no one
relies on the shared data from this cluster before deleting.
