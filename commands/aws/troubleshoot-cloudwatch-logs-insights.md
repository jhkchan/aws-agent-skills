---
allowed-tools: Read, Bash, Grep
description: "Diagnose CloudWatch Logs Insights issues — query returns no results, query timeout/cancelled, syntax errors, Contributor Insights not showing, metric filter vs Logs Insights confusion, pattern/anomaly detection problems"
nl_triggers:
  - "CloudWatch Logs Insights no results"
  - "Logs Insights query timeout"
  - "Logs Insights query cancelled"
  - "Logs Insights syntax error"
  - "Logs Insights parse error"
  - "Contributor Insights not showing"
  - "Contributor Insights blank"
  - "Logs Insights filter pattern not matching"
  - "Logs Insights pattern command"
  - "Logs Insights anomaly detection"
  - "metric filter vs Logs Insights"
  - "CloudWatch Logs query returns nothing"
  - "diagnose Logs Insights"
routes_to: cloudwatch-logs-insights-troubshooter
---

# /aws:troubleshoot-cloudwatch-logs-insights

Activate the `cloudwatch-logs-insights-troubshooter` skill and diagnose
a CloudWatch Logs Insights problem.

## What it does

Reads the query text, log group, time range, and error/result and walks
the symptom-to-cause decision tree across six categories:

1. NO_RESULTS — query completes but returns 0 rows (wrong log group,
   stale ingestion, filter case sensitivity, field not extracted).
2. TIMEOUT — query cancelled or timed out (wide time range, no early
   filter, parse before filter, sort before limit on raw events).
3. SYNTAX_ERROR — query fails (command ordering, stats without
   aggregation, glob in like, parse pattern mismatch).
4. CONTRIBUTOR_INSIGHTS — tab empty (no rule created, rule disabled,
   wrong log group in rule, conceptual mismatch with Logs Insights).
5. METRIC_FILTER_CONFUSION — using metric filter syntax in Logs
   Insights or vice versa.
6. PATTERN_ANOMALY — pattern command or anomaly detection not working
   (no @message, short baseline window, field extraction issues).

Emits a deterministic VERDICT per query:

```text
INCIDENT: <log-group> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing query element or config>
EVIDENCE:
  - Query text: <the offending line or pattern>
  - describe-log-groups / describe-log-streams: <signal>
  - get-query-results / describe-queries: <status + result>
  - describe-contributor-insights / describe-metric-filters: <AWS-side signal>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific query or config change>
  2. <verification command>
  3. <post-fix monitoring>
```

## When to invoke

Paste any of the following:

- A Logs Insights query and "it returns nothing" / "0 rows".
- A query timeout / cancellation message.
- A syntax or parse error message.
- "Contributor Insights is empty" / "Contributor Insights not showing".
- "My metric filter isn't working" (may be a Logs Insights query
  instead).
- A `pattern` or anomaly detection question.

A bare log group name + any Logs Insights verb also routes here.

## Inputs

- Query text (the full pipe-delimited command chain).
- Log group name or ARN.
- Time range (relative or absolute).
- Error message or observed result (0 rows, Cancelled, Failed, etc.).
- For Contributor Insights: `describe-contributor-insights` output.
- For metric filter confusion: `describe-metric-filters` output.

## Outputs

- One VERDICT block per query (earliest-blocker wins).
- EVIDENCE citing the specific query lines and AWS-side signals.
- REMEDIATION with exact query rewrites or AWS CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Management/Logs).
- `/aws:audit-cloudwatch-alarm` for alarm configuration audits
  (separate from Logs Insights query diagnosis).
