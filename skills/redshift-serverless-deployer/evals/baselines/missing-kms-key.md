# Baseline (no-skill) — missing-kms-key

> This is the response a model produces **without** the skill definition.
> It proceeds with deployment using the AWS-owned default KMS key
> without flagging that production encryption requires a CMK. The
> namespace is created but cannot support cross-Region snapshot copy,
> key rotation, or compliance auditing. Migrating to a CMK later
> requires a full UNLOAD/LOAD cycle.

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

Redshift will use the default AWS-owned KMS key for encryption.
