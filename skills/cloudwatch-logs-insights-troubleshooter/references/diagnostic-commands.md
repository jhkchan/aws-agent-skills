# Diagnostic Commands (load on demand) — CloudWatch Logs Insights Troubleshooter

Diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0 — verify the log group exists and has data (moved from SKILL.md)

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
---

## Step 2 — NO_RESULTS diagnostic commands (moved from SKILL.md)

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
---

## Step 3 — TIMEOUT diagnostic commands (moved from SKILL.md)

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
---

## Step 5 — CONTRIBUTOR_INSIGHTS diagnostic commands (moved from SKILL.md)

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
---

## Step 6 — METRIC_FILTER_CONFUSION diagnostic commands (moved from SKILL.md)

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
