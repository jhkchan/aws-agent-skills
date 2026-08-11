# Baseline (no-skill) — production-namespace-workgroup

> This is the response a model produces **without** the skill definition.
> It produces the create-namespace and create-workgroup commands but
> misses usage limits, enhanced VPC routing, Data API enablement,
> Secrets Manager admin credential management, and log exports. The
> workgroup deploys but cost controls are absent and COPY/UNLOAD
> traffic traverses the public internet.

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

Your workgroup should be available shortly.
