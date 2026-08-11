# Eval prompt: cur-athena-top-spenders-scheduled

Design an automated CUR Athena top-spenders workflow. Emit the
standard design block (DETECTION_SOURCE, RESPONSE_SCOPE, VERDICT,
WORKFLOW, GUARDRAILS, AUDIT, FINDINGS, REMEDIATION).

Scenario: cur-athena-top-spenders-scheduled

Detection source: CUR (Cost and Usage Report)
Response scope: cur-analysis (top-spenders drill-down)
CUR: parquet format (CUR 2.0), daily delivery, partitions loaded
  (MSCK REPAIR run weekly)
Athena database: cur, table: cur_table
Athena results bucket: s3://cur-athena-results-us-east-1/
EventBridge schedule: cron(0 12 * * ? *) (daily 12:00 UTC)
Lambda: cur-top-spenders (start-query-execution, fetch results,
  format Slack message, post to webhook)
Kill-switch: Parameter Store /cost/kill-switch (enabled)
IAM: Lambda scoped to athena:StartQueryExecution,
  athena:GetQueryResults, s3:GetObject on results bucket,
  ssm:GetParameter on /cost/slack-webhook
Dry-run: completed 14 days
Idempotency: query deduped by execution ID
