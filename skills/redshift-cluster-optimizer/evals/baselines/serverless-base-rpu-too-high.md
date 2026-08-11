# Baseline (no-skill) response: serverless-base-rpu-too-high

This file captures what a generic assistant produces WITHOUT the
redshift-cluster-optimizer skill loaded.

---

Your Redshift Serverless workgroup has a base capacity of 32 RPU but
is only using an average of 8 RPU. You can lower the base capacity to
reduce costs.

To update the base capacity:

```bash
aws redshift-serverless update-workgroup \
  --workgroup-name analytics-serverless \
  --base-capacity 8
```

This should significantly reduce your monthly cost since you're paying
for 32 RPU even when only using 8. Setting it to 8 RPU will still give
you room to auto-scale up to your max of 128 RPU when needed.
