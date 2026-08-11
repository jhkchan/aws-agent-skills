# Baseline (no-skill) — enterprise-spice-athena-dashboard

> This is the response a model produces **without** the skill
> definition. It creates the data source and dashboard but misses the
> SPICE vs Direct Query trade-off analysis, the refresh schedule setup,
> the row-level security dataset pattern, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To create a QuickSight dashboard with Athena:

1. Sign up for QuickSight Enterprise.
2. Add Athena as a data source.
3. Create a dataset selecting your table.
4. Build a dashboard with some charts.
5. Share it with your team.

```bash
aws quicksight create-data-source --type ATHENA --name "Athena"
aws quicksight create-data-set --import-mode SPICE --name "sales_metrics"
```

You can set up refresh and security in the console.
