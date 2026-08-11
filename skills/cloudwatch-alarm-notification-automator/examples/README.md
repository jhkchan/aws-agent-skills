# End-to-end usage scenario: cloudwatch-alarm-notification-automator

A walkthrough showing the skill designing three workflows: (1) an
SNS-to-Lambda fan-out delivering to Slack + PagerDuty, (2) an
alarm-to-Jira ticket automation, and (3) a 2024-2026 native-surface
design using AWS User Notifications + Amazon Q. Each path includes
the pre-flight gate, the safety baseline, and the deterministic
VERDICT block — and is contrasted with the MANUAL_STEP_REQUIRED case
where a broken subscription is caught before relying on the workflow.

## Input (user prompt)

> Wire the prod-checkout-critical-rollup composite alarm to Slack
> #ops-alerts and PagerDuty service PXYZ. Then add a Jira ticket
> automation for the same composite. Then validate an existing
> alarm-to-Slack workflow that on-call reports as broken (alarms fire
> but Slack is silent). Finally, design a greenfield deployment using
> AWS User Notifications + Amazon Q (no Lambda).

```json
{
  "Design": "Multi-surface alarm notification for prod-checkout",
  "Region": "us-east-1",
  "Account": "111111111111",
  "SourceComposite": {
    "alarmName": "prod-checkout-critical-rollup",
    "alarmRule": "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)"
  }
}
```

## Skill output — SNS-to-Lambda Slack + PagerDuty (AUTOMATED)

```text
NOTIFICATION_SOURCE: prod-checkout-critical-rollup (composite)
SCOPE: Slack #ops-alerts + PagerDuty service PXYZ, 1-tier
VERDICT: AUTOMATED
WORKFLOW:
  EventBridge rule: alarm-state-change-to-sns
  SNS topic: arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout
  Lambda forwarder(s): alarm-slack-forwarder, alarm-pagerduty-forwarder
  Subscription status: confirmed (2 Lambda subscriptions, both active)
  Escalation state machine: N/A (1-tier)
  Ticket integration: N/A
  AWS User Notifications hub: N/A
SAFETY:
  - [PASS] Kill-switch: Parameter Store /notifications/kill-switch (checked first in both Lambdas)
  - [PASS] Both Lambda subscriptions confirmed (SubscriptionArn populated)
  - [PASS] Test publish delivered to Slack and PagerDuty within 12s
  - [PASS] Lambda IAM scoped to ssm:GetParameter on /slack/*, /pagerduty/*
  - [PASS] Slack webhook in Parameter Store /slack/critical-webhook (encrypted)
  - [PASS] PagerDuty routing key in Parameter Store /pagerduty/integration-key (encrypted)
  - [PASS] Composite rollup deduplicates 3 child alarms (flap-safe)
FINDINGS:
  - [INFO] Composite OR rule covers alb-error-ratio-prod, alb-latency-anomaly-prod, lambda-errors-high-prod-checkout
  - [INFO] PagerDuty dedup_key = AlarmName:Region for auto-resolve
  - [WARN] AWS User Notifications hub also configured — may double-notify if Chatbot subscribes to the same topic
REMEDIATION: Deploy via CloudFormation:
  aws cloudformation deploy --stack-name prod-alarm-notifications \
    --template-file alarm-notifications.yaml \
    --capabilities CAPABILITY_NAMED_IAM
```

## Skill output — alarm-to-Jira ticket (AUTOMATED)

```text
NOTIFICATION_SOURCE: prod-checkout-critical-rollup (composite)
SCOPE: Jira project OPS, Incident issue type, auto-create on ALARM + auto-resolve on OK
VERDICT: AUTOMATED
WORKFLOW:
  EventBridge rule: alarm-state-change-to-jira (state ENABLED, pattern matches ALARM + OK transitions)
  SNS topic: N/A (direct EventBridge -> Lambda)
  Lambda forwarder(s): alarm-jira-creator
  Subscription status: confirmed (lambda:add-permission for events.amazonaws.com present)
  Ticket integration: Jira project OPS, Incident issue type, dedup via DynamoDB alarm-ticket-map
SAFETY:
  - [PASS] Kill-switch: Parameter Store /notifications/kill-switch (checked first in Lambda)
  - [PASS] EventBridge -> Lambda invoke permission present
  - [PASS] Jira API token in Parameter Store /jira/api-token (encrypted)
  - [PASS] Idempotency: DynamoDB alarm-ticket-map keyed by alarmName; duplicate alarm events within 5 min suppressed
  - [PASS] Auto-resolve: OK transition triggers Jira transition to Resolved (state=31)
FINDINGS:
  - [INFO] DynamoDB TTL set to 30 days on alarm-ticket-map to expire resolved tickets
  - [WARN] Jira transition ID 31 (Resolved) is project-specific; verify in the OPS project workflow editor
REMEDIATION: Deploy via CloudFormation:
  aws cloudformation deploy --stack-name prod-alarm-jira \
    --template-file alarm-jira.yaml \
    --capabilities CAPABILITY_NAMED_IAM
```

## Skill output — broken subscription validation (MANUAL_STEP_REQUIRED)

```text
NOTIFICATION_SOURCE: api-error-rate-prod (via existing alarm-to-Slack workflow)
SCOPE: Slack #ops-alerts (validation mode)
VERDICT: MANUAL_STEP_REQUIRED
WORKFLOW:
  EventBridge rule: alarm-state-change-to-sns (state ENABLED)
  SNS topic: arn:aws:sns:us-east-1:111111111111:critical-notifications-api
  Lambda forwarder(s): alarm-slack-forwarder
  Subscription status: PENDING (Lambda subscription added but lambda:add-permission missing)
SAFETY:
  - [PASS] Kill-switch implemented
  - [FAIL] Subscription NOT functional: lambda:add-permission for AllowSNSInvoke missing. SNS cannot invoke the Lambda.
  - [PASS] Lambda IAM least-privilege
  - [PASS] Secrets in Parameter Store
FINDINGS:
  - [CRITICAL] SNS topic -> Lambda subscription is broken: the Lambda resource policy does not grant sns.amazonaws.com lambda:InvokeFunction for this topic ARN. The alarm fires, SNS publishes, but the Lambda is never invoked. This is the silent-drop failure mode — the #1 root cause of "the alarm was firing but nobody was paged."
  - [HIGH] Test publish was never run after the subscription was added.
  - [HIGH] NumberOfNotificationsFailed = 1 on the test publish, CloudWatch Logs show no Lambda invocations
REMEDIATION:
  1. aws lambda add-permission --function-name alarm-slack-forwarder --statement-id AllowSNSInvoke --action lambda:InvokeFunction --principal sns.amazonaws.com --source-arn arn:aws:sns:us-east-1:111111111111:critical-notifications-api
  2. aws sns publish --topic-arn arn:aws:sns:us-east-1:111111111111:critical-notifications-api --message '{"AlarmName":"test-alarm","NewStateValue":"ALARM","NewStateReason":"Manual test publish"}' --subject "TEST after fix"
  3. Verify the test message appears in Slack #ops-alerts within 30s.
  4. Verify the Lambda invocation appears in CloudWatch Logs.
```

## What the skill caught that a generic assistant misses

1. **Subscription confirmation as the #1 silent failure.** A generic
   assistant suggests "check the SNS subscription." The skill pinpoints
   the exact missing `lambda:add-permission`, explains the silent-drop
   failure mode, and provides the exact remediation command with the
   correct source-arn.

2. **Idempotency for ticket automation.** A generic assistant creates a
   ticket on every alarm event. The skill requires a DynamoDB dedup
   table keyed by alarmName — without it, alarm flapping creates dozens
   of tickets per hour.

3. **Composite rollup as the fatigue fix.** A generic assistant wires
   notifications to each child alarm. The skill wires only the
   composite and requires child alarms to have empty actions — wiring
   both = N+1 pages per incident.

4. **PagerDuty dedup_key.** A generic assistant omits the dedup_key.
   The skill requires `AlarmName:Region` so a fire-then-clear
   auto-resolves the same PagerDuty incident.

5. **Secret storage in Parameter Store.** A generic assistant suggests
   environment variables for the webhook. The skill requires Parameter
   Store (webhook visible in CloudTrail `GetFunctionConfiguration`
   otherwise).

6. **Kill-switch before any action.** A generic assistant omits it. The
   skill requires a Parameter Store value checked first in every Lambda
   forwarder — the only way to silence a flapping alarm without
   disabling the EventBridge rule.

7. **AWS User Notifications + Amazon Q as 2024-2026 native surfaces.**
   A generic assistant reaches for Lambda for every alarm-to-Slack
   workflow. The skill surfaces User Notifications (no Lambda glue for
   standard chat delivery) and Amazon Q (triage layer on top of any
   notification surface).

## Slash-command invocation

```
/aws:automate-cloudwatch-alarm-notification
```

Or via the orchestrator:

```
/aws:pipeline
You: "wire the prod-checkout-critical composite to Slack and PagerDuty"
```

The orchestrator emits
`[Phase: Automate | Skills routed: cloudwatch-alarm-notification-automator]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "wire alarm to Slack and PagerDuty"
# [Phase: Automate | Skills routed: cloudwatch-alarm-notification-automator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the workflow is deployed:

```bash
# Verify subscriptions are confirmed
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout \
  --profile default \
  --query 'Subscriptions[*].{Endpoint:Endpoint, Arn:SubscriptionArn}' \
  --output table

# Send a test publish and verify delivery
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout \
  --subject "TEST post-deploy" \
  --message '{"AlarmName":"test-alarm","NewStateValue":"ALARM","OldStateValue":"OK","NewStateReason":"Manual test publish","Region":"us-east-1"}' \
  --profile default

# Verify the Lambda was invoked (CloudWatch Logs)
aws logs filter-log-events \
  --log-group-name /aws/lambda/alarm-slack-forwarder \
  --start-time $(date -u -d '5 min ago' +%s)000 \
  --profile default

# For Jira integration: verify the dedup table
aws dynamodb scan --table-name alarm-ticket-map \
  --profile default \
  --query 'Items[*].{Alarm:alarmName.S, Ticket:issueKey.S}' \
  --output table
