# Baseline (no-skill) — redshift-environment-profile

> This is the response a model produces **without** the skill
> definition. It creates the domain and Redshift data source but
> misses the distinction between blueprints (WHAT is deployed) and
> environment profiles (WHERE it is deployed), the Secrets Manager
> requirement for Redshift credentials, the cross-account IAM role
> for Redshift access, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the domain and add the Redshift data source:

```bash
aws datazone create-domain --name dw-domain
aws datazone create-data-source --name sales-dw-cluster --type REDSHIFT
```

Then enable the data warehouse blueprint and create an environment.
