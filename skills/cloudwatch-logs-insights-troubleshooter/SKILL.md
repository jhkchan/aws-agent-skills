---
name: cloudwatch-logs-insights-troubleshooter
description: 'Diagnoses CloudWatch Logs Insights problems across six categories: query returns no results (wrong log group, time range outside ingestion, filter case sensitivity, field not extracted), query timeout/cancelled (scanning too much data, no early filter, missing stats aggregation), query syntax errors (command ordering, stats without aggregation, glob vs regex in like, parse pattern), Contributor Insights not showing (must enable separately via PutInsightRule; does not share Logs Insights syntax), metric filter vs Logs Insights confusion (separate features with different syntax/output), and pattern/anomaly detection issues. Walks a symptom-to-cause decision tree using describe-log-groups, describe-log-streams, start-query, get-query-results, describe-queries, describe-contributor-insights. Emits a verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE). Use when a Logs Insights query returns nothing, times out, throws a syntax error, Contributor Insights is blank, or pattern/anomaly detection fails.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on pasted query text, error messages, and console screenshots. Live-account diagnosis uses aws logs describe-log-groups, describe-log-streams, start-query, get-query-results, describe-queries, stop-query, describe-contributor-insights, get-log-record, and filter-log-events (AWS CLI v2, SSO or key-based credentials, logs:DescribeLogGroups, logs:StartQuery, logs:GetQueryResults...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: 'Diagnosing CloudWatch Logs Insights failures: query returns zero rows, query is cancelled or times out, query throws a syntax / parse error, Contributor Insights shows no data for a log group, metric filters appear not to work (and the user is actually using Logs Insights), or the new pattern / anomaly detection commands do not produce expected output.'
  activation_triggers: CloudWatch Logs Insights no results, Logs Insights query timeout, Logs Insights query cancelled, Logs Insights syntax error, Logs Insights parse error, Contributor Insights not showing, Contributor Insights blank, Logs Insights filter pattern not matching, Logs Insights pattern command, Logs Insights anomaly detection, metric filter vs Logs Insights, CloudWatch Logs query returns nothing
  invocation_schema: 'Input: either (a) a symptom description (query text, observed result, error message, log group name), OR (b) a live-account scenario where the agent runs aws logs describe-log-groups, start-query, get-query-results, describe-queries to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT is one of {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific failure category (NO_RESULTS / TIMEOUT / SYNTAX_ERROR / CONTRIBUTOR_INSIGHTS / METRIC_FILTER_CONFUSION / PATTERN_ANOMALY) and the offending query element or config.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch Logs, Logs Insights, query, no results, timeout, syntax error, filter pattern, Contributor Insights, metric filter, pattern command, anomaly detection, parse, stats, sort, limit, fields, display, glob, regular expression, time range
  tags: cloudwatch, logs, management, troubleshoot, query, insights, contributor-insights, pattern, anomaly
---

# CloudWatch Logs Insights Troubleshooter

## Activation

Activate this skill when the user reports a CloudWatch Logs Insights
problem. Trigger phrases: "Logs Insights no results", "Logs Insights
query timeout", "Logs Insights query cancelled", "Logs Insights
syntax error", "Contributor Insights not showing", "Contributor
Insights blank", "Logs Insights filter pattern not matching", "Logs
Insights pattern command", "Logs Insights anomaly detection", "metric
filter vs Logs Insights", "CloudWatch Logs query returns nothing".

## Mindset

**One-line takeaway:** every Logs Insights failure falls into one of
three buckets — the query is correct but scanning the wrong data
(no results), the query is correct but scanning too much data
(timeout), or the query itself is malformed (syntax error). Read the
query text, the time range, and the error message before declaring a
root cause.

Three facts make Logs Insights troubleshooting different from generic
query debugging:

- **Logs Insights queries are scoped to log groups, not log streams
  by default.** A query that returns no results is almost always
  pointing at the wrong log group, the wrong time range, or the wrong
  filter pattern. The log group ARN/name and the time window are the
  first two things to verify — before touching the query syntax.
- **Logs Insights has a query timeout tied to the volume of data
  scanned, not wall-clock time.** A query that works for 1 hour of
  logs may time out for 30 days of logs. The fix is always to reduce
  the data scanned: narrow the time range, push `filter` earlier in
  the pipeline, or use `stats` aggregation to collapse rows before
  `sort` / `limit`.
- **Contributor Insights and metric filters are SEPARATE features
  from Logs Insights.** They do not share syntax, they do not feed
  each other, and enabling one does not enable the others. A user who
  says "my Logs Insights query should show up in Contributor Insights"
  has a conceptual mismatch — this skill catches it.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| Query succeeds, 0 rows returned | NO_RESULTS | Verify log group name + time range vs ingestion window |
| Query status `Cancelled` or `Timeout` | TIMEOUT | Narrow time range; add early `filter`; use `stats` aggregation |
| Query status `Failed`; error mentions `Syntax` / `Parse` / `Unexpected` | SYNTAX_ERROR | Read the query line cited in the error; check `fields`/`filter`/`parse`/`stats` syntax |
| Contributor Insights tab empty for a log group | CONTRIBUTOR_INSIGHTS | `aws logs describe-contributor-insights`; check the rule exists and is ENABLED |
| "Metric filter" not producing expected data | METRIC_FILTER_CONFUSION | Determine whether the user means metric filter (emits metrics) or Logs Insights (query engine) |
| `pattern` / anomaly detection yields nothing or noise | PATTERN_ANOMALY | Verify log field extraction; check `parse` before `pattern`; verify anomaly baseline window |

## Quick navigation

- **Step 0** — Capture the failure signal (query text, log group, time range, error/result).
- **Step 1** — Map the symptom to a category letter (A-F).
- **Step 2** — NO_RESULTS diagnostic (zero rows).
- **Step 3** — TIMEOUT diagnostic (cancelled / timed-out query).
- **Step 4** — SYNTAX_ERROR diagnostic (fields, filter, parse, stats, sort, limit, display).
- **Step 5** — CONTRIBUTOR_INSIGHTS diagnostic (empty Contributor Insights).
- **Step 6** — METRIC_FILTER_CONFUSION diagnostic (metric filter vs Logs Insights).
- **Step 7** — PATTERN_ANOMALY diagnostic (pattern command + anomaly detection).
- **Step 8** — Root-cause catalog (top patterns + canonical fixes).
- **Step 9** — Verify the fix.
- **Step 10** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO / ESCALATE).

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these four pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Query text** | User-provided or console | Drives the syntax check and the data-scan estimate |
| **Log group name/ARN** | User-provided or `aws logs describe-log-groups` | Determines which data is scanned |
| **Time range** | User-provided or console selector | The most common no-results and timeout cause |
| **Error message or result** | Console, `get-query-results`, or `describe-queries` | Distinguishes no-results from timeout from syntax |

If the user has not provided the query text or log group, output:

```text
INCIDENT: <log-group> — <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the query text and the log group name.
MISSING:
  - The exact Logs Insights query text (fields / filter / stats / sort / limit lines)
  - The log group name or ARN being queried
  - The time range selected (relative or absolute start/end)
  - The observed result (0 rows, error message, timeout, partial results)
```

If the user reports "my query is broken" but does not know the query
text, ask for it. Then verify the log group exists:

```bash
# List log groups to confirm the name (and find the right one):
aws logs describe-log-groups \
  --log-group-name-prefix <prefix> \
  --query 'logGroups[*].{name:logGroupName,arn:arn,storedBytes:storedBytes,retention:retentionInDays}'

# Check recent ingestion (does the log group have data at all?):
aws logs describe-log-streams \
  --log-group-name <log-group> \
  --order-by LastEventTime \
  --descending \
  --limit 5 \
  --query 'logStreams[*].{name:logStreamName,lastEvent:lastIngestionTime,firstEvent:firstEventTimestamp}'
```

The `lastIngestionTime` confirms whether the log group has received
data recently. A log group with no recent streams will return no
results regardless of the query.

### Step 1: Identify the symptom category

Map the observed state to one of six categories.

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. NO_RESULTS** | Query status `Complete`, results array empty `[]` | Step 2 |
| **B. TIMEOUT** | Query status `Cancelled` or `Timeout`; console shows "Query timed out" or "Query cancelled" | Step 3 |
| **C. SYNTAX_ERROR** | Query status `Failed`; error contains `Syntax`, `Parse`, `Unexpected token`, `Unknown field`, `Invalid` | Step 4 |
| **D. CONTRIBUTOR_INSIGHTS** | Contributor Insights tab empty; `describe-contributor-insights` returns no rule or `DISABLED` | Step 5 |
| **E. METRIC_FILTER_CONFUSION** | User says "metric filter" or "filter" but expects query results, OR expects a metric but is using Logs Insights | Step 6 |
| **F. PATTERN_ANOMALY** | `pattern` command yields nothing / noise; anomaly detection baseline not forming | Step 7 |

**Earliest-blocker rule.** If the symptom matches more than one
category, pick the earliest blocker. A SYNTAX_ERROR prevents the
query from running at all, so it precedes NO_RESULTS and TIMEOUT.
METRIC_FILTER_CONFUSION is a conceptual mismatch that precedes all
query-level diagnosis — if the user is using the wrong feature,
fixing the query will not help.

### Step 2: NO_RESULTS diagnostic (query returns 0 rows)

A query that completes with zero rows means the query ran but matched
nothing. The cause is almost always one of: wrong log group, time
range outside the ingestion window, filter pattern too restrictive,
or field name mismatch (the `filter` references a field that does not
exist in the log payload).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| 0 rows; log group name is a substring or has a typo | Wrong log group — e.g. `/aws/lambda/myapi` vs `/aws/lambda/my-api-prod` | `aws logs describe-log-groups --log-group-name-prefix <prefix>`; compare exact names |
| 0 rows; time range is "last 5 min" but last ingestion was 2 hours ago | Time range outside ingestion window | `aws logs describe-log-streams --order-by LastEventTime --descending --limit 1`; compare `lastIngestionTime` to the query window |
| 0 rows; `filter` uses `like` or `=` on a field that is not extracted | Field name mismatch — raw JSON logs need the field to exist at the top level; embedded fields need `parse` first | Run the query with just `fields @timestamp, @message | limit 10` to see the raw payload; verify field names |
| 0 rows; `filter @message like /ERROR/` returns nothing but logs contain "error" (lowercase) | Case sensitivity — `like` with regex is case-sensitive by default | Use `filter @message like /(?i)error/` or `filter strcontains(@message, "error")` for case-insensitive |
| 0 rows; `filter level = "ERROR"` but the field is `levelname` not `level` | Field name typo | Inspect raw `@message` with a `fields @timestamp, @message | limit 5` query; cross-check field names |
| 0 rows on a specific log stream but works on others | Log stream-scoped query missing the stream | Logs Insights queries all streams by default; if the stream has no matching events, it returns nothing |

**Diagnostic walk:**

1. **Verify the log group exists and has data** in the queried time
   range. Use `describe-log-streams` with `--order-by LastEventTime
   --descending` and check `lastIngestionTime` falls within the query
   window.
2. **Run the simplest possible query first** to confirm the data is
   there: `fields @timestamp, @message | sort @timestamp desc | limit 10`.
   If this returns rows, the data exists and the problem is in the
   filter/aggregation. If 0 rows, the problem is the log group or
   time range.
3. **Inspect the raw payload** to verify field names. For JSON logs,
   Logs Insights auto-extracts top-level keys. For text logs, you must
   `parse` the `@message` field before filtering on parsed fields.
4. **Check filter case sensitivity.** The `like` operator with a
   regex is case-sensitive. Use `(?i)` in the regex or `strcontains`
   for case-insensitive substring matching.
5. **Check glob vs regex.** The `like` operator uses regex, not glob.
   `filter @message like "ERROR*"` treats `*` as a regex quantifier,
   not a wildcard. Use `/ERROR.*/` or `strcontains(@message, "ERROR")`.

**Diagnostic commands:**

```bash
# Confirm the log group exists and has recent data:
aws logs describe-log-groups \
  --log-group-name-prefix <prefix> \
  --query 'logGroups[*].{name:logGroupName,arn:arn,storedBytes:storedBytes}'

# Check the most recent ingestion timestamp:
aws logs describe-log-streams \
  --log-group-name <log-group> \
  --order-by LastEventTime \
  --descending \
  --limit 1 \
  --query 'logStreams[0].{stream:logStreamName,lastEvent:lastIngestionTime,firstEvent:firstEventTimestamp}'

# Start a minimal query to confirm data presence (1-minute window):
QUERY_ID=$(aws logs start-query \
  --log-group-name <log-group> \
  --start-time $(date -d '5 minutes ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | sort @timestamp desc | limit 10' \
  --query 'queryId')

# Poll for results:
aws logs get-query-results --query-id "$QUERY_ID"
```

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

### Step 3: TIMEOUT diagnostic (query cancelled or timed out)

A query that times out or is cancelled scanned too much data. Logs
Insights enforces a limit on the volume of data scanned per query.
The fix is always to reduce the data scanned — not to "make the query
faster."

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Query works for 1h but times out for 7d | Time range too wide for the query's data scan volume | Narrow the time range; run multiple smaller queries and union |
| Query times out; no `filter` before `stats` or `sort` | Missing early filter — the engine scans every event before aggregating | Add `filter` as the FIRST command after `fields` to eliminate non-matching events early |
| Query times out; `sort @timestamp desc | limit 1000` on a huge log group | Sort across the full dataset before limit | Use `stats` to aggregate first, then sort the aggregated results |
| Query times out; querying 50+ log groups at once | Too many log groups in one query | Split into per-log-group queries or use a log-group-prefix query if supported |
| Query times out; `parse` with a complex regex over millions of events | `parse` is expensive per event; applied before filtering | Move `filter` BEFORE `parse` so parse only runs on pre-filtered events |
| Query was running fine but now times out | Log volume spiked (new deployment, error storm) | Check ingestion volume via `get-metric-statistics` on `IncomingBytes`; narrow time range |

**The data-scan reduction hierarchy (apply in order):**

1. **Narrow the time range.** The single most effective fix. If the
   user needs 30 days of data, run 30 daily queries and concatenate.
2. **Push `filter` to the front.** Every command before `filter` runs
   on the full dataset. Moving `filter` to the first line reduces the
   data for all subsequent commands.
3. **Use `stats` aggregation early.** `stats count() by @logStream`
   collapses millions of events into a few rows. Sort and limit the
   aggregated results, not the raw events.
4. **Move `parse` after `filter`.** `parse` runs a regex per event.
   If you filter first, parse runs on fewer events.
5. **Reduce the number of log groups.** Querying across many log
   groups multiplies the scan. Split into per-group queries.

**Before-and-after example:**

```text
# BEFORE — times out (scans everything, sorts everything, then limits):
fields @timestamp, @message, level, service
| parse @message "* * * *" as timestamp, level, service, msg
| sort @timestamp desc
| limit 1000

# AFTER — completes in seconds (filter first, aggregate, sort last):
filter @message like /ERROR/
| parse @message "* * * *" as timestamp, level, service, msg
| stats count() as errorCount by service
| sort errorCount desc
| limit 20
```

**Diagnostic commands:**

```bash
# Check the status of the most recent queries (find timeouts):
aws logs describe-queries \
  --log-group-name <log-group> \
  --status Cancelled \
  --max-results 10 \
  --query 'queries[*].{id:queryId,status:status,created:createTime,queryString:queryString}'

# Also check Failed queries:
aws logs describe-queries \
  --log-group-name <log-group> \
  --status Failed \
  --max-results 10

# Check ingestion volume (is a spike causing the timeout?):
aws cloudwatch get-metric-statistics \
  --namespace AWS/Logs \
  --metric-name IncomingBytes \
  --dimensions Name=LogGroupName,Value=<log-group> \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Sum \
  --query 'Datapoints[*].{time:Timestamp,bytes:Sum}'
```

### Step 4: SYNTAX_ERROR diagnostic

Logs Insights uses a pipe-delimited query language. Syntax errors
typically involve quoting, the `stats` aggregation syntax, the
`parse` pattern, or the `sort`/`limit` placement.

| Error message sub-string | Root cause | Fix |
|---|---|---|
| `Unknown field` / `Field not found` | `fields` or `filter` references a field that does not exist | Inspect `@message` raw payload; use `parse` to extract; verify JSON keys are top-level |
| `Unexpected token` | Pipe placement wrong; command after a terminal command (`limit`) | `limit` must be LAST; `sort` before `limit`; `display` before `sort` |
| `Parse error` / `Invalid parse pattern` | `parse` pattern does not match the log format | Test the glob pattern against a sample `@message`; placeholders use `*` |
| `Syntax error in stats` | `stats` syntax wrong — missing `by`, missing aggregation function | `stats count() by field` or `stats avg(numericField) by field`; the aggregation function is required |
| `Invalid sort field` | `sort` on a field that does not exist or is not extracted | Sort on `@timestamp` or on a field produced by `stats` |
| `limit must be a positive integer` | `limit` value is 0, negative, or a string | Use `limit 100` (positive integer) |

**Command ordering rules (the most common syntax-error source):**

Logs Insights commands run left to right. The valid order is:

```text
fields <field-list>
| filter <condition>
| parse <pattern>
| stats <aggregation> by <group-key>
| sort <field> <asc|desc>
| display <field-list>
| limit <n>
```

- `fields` selects fields (optional; defaults to `@timestamp, @message`).
- `filter` must precede `stats`/`sort` for efficiency.
- `parse` extracts fields from `@message`; must precede any
  `filter`/`stats` referencing parsed fields.
- `stats` aggregates; output fields are the group key + alias.
- `sort` runs on `stats` output (or raw events if no `stats`).
- `display` reorders/renames columns; runs after `stats`.
- `limit` must be the LAST command.

**Common syntax-error patterns:**

```text
# WRONG — limit before sort:
fields @timestamp, @message | limit 10 | sort @timestamp desc
# RIGHT:
fields @timestamp, @message | sort @timestamp desc | limit 10

# WRONG — stats without aggregation function:
fields duration | stats by service
# RIGHT:
fields duration | stats avg(duration) as avgDuration by service

# WRONG — filter referencing a parsed field before parse:
filter parsedLevel = "ERROR" | parse @message "* *" as ts, parsedLevel
# RIGHT:
parse @message "* *" as ts, parsedLevel | filter parsedLevel = "ERROR"

# WRONG — regex in like without slashes:
filter @message like "ERROR\s\d+"
# RIGHT (regex must be in /.../):
filter @message like /ERROR\s\d+/

# WRONG — glob wildcard in like (treated as regex quantifier):
filter @message like "ERROR*"
# RIGHT (use regex .*) or use strcontains:
filter @message like /ERROR.*/  |  filter strcontains(@message, "ERROR")
```

**Diagnostic walk:**

1. **Read the exact error message.** Logs Insights reports the
   command and token where the error occurred.
2. **Check command ordering** against the valid order above.
3. **Check `stats` syntax** — needs an aggregation function (`count()`,
   `sum()`, `avg()`, `min()`, `max()`, `percentile(N, field)`).
4. **Check `parse` pattern** — placeholders are `*` (glob), not regex
   groups. Test against a sample `@message`.
5. **Check quoting** — string literals use double quotes; regex in
   `like` uses `/pattern/` slashes.
6. **Run a minimal query** (`fields @timestamp | limit 1`), then add
   commands back one at a time to isolate the error.

### Step 5: CONTRIBUTOR_INSIGHTS diagnostic (empty / blank)

Contributor Insights is a SEPARATE feature from Logs Insights. It
runs pre-defined rules that aggregate log data into top-N contributor
reports (top source IPs, top user agents, etc.). It does NOT use Logs
Insights query syntax, and enabling Logs Insights does NOT enable
Contributor Insights.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Contributor Insights tab empty; no rule exists | Rule not created | `aws logs describe-contributor-insights --log-group-name <lg>`; if empty, the rule was never created |
| Rule exists but status is `DISABLED` | Rule was disabled or failed to activate | `aws logs describe-contributor-insights`; check `status` field |
| Rule exists and `ENABLED` but no data | Rule's `logGroupArn` points at wrong log group; or log format changed | Verify the rule's `logGroupArn` matches; verify the log payload still matches the rule's schema |
| Rule works for one log group but not another | Each log group needs its OWN Contributor Insights rule | Create a rule per log group; rules do not cascade |
| User expects Logs Insights query to populate Contributor Insights | Conceptual mismatch — Logs Insights and Contributor Insights are independent | Clarify the two features; create a Contributor Insights rule separately |

**Diagnostic commands:**

```bash
# Check if a Contributor Insights rule exists and its status:
aws logs describe-contributor-insights \
  --log-group-name <log-group> \
  --query '{status: status, ruleName: contributionLogGroupMetrics[0].name}'

# List ALL Contributor Insights rules (find a missing one):
aws logs describe-contributor-insights

# Create a rule (if missing):
aws logs put-insight-rule \
  --rule-name my-rule \
  --rule-state Enabled \
  --rule-definition '{"Schema":{"Name":"ContributorInsights","Version":1},"LogGroupNames":["<log-group>"],"LogFormat":"JSON","Fields":["sourceIp","userAgent"]}'
```

**Common fix patterns:**

- **No rule exists:** create one via `put-insight-rule`. Each log group
  needs its own rule.
- **Rule is `DISABLED`:** re-enable with `--rule-state Enabled`.
- **Wrong log group:** the `LogGroupNames` array must include the exact
  log group name.
- **Log format changed:** update the rule's `LogFormat` (`JSON` vs
  `CLF`/custom) if the app switched log formats.

### Step 6: METRIC_FILTER_CONFUSION diagnostic

Metric filters and Logs Insights are different features with different
purposes:

| Feature | Purpose | Output | Syntax |
|---|---|---|---|
| **Metric filter** | Emits a CloudWatch metric based on log patterns | A time-series metric (numeric) | Filter pattern (JSON token matching or space-delimited) |
| **Logs Insights** | Interactive query of log data | Tabular results (rows + columns) | Pipe-delimited query language (fields, filter, stats, sort, limit) |
| **Contributor Insights** | Top-N contributor aggregation | Top contributor report | Rule-based (JSON schema) |

| Sub-symptom | Root cause | Fix |
|---|---|---|
| User says "my metric filter query returns nothing" but pastes a Logs Insights query | Using Logs Insights syntax in a metric filter context | Metric filters use filter-pattern syntax, not Logs Insights pipe syntax |
| User expects a metric alarm but is running Logs Insights | Logs Insights does not emit metrics; metric filters do | Create a metric filter with the right filter pattern; set an alarm on the emitted metric |
| User has a metric filter but sees no metric data | Filter pattern does not match log format, or metric namespace/name is wrong | Test the filter pattern with `test-metric-filter`; verify the metric namespace and name |
| User pastes a JSON token filter pattern into Logs Insights | JSON token patterns are metric-filter syntax, not Logs Insights | Convert to Logs Insights `filter` syntax |

**Diagnostic commands:**

```bash
# List metric filters for a log group:
aws logs describe-metric-filters \
  --log-group-name <log-group> \
  --query 'metricFilters[*].{name:filterName,pattern:filterPattern,namespace:metricTransformations[0].metricNamespace}'

# Test a metric filter pattern against sample log data:
aws logs test-metric-filter \
  --filter-pattern '{ $.level = "ERROR" }' \
  --log-event-messages '{"level":"ERROR","msg":"disk full"}'
```

**Common fix patterns:** use metric filters for metrics + alarms, Logs
Insights for ad-hoc queries. Test patterns with `test-metric-filter`.
Verify the alarm references the same namespace and metric name as the
filter's `metricTransformations`.

### Step 7: PATTERN_ANOMALY diagnostic (pattern command + anomaly detection)

The `pattern` command auto-detects patterns in log data by clustering
similar log events. Anomaly detection identifies unusual log volume or
content patterns.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `pattern` command returns nothing | No data in the time range, or `parse` before `pattern` consumed the `@message` | Run `fields @timestamp, @message | limit 5` first; ensure `@message` is available to `pattern` |
| `pattern` returns too many patterns (noise) | Time range too wide; too many unique messages | Narrow the time range; add a `filter` before `pattern` to focus on a subset |
| `pattern` groups unrelated logs together | Pattern detection threshold too coarse | Provide fewer fields to `pattern`; use `parse` to extract key fields before `pattern` |
| Anomaly detection shows no anomalies | Baseline window too short (needs sufficient data) | Anomaly detection requires a baseline; widen the time range to build a baseline |
| Anomaly detection shows everything as anomalous | Baseline window includes the anomaly itself | Use a longer time range so the anomaly is a small portion of the baseline |

**`pattern` command usage:**

```text
# Auto-detect patterns in raw log messages:
fields @timestamp, @message
| pattern @message
| limit 20

# Pattern detection with a filter (recommended):
filter level = "ERROR"
| pattern @message
| display @pattern, @sampleCount, @representation
| limit 20
```

The `pattern` command outputs `@pattern` (detected pattern with
wildcards), `@sampleCount` (number of matching events), and
`@representation` (a sample log line). If `pattern` returns nothing,
ensure `@message` is available — a prior `parse` may have consumed it.

**Anomaly detection** relies on `stats count()` over time bins. The
console's anomaly view compares recent volumes to the historical
baseline. To troubleshoot: (1) verify the grouping field exists (use
`parse` if needed), (2) verify `bin(5m)` is appropriate — too small
creates noise, too large hides anomalies, (3) ensure 2+ weeks of data
for a stable baseline.

### Step 8: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Wrong log group name (typo, wrong environment, wrong prefix) | NO_RESULTS | Correct the log group name; verify with `describe-log-groups` |
| 2 | Time range outside the ingestion window | NO_RESULTS | Widen the time range; verify `lastIngestionTime` with `describe-log-streams` |
| 3 | Filter pattern case-sensitive (`like` with regex) | NO_RESULTS | Use `(?i)` in regex or `strcontains` for case-insensitive matching |
| 4 | Filter references a field that is not extracted (no `parse`) | NO_RESULTS | Add `parse` before `filter`; verify field names against raw `@message` |
| 5 | Query scans too much data (wide time range, no early filter, sort before limit) | TIMEOUT | Narrow time range; push `filter` first; use `stats` aggregation before `sort` |
| 6 | `parse` runs before `filter` (expensive regex on full dataset) | TIMEOUT | Move `filter` before `parse` so parse runs on fewer events |
| 7 | Command ordering error (`limit` before `sort`, `sort` before `stats`) | SYNTAX_ERROR | Follow the valid command order: fields, filter, parse, stats, sort, display, limit |
| 8 | `stats` without aggregation function | SYNTAX_ERROR | Add aggregation function: `stats count() by field` or `stats avg(x) by field` |
| 9 | Contributor Insights rule not created for the log group | CONTRIBUTOR_INSIGHTS | Create a rule via `put-insight-rule`; one rule per log group |
| 10 | Using Logs Insights syntax in a metric filter context (or vice versa) | METRIC_FILTER_CONFUSION | Clarify the feature; use metric-filter pattern syntax for filters, Logs Insights for queries |
| 11 | `pattern` command has no `@message` to cluster (consumed by prior `parse`) | PATTERN_ANOMALY | Ensure `@message` is available; run `pattern` before `parse` or re-include `@message` in `fields` |

### Step 9: Verify the fix

Before declaring ROOT_CAUSE_FOUND, validate the proposed fix:

- **For NO_RESULTS:** run the minimal query
  (`fields @timestamp, @message | limit 10`) and confirm rows appear.
  Then add the original filter back and confirm rows still appear.
- **For TIMEOUT:** run the optimized query with the narrowed time
  range and confirm it completes. Then gradually widen the range to
  find the practical limit.
- **For SYNTAX_ERROR:** run the corrected query in the console or via
  `start-query` and confirm status `Complete` with results.
- **For CONTRIBUTOR_INSIGHTS:** run `describe-contributor-insights`
  and confirm status `ENABLED`; wait 5-10 minutes for data to appear.
- **For METRIC_FILTER_CONFUSION:** confirm the user understands which
  feature they need; test with `test-metric-filter`.

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category
  and a specific query element or configuration issue. Output
  REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where evidence is
  unavailable (e.g., the user did not paste the query text, or the
  log group name is ambiguous). Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: IAM permissions preventing `start-query`, a log group in
  another account, or a Logs Insights service-level issue. Output the
  escalation target and the specific request.

## STRICT output contract

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

### Worked example — NO_RESULTS from wrong log group

```text
INCIDENT: /aws/lambda/my-api — query returns 0 rows
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: NO_RESULTS — querying /aws/lambda/my-api but the actual
log group is /aws/lambda/my-api-prod; describe-log-groups shows both
exist but only -prod has recent ingestion
EVIDENCE:
  - Query: fields @timestamp, @message | filter @message like /ERROR/
    | limit 100
  - Time range: last 15 minutes
  - describe-log-streams on /aws/lambda/my-api: lastIngestionTime is
    2025-03-01 (stale — no recent data)
  - describe-log-streams on /aws/lambda/my-api-prod:
    lastIngestionTime is 2 minutes ago (active)
ROOT_CAUSE_CATALOG: #1 (wrong log group)
REMEDIATION:
  1. Switch the query to /aws/lambda/my-api-prod.
  2. Verify data with: fields @timestamp, @message | limit 5
  3. Re-apply the filter: fields @timestamp, @message | filter
     @message like /ERROR/ | limit 100
```

## Expert heuristic — "Filter early, aggregate early, sort last"

Three rules, in order, eliminate 90% of Logs Insights failures:

1. **Filter early.** The first pipe after `fields` should be `filter`.
   Every event eliminated by the filter is an event that `parse`,
   `stats`, and `sort` do not have to touch. A query that scans 10M
   events with `filter` first may process 10K events through the rest
   of the pipeline.
2. **Aggregate early.** `stats count() by field` collapses millions of
   raw events into a small number of grouped rows. Sort and limit the
   aggregated output, not the raw events. A `sort @timestamp desc |
   limit 100` on raw events must materialise the full sorted order
   before truncating; `stats ... | sort ... | limit` sorts a handful
   of rows.
3. **Sort last.** `sort` is the most expensive command on large
   datasets because it must hold all rows in memory to establish the
   order. If you `stats` first, `sort` runs on the aggregated output
   (tens or hundreds of rows) instead of the raw events (millions).

If a query times out, apply these three rules before trying anything
else. They are the single most effective fix.

## Anti-Patterns — NEVER

- **NEVER** declare the root cause without verifying the log group
  has data in the queried time range. A stale log group
  (`lastIngestionTime` hours or days ago) returns 0 rows for any
  query. Always run `describe-log-streams --order-by LastEventTime`
  first.

- **NEVER** use glob wildcards (`*`, `?`) in the `like` operator.
  `like` uses regular expressions; `*` is a regex quantifier that
  means "zero or more of the preceding character." Use `.*` for
  "any characters" or use `strcontains(@message, "substring")` for
  literal substring matching.

- **NEVER** put `limit` before `sort`. Logs Insights runs commands
  left to right; `limit` before `sort` truncates before sorting,
  producing a random (not sorted) subset. `sort` must precede
  `limit`.

- **NEVER** confuse Contributor Insights with Logs Insights.
  Contributor Insights uses pre-defined rules
  (`put-insight-rule`), not Logs Insights queries. Enabling Logs
  Insights does NOT enable Contributor Insights. Each log group
  needs its own Contributor Insights rule.

- **NEVER** run `parse` before `filter` on a large dataset. `parse`
  applies a regex to every event. If you filter first, `parse` runs
  on the filtered subset, dramatically reducing the work. The only
  exception is when the `filter` condition depends on a field that
  `parse` extracts — in that case, accept the cost but narrow the
  time range to compensate.

- **NEVER** use `stats` without an aggregation function.
  `stats by field` is invalid syntax; it must be
  `stats count() by field` or `stats avg(x) by field`. The
  aggregation function is mandatory.

- **NEVER** assume metric filters and Logs Insights share syntax.
  Metric filters use JSON token patterns (`{ $.level = "ERROR" }`)
  or space-delimited patterns. Logs Insights uses pipe-delimited
  query syntax (`filter level = "ERROR"`). Pasting one into the
  other produces errors or no results.

- **NEVER** widen the time range to "fix" a NO_RESULTS problem
  without first confirming the log group has data. If the log group
  is stale (no recent ingestion), widening the range will still
  return nothing.

## Recent AWS features (2024-2026)

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

## References

See `references/query-syntax-reference.md` for the full Logs Insights
command reference (fields, filter, parse, stats, sort, display, limit,
pattern) with syntax diagrams and examples, and
`references/diagnostic-decision-tree.md` for the complete
symptom-to-cause walk with worked examples per category.

## Domain

AWS CloudOps / CloudWatch Logs Observability.

## AWS documentation

- **CloudWatch Logs Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html
- **Logs Insights query syntax** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html
- **Contributor Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/ContributorInsights.html
- **Metric filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
- **CloudWatch Logs anomaly detection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html
- **start-query API** — https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_StartQuery.html
- **get-query-results API** — https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_GetQueryResults.html
- **put-insight-rule API** — https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutInsightRule.html
