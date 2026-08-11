# Baseline (no-skill) response: statistic-mismatch-dashboard-vs-alarm

---

Your alarm stays in OK while the dashboard shows the metric breaching.
The threshold is 500ms but the alarm isn't firing. Try lowering the
threshold to see if the alarm starts triggering. Also check the
EvaluationPeriods — 5 consecutive periods is a lot; maybe reduce it
to 1 or 2 so the alarm fires faster.

If the dashboard is using a different aggregation than the alarm,
that could explain the difference. Make sure both are looking at the
same view of the data.
