# Baseline (no-skill) response: timeout-no-early-filter

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-insights-troubshooter skill loaded.

---

Your query timed out because it's scanning too much data. Try
narrowing the time range to 1 day instead of 7. You could also try
adding a filter to reduce the number of events being processed.

If that doesn't work, maybe your log group is too large and you need
to archive some older logs or reduce the retention period.
