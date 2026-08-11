# Baseline (no-skill) — cost-controls-usage-limits

> This is the response a model produces **without** the skill definition.
> It creates the namespace and workgroup but does not set usage limits,
> log exports, or enhanced VPC routing. A runaway query can exhaust
> the budget in hours with no guardrail, and COPY/UNLOAD traffic
> traverses the public internet.

---

Here are the commands to deploy your Redshift Serverless namespace
and workgroup:

```bash
aws redshift-serverless create-namespace \
  --namespace-name bi-ns-prod \
  --admin-username admin \
  --admin-user-password 'TempPass123!' \
  --db-name reporting

aws redshift-serverless create-workgroup \
  --workgroup-name bi-wg-prod \
  --namespace-name bi-ns-prod \
  --base-capacity 64 \
  --subnet-group-name bi-subnet-group
```

Your BI workgroup should be available shortly. You can monitor
costs in the billing console.
