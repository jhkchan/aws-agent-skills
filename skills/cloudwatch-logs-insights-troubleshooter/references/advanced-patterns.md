# Advanced Patterns (load on demand) — CloudWatch Logs Insights Troubleshooter

Step rationale prose, common fix patterns, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Step rationale prose (moved from SKILL.md)

**Step 2 — NO_RESULTS rationale:**

A query that completes with zero rows means the query ran but matched
nothing. The cause is almost always one of: wrong log group, time
range outside the ingestion window, filter pattern too restrictive,
or field name mismatch (the `filter` references a field that does not
exist in the log payload).

**Step 3 — TIMEOUT rationale:**

A query that times out or is cancelled scanned too much data. Logs
Insights enforces a limit on the volume of data scanned per query.
The fix is always to reduce the data scanned — not to "make the query
faster."

**Step 4 — SYNTAX_ERROR rationale:**

Logs Insights uses a pipe-delimited query language. Syntax errors
typically involve quoting, the `stats` aggregation syntax, the
`parse` pattern, or the `sort`/`limit` placement.

**Step 5 — CONTRIBUTOR_INSIGHTS rationale:**

Contributor Insights is a SEPARATE feature from Logs Insights. It
runs pre-defined rules that aggregate log data into top-N contributor
reports (top source IPs, top user agents, etc.). It does NOT use Logs
Insights query syntax, and enabling Logs Insights does NOT enable
Contributor Insights.

**Step 6 — METRIC_FILTER_CONFUSION rationale:**

Metric filters and Logs Insights are different features with different
purposes:
---

## Common fix patterns (moved from SKILL.md)

**Step 2 — NO_RESULTS fixes:**

**Common fix patterns:**

- **Wrong log group:** correct the name; verify with
  `describe-log-groups`.
- **Time range outside ingestion:** widen to include
  `lastIngestionTime`, or confirm the app is emitting logs.
- **Filter too restrictive:** run without filter first to confirm
  data, then add filters back one at a time.
- **Case sensitivity:** use `(?i)` in regex or `strcontains`.
- **Field name mismatch:** inspect `@message`; use `parse` to extract
  fields from non-JSON logs before filtering.

**Step 5 — CONTRIBUTOR_INSIGHTS fixes:**

**Common fix patterns:**

- **No rule exists:** create one via `put-insight-rule`. Each log group
  needs its own rule.
- **Rule is `DISABLED`:** re-enable with `--rule-state Enabled`.
- **Wrong log group:** the `LogGroupNames` array must include the exact
  log group name.
- **Log format changed:** update the rule's `LogFormat` (`JSON` vs
  `CLF`/custom) if the app switched log formats.

**Step 6 — METRIC_FILTER_CONFUSION fixes:**

**Common fix patterns:** use metric filters for metrics + alarms, Logs
Insights for ad-hoc queries. Test patterns with `test-metric-filter`.
Verify the alarm references the same namespace and metric name as the
filter's `metricTransformations`.
---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Logs Insights `pattern` command (2024 GA):** auto-detects and
  clusters log patterns. Usage: `fields @timestamp, @message | pattern
  @message | limit 20`. Outputs `@pattern`, `@sampleCount`,
  `@representation`. Troubleshoot empty results by ensuring
  `@message` is available (not consumed by a prior `parse`).
- **Logs Insights anomaly detection (2024-2025):** the console
  anomaly view compares recent log volumes to a historical baseline.
  Requires 2+ weeks of data. Troubleshoot by verifying
  `stats count() by bin(5m)` produces the time series and the
  grouping field exists.
- **CloudWatch Logs integrated query experience (2025):** the unified
  console merges Logs Insights, Contributor Insights, and metric
  filters into one "Logs" tab — making METRIC_FILTER_CONFUSION more
  common. Verify which sub-feature the user is actually using.
- **CloudWatch Logs data protection (2024-2026):** data protection
  policies mask sensitive fields in `@message` (replaced with `***`).
  If a previously-working filter stops matching, check the log
  group's data protection policy.
