# Baseline (no-skill) response: materialized-view-for-dashboard

This file captures what a generic assistant produces WITHOUT the
redshift-wlm-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, materialized view DDL, auto-refresh
recommendation, scan-row reduction math, CONFIRM gate).

---

Your dashboard queries are scanning 12 billion rows each time and taking
35 seconds. Since these queries run 500 times per day, that's a lot of
repeated work.

You could create materialized views to pre-compute the aggregates. For
example:

```sql
CREATE MATERIALIZED VIEW dashboard_daily_revenue AS
  SELECT DATE_TRUNC('day', order_date) AS day, region, SUM(revenue) AS revenue
  FROM orders
  GROUP BY 1, 2;
```

Then your dashboards can query the view instead of the base table. You'll
need to refresh the view periodically to keep it up to date. Since your
ETL runs hourly, you could refresh after each ETL run.

This should make your dashboard queries much faster.
