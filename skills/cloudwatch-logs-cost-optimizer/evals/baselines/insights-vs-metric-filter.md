# Baseline (no-skill) response: insights-vs-metric-filter

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-cost-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, per-query scan-cost
math, metric-filter syntax, CONFIRM gate).

---

You're running a lot of Logs Insights queries — 450 per month scanning
120 GB each. At $0.005/GB scanned, that's about $270/month in query
costs alone.

Since your queries are mostly counting errors and timeouts, you could
use metric filters instead. Metric filters are free and compute the
same counts at ingestion time.

You can create a metric filter like this:

```
aws logs put-metric-filter --log-group-name /app/insights-vs-metric-filter --filter-name ErrorCount --filter-pattern '"ERROR"' --metric-transformations metricName=ErrorCount,metricNamespace=AppMetrics,metricValue=1
```

This should eliminate most of your $270/month in Insights charges.
