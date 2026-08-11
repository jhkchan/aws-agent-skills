# Baseline (no-skill) response: ctas-materialization-repeated-scan

This file captures what a generic assistant produces WITHOUT the
athena-query-optimizer skill loaded.

---

Your dashboard runs the same aggregation query 50 times per day, each time
scanning 200 GB. That's expensive at $1,500/month. You could create a
materialized view or use CTAS to pre-compute the aggregation and store the
results in a smaller table.

Try creating a summary table that gets updated daily, and point your
dashboard at that table instead. This way each dashboard query reads the
small summary table instead of scanning the raw events.

Also make sure result reuse is enabled so identical queries get cached.
