# Baseline (no-skill) — missing-security-group

> This is the response a model produces **without** the skill definition.
> It deploys the namespace and workgroup without checking the security
> group inbound rules. The analytics application cannot connect via
> JDBC because there is no inbound rule for port 5439. This is a
> silent failure — the workgroup is AVAILABLE but unreachable.

---

Here are the commands to deploy your Redshift Serverless namespace
and workgroup:

```bash
aws redshift-serverless create-namespace \
  --namespace-name analytics-ns-prod \
  --admin-username admin \
  --admin-user-password 'TempPass123!' \
  --db-name dev \
  --security-group-ids sg-redshift-prod

aws redshift-serverless create-workgroup \
  --workgroup-name analytics-wg-prod \
  --namespace-name analytics-ns-prod \
  --base-capacity 64 \
  --subnet-group-name redshift-subnet-group \
  --security-group-ids sg-redshift-prod
```

Your analytics application should be able to connect once the
workgroup is available.
