# Baseline (no-skill) response: syntax-error-command-ordering

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-insights-troubshooter skill loaded.

---

Your query has a syntax error. The error says "limit must be the last
command" so you should move the sort before the limit. Try changing
the order of the commands. The correct query would be to put sort
first and limit last.

Also make sure your field names are correct and that you're using the
right syntax for CloudWatch Logs Insights.
