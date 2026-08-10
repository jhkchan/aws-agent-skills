# Baseline (no-skill) response: cw-emf-missing-aws-field

This file captures what a generic assistant produces WITHOUT the
cloudwatch-metrics-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, category-aware
walk, specific remediation).

---

Your custom metric isn't showing up. Since you're using EMF (not
PutMetricData), CloudWatch Logs needs to parse the metric directive
out of your log entries. Looking at the log blob, it's missing the
`_aws` field that contains the `CloudWatchMetrics` directive. Without
that, CloudWatch just ingests the line as a log entry and doesn't
extract any metrics.

Make sure your code actually calls `metrics.flush()` (or equivalent)
to attach the EMF directive before the log line is written. The
directive should look like:

```json
{
  "_aws": {
    "CloudWatchMetrics": [...],
    "Timestamp": 1691616000000
  },
  "JobsProcessed": 42
}
```
