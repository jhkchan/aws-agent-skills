# Baseline (no-skill) — template-multi-tenant-deployment

> This is the response a model produces **without** the skill
> definition. It mentions templates but misses the multi-tenant
> deployment flow (template from analysis, per-tenant dataset and
> dashboard from template, RLS per tenant, update propagation), the
> schema-match requirement, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

You can use QuickSight templates for multi-tenant:

1. Create a template from your dashboard.
2. Create dashboards for each tenant.

```bash
aws quicksight create-template --name "sales-template"
aws quicksight create-dashboard --name "tenant-a-sales"
```

Make sure each tenant has their own data.
