# CloudWatch Logs Insights Query Syntax — Reference

Supplementary reference for the CloudWatch Logs Insights Troubleshooter
skill. The canonical command reference with syntax diagrams, supported
operators, and examples per command.

## Supported commands (valid order)

Logs Insights commands run left to right in a pipe-delimited chain.
The valid ordering is:

```text
fields <field-list>
| filter <condition>
| parse <pattern>
| stats <aggregation> by <group-key>
| sort <field> <asc|desc>
| display <field-list>
| limit <n>
```

## fields

Selects which fields to include in the output. Optional — defaults to
`@timestamp` and `@message`.

```text
fields @timestamp, @message, level, requestId
```

### Special fields

- `@timestamp` — event timestamp
- `@message` — raw log event
- `@logStream` — log stream name
- `@log` — log group ARN

For JSON logs, top-level keys are auto-extracted as fields.

## filter

Filters events by a condition. Supports comparison operators (`=`,
`!=`, `<`, `>`, `<=`, `>=`), boolean operators (`and`, `or`, `not`),
and the `like` operator (regex).

```text
# Equality
filter level = "ERROR"

# Boolean
filter level = "ERROR" and service = "api"

# Regex (case-sensitive by default)
filter @message like /ERROR/

# Case-insensitive regex
filter @message like /(?i)error/

# Substring (case-insensitive)
filter strcontains(@message, "error")

# Numeric comparison
filter duration > 1000

# Field presence
filter ispresent(requestId)
```

### Glob vs regex

The `like` operator uses **regex**, not glob. `*` is a regex
quantifier meaning "zero or more of the preceding character."

```text
# WRONG — * is a regex quantifier:
filter @message like "ERROR*"

# RIGHT — .* means "any characters":
filter @message like /ERROR.*/

# RIGHT — literal substring:
filter strcontains(@message, "ERROR")
```

## parse

Extracts fields from `@message` using a glob-like pattern with `*`
placeholders.

```text
parse @message "* * * *" as timestamp, level, message
```

Each `*` captures a token (whitespace-delimited). For more complex
extraction, use a regex pattern:

```text
parse @message /\[(?<level>\w+)\]\s+(?<msg>.*)/
```

**Important:** `parse` must come before any `filter` or `stats` that
references the parsed fields.

## stats

Aggregates events. Requires an aggregation function.

```text
# Count by field
stats count() as eventCount by level

# Average
stats avg(duration) as avgDuration by service

# Percentile
stats pct(95, duration) as p95Duration by service

# Min / Max
stats min(duration) as minDur, max(duration) as maxDur by service

# Sum
stats sum(bytes) as totalBytes by @logStream

# Time-binned aggregation
stats count() by bin(5m)
```

### Supported aggregation functions

| Function | Description |
|---|---|
| `count()` | Count of events |
| `sum(field)` | Sum of numeric field |
| `avg(field)` | Average of numeric field |
| `min(field)` | Minimum value |
| `max(field)` | Maximum value |
| `pct(N, field)` | Nth percentile |
| `distinct_count(field)` | Count of distinct values |

### `stats` without aggregation is invalid

```text
# WRONG:
stats by service

# RIGHT:
stats count() by service
```

## sort

Sorts results. Must come after `stats` (if present) and before `limit`.

```text
sort @timestamp desc
sort eventCount desc
```

## display

Renames or reorders output columns. Runs after `stats`.

```text
display @timestamp, level as LogLevel, eventCount as Count
```

## limit

Truncates results. Must be the LAST command.

```text
limit 100
limit 20
```

## pattern

Auto-detects and clusters log patterns. Outputs `@pattern`,
`@sampleCount`, and `@representation`.

```text
fields @timestamp, @message
| pattern @message
| limit 20
```

## Common pitfalls

1. **`limit` before `sort`** — truncates before sorting, producing a
   random subset.
2. **`stats` without aggregation function** — syntax error.
3. **`filter` referencing parsed field before `parse`** — field does
   not exist yet.
4. **Glob `*` in `like`** — treated as regex quantifier, not wildcard.
5. **`parse` before `filter` on large datasets** — expensive regex on
   every event.
