# CloudWatch Logs Insights Diagnostic Decision Tree — Reference

Supplementary reference for the CloudWatch Logs Insights Troubleshooter
skill. The complete symptom-to-cause walk with worked examples per
category.

## Category A: NO_RESULTS

### A1: Wrong log group name

**Symptom:** Query completes with 0 rows.

**Decision:**
1. Does the log group name match exactly?
2. Does `describe-log-groups` show a similar name (typo)?
3. Does `describe-log-streams` show recent `lastIngestionTime`?

**Worked example:** User queries `/aws/lambda/my-api` but the actual
group is `/aws/lambda/my-api-prod`. `describe-log-streams` on
`my-api` shows `lastIngestionTime` from months ago; `my-api-prod` shows
ingestion 2 minutes ago.

**Fix:** Switch the query to the correct log group name.

### A2: Time range outside ingestion window

**Symptom:** Query completes with 0 rows; log group has data but not
in the queried window.

**Decision:** Check `lastIngestionTime` vs the query time range.

**Worked example:** User queries "last 5 minutes" but the application
was redeployed 1 hour ago and has not received traffic since.

**Fix:** Widen the time range or confirm the app is emitting logs.

### A3: Filter case sensitivity

**Symptom:** Query returns 0 rows; logs contain the keyword in a
different case.

**Worked example:** `filter @message like /ERROR/` returns nothing but
logs contain "error" (lowercase).

**Fix:** Use `filter @message like /(?i)error/` or
`filter strcontains(@message, "error")`.

### A4: Field not extracted

**Symptom:** `filter level = "ERROR"` returns 0 rows because `level`
is not a top-level JSON key; it is embedded in a text `@message`.

**Fix:** Add `parse @message "* *" as ts, level` before the filter.

## Category B: TIMEOUT

### B1: No early filter

**Symptom:** Query cancelled after scanning a large volume of data.

**Worked example:**
```text
fields @timestamp, level, msg
| parse @message "* * *" as ts, level, msg
| sort @timestamp desc
| limit 1000
```
7-day time range, 50 GB/day ingestion = 350 GB scanned.

**Fix:** Push `filter` first, move `parse` after filter, use `stats`
before `sort`:
```text
filter @message like /ERROR/
| parse @message "* * *" as ts, level, msg
| stats count() as errorCount by level
| sort errorCount desc
| limit 20
```

### B2: Sort before aggregation

**Symptom:** `sort @timestamp desc | limit 100` on raw events times
out because the engine must sort millions of rows.

**Fix:** `stats count() by bin(5m) | sort @timestamp desc | limit 100`.

## Category C: SYNTAX_ERROR

### C1: Limit before sort

**Symptom:** Query succeeds but results are not sorted.

**Fix:** Move `limit` to the last position.

### C2: Stats without aggregation

**Symptom:** `Syntax error in stats`.

**Fix:** Add `count()`, `avg()`, `sum()`, etc.

### C3: Parse after filter referencing parsed field

**Symptom:** `Unknown field` error.

**Fix:** Move `parse` before `filter`.

## Category D: CONTRIBUTOR_INSIGHTS

### D1: No rule created

**Symptom:** Contributor Insights tab is empty.

**Decision:** `aws logs describe-contributor-insights --log-group-name
<lg>` returns no rule.

**Fix:** Create a rule with `put-insight-rule`.

### D2: Rule disabled

**Symptom:** Rule exists but tab is empty.

**Decision:** Status is `DISABLED`.

**Fix:** Re-enable with `--rule-state Enabled`.

## Category E: METRIC_FILTER_CONFUSION

### E1: Logs Insights syntax in metric filter

**Symptom:** User pastes `filter level = "ERROR"` into a metric filter
creation form.

**Fix:** Metric filters use JSON token patterns:
`{ $.level = "ERROR" }`, not Logs Insights pipe syntax.

### E2: Expecting metrics from Logs Insights

**Symptom:** User runs a Logs Insights query and expects a metric
alarm.

**Fix:** Create a metric filter (not Logs Insights) to emit a metric,
then set an alarm on that metric.

## Category F: PATTERN_ANOMALY

### F1: Pattern returns nothing

**Symptom:** `pattern @message` returns 0 patterns.

**Decision:** A prior `parse` may have consumed `@message`. Or no data
in the time range.

**Fix:** Ensure `@message` is available: `fields @timestamp, @message
| pattern @message | limit 20`.

### F2: Anomaly baseline too short

**Symptom:** Anomaly detection shows no anomalies or everything as
anomalous.

**Fix:** Use 2+ weeks of data for a stable baseline.
