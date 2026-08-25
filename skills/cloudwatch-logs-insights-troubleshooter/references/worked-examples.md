# Worked Examples (load on demand) — CloudWatch Logs Insights Troubleshooter

Secondary worked examples moved verbatim from SKILL.md; the primary worked example (NO_RESULTS from wrong log group) remains inline in SKILL.md. Loaded on demand.

---

## Step 3 — before-and-after timeout example (moved from SKILL.md)

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
---

## Step 4 — common syntax-error patterns, WRONG vs RIGHT (moved from SKILL.md)

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
---

## Step 7 — `pattern` command usage (moved from SKILL.md)

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
