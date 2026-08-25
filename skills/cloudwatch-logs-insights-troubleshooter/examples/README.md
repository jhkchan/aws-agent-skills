# End-to-end usage scenario: cloudwatch-logs-insights-troubleshooter

A walkthrough showing the skill diagnosing a Logs Insights query that
returns no results due to a wrong log group name. This exercises Step 1
(symptom identification), Step 2 (NO_RESULTS), and the remediation
workflow.

## Input (user prompt)

> My Logs Insights query on `/aws/lambda/my-api` returns 0 rows. The
> query is `fields @timestamp, @message | filter @message like /ERROR/
> | limit 100` with a 15-minute time range. My app is running and
> logging errors. `describe-log-streams` on `my-api` shows
> `lastIngestionTime` from months ago, but `describe-log-groups` shows
> `/aws/lambda/my-api-prod` exists with recent data.

## Skill output

```text
INCIDENT: /aws/lambda/my-api — query returns 0 rows
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: NO_RESULTS — querying /aws/lambda/my-api but the actual
log group is /aws/lambda/my-api-prod; my-api has stale data
(lastIngestionTime months ago)
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

## What the skill caught that a generic assistant misses

1. **The stale `lastIngestionTime` signal.** A generic assistant
   guesses "maybe your app isn't logging" or "try a wider time range."
   The skill reads `describe-log-streams` and sees the log group has
   no recent data — the problem is the log group, not the query.

2. **The similar-name disambiguation.** A generic assistant does not
   check for similarly-named log groups. The skill runs
   `describe-log-groups` with a prefix and identifies
   `/aws/lambda/my-api-prod` as the active group.

3. **The verification-first remediation.** A generic assistant jumps
   to "just change the log group." The skill prescribes verifying data
   presence first (`fields @timestamp, @message | limit 5`), then
   re-applying the filter — so the user confirms data exists before
   adding complexity.

## Slash-command invocation

```
/aws:troubleshoot-cloudwatch-logs-insights
```

Or via the orchestrator:

```
/aws:pipeline
You: "Logs Insights query on my-api returns nothing, but the app is logging errors"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudwatch-logs-insights-troubleshooter]` and hands off to this skill
for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has AWS credentials:

```bash
# Confirm the log group exists and check recent ingestion.
aws logs describe-log-streams \
  --log-group-name /aws/lambda/my-api \
  --order-by LastEventTime \
  --descending \
  --limit 1

# Check for similarly-named log groups.
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/my-api

# Start a minimal query on the correct log group.
QUERY_ID=$(aws logs start-query \
  --log-group-name /aws/lambda/my-api-prod \
  --start-time $(date -d '15 minutes ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | limit 5' \
  --query 'queryId')

aws logs get-query-results --query-id "$QUERY_ID"
```

The stale `lastIngestionTime` plus the active `-prod` log group
confirms the diagnosis without needing to inspect the query syntax.
