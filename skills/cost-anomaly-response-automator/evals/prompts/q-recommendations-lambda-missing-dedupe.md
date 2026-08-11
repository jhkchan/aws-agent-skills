# Eval prompt: q-recommendations-lambda-missing-dedupe

Validate the existing Cost Optimization Hub polling Lambda against the
mandatory guardrails. Emit the standard validation block
(DETECTION_SOURCE, RESPONSE_SCOPE, VERDICT, WORKFLOW, GUARDRAILS,
AUDIT, FINDINGS, REMEDIATION).

Scenario: q-recommendations-lambda-missing-dedupe

Detection source: q-recommendations (Cost Optimization Hub)
Response scope: notify (Slack)
Schedule: EventBridge cron(0 9 * * ? *) (daily 09:00 UTC)
Lambda: cost-hub-poller (calls get-recommendations, formats,
  posts to Slack)
The Lambda does NOT track last-seen recommendationId.
Last 7 days of Slack: same EC2 rightsize recommendation posted
  every day.
Kill-switch: Parameter Store /cost/kill-switch (enabled)
IAM: Lambda scoped to cost-optimization-hub:GetRecommendations,
  ssm:GetParameter on /cost/slack-webhook
Dry-run: never run (deployed straight to live).
