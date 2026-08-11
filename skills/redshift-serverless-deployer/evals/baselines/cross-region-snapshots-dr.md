# Baseline (no-skill) — cross-region-snapshots-dr

> This is the response a model produces **without** the skill definition.
> It creates the namespace and workgroup but does not configure
> scheduled snapshots or cross-Region snapshot copy. It also misses the
> requirement for a separate destination-Region KMS key, so the
> snapshot copy grant will fail.

---

Here are the commands to deploy your Redshift Serverless namespace
and workgroup:

```bash
aws redshift-serverless create-namespace \
  --namespace-name analytics-ns-prod \
  --admin-username admin \
  --admin-user-password 'TempPass123!' \
  --db-name dev

aws redshift-serverless create-workgroup \
  --workgroup-name analytics-wg-prod \
  --namespace-name analytics-ns-prod \
  --base-capacity 128 \
  --subnet-group-name redshift-subnet-group
```

You can set up snapshots later from the console.
