# Eval prompt: insufficient-context-no-query

Diagnose the following CloudWatch Logs Insights failure. The user
reports a problem but has not provided enough information to diagnose.

## Scenario

A user reports: "my CloudWatch Logs query is broken and returns
nothing."

## Known facts

- The user has not provided:
  - The query text
  - The log group name
  - The time range
  - The error message or result status
- No `describe-log-groups` or `describe-log-streams` output has been
  shared
- No console screenshot has been shared

## Symptom

The user's report is too vague to begin diagnosis. There is no query
text, no log group name, and no error message to work from.
