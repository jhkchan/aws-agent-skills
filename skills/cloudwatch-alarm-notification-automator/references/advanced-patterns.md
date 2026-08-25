# CloudWatch Alarm Notification Automator — Advanced Patterns

Deep-dive material moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## 2024-2026 native surfaces (detail)

### AWS User Notifications (chat-based, no Lambda glue)

AWS User Notifications (2024-2025) delivers CloudWatch alarm state
changes natively to Slack, Amazon Chime, Microsoft Teams, email, and the
AWS Console Notifications Center without any Lambda forwarder.

```bash
aws notifications create-notification-hub --region us-east-1

aws chatbot create-slack-channel-configuration \
  --configuration-name prod-alarm-slack \
  --slack-workspace-id T0XXXXXXXX \
  --slack-channel-id C0XXXXXXXX \
  --sns-topic-arns arn:aws:sns:us-east-1:111111111111:aws-chatbot \
  --iam-role-arn arn:aws:iam::111111111111:role/aws-chatbot-role
```

| Dimension | User Notifications (Chatbot) | Lambda forwarder |
|---|---|---|
| Setup time | Minutes (console) | Hours (code + deploy) |
| Formatting | AWS-default (limited) | Full custom (Slack blocks, buttons) |
| Interactive buttons | Limited (ack from Slack) | Full (custom actions) |
| Maintenance | AWS-managed | You maintain Lambda runtime |
| Use when | Standard alarm -> chat | Custom formatting / multi-step workflow |

### SNS SMS + phone-number subscriptions (page-the-human)

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:on-call-critical \
  --protocol sms \
  --notification-endpoint +15551234567
```

**Caveats:**
- SMS subscriptions require confirmation (reply YES).
- SMS delivery is best-effort, NOT guaranteed. Use PagerDuty/Opsgenie
  for guaranteed delivery; SNS SMS as backup.
- SMS cost per message varies by country ($0.00645 in US). A flapping
  alarm at 60s intervals = $9/day in SMS charges. Always pair with a
  composite rollup to deduplicate.
  via SNS + Amazon Pinpoint — verify regional availability.

### Amazon Q operational analysis (alarm triage)

Amazon Q (2024-2025) provides natural-language triage for CloudWatch
alarms. When an alarm fires, Q analyzes related logs, metrics,
deployments, and prior incidents, then produces a "what changed, what
to check, what to do" summary.

```bash
aws application-signals update-application \
  --application-identifier prod-checkout \
  --operational-analysis-config '{"enabled": true}'
```

The SNS notification can include a deep link to the Q analysis:
`https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#amazonq:alarm=<alarm-name>`.

**What Q adds (vs raw alarm notification):**
- Correlates the alarm with recent deployments (CodeDeploy /
  CodePipeline) — "alarm started 8 min after deploy v123."
- Surfaces related log errors via Logs Insights query.
- Compares current metric to the prior 7-day baseline.
- Suggests a remediation runbook based on the alarm type.

Use Q as the triage layer ON TOP of the notification surface: the
notification wakes the human; Q tells the human what to do next.

## Edge-case handling

- **Alarm flapping (OK -> ALARM every 60s).** Without a composite
  rollup, this generates 60 pages/hour. Fix: build a composite with
  `DatapointsToAlarm=2, EvaluationPeriods=3`, OR add a dedup window in
  the Lambda forwarder (track last-notified timestamp in DynamoDB;
  suppress if within 5 min).
- **Cross-region alarm notification.** SNS topics are regional. An alarm
  in eu-west-1 cannot directly invoke an SNS topic in us-east-1. Use
  EventBridge global endpoint bus or deploy the stack in every region.
- **Lambda forwarder timeout.** The default 3s is too short for
  PagerDuty API calls (2-5s under load). Set timeout to at least 10s
  and provision concurrency headroom — 50 alarms in 10s will throttle.
- **PagerDuty rate limiting.** Events API v2 rate-limits at
  300 events/min per routing key. A composite rollup deduplicates to
  one event; N child alarms without rollup can hit the limit.
- **Slack rate limiting.** Incoming webhooks rate-limit at
  1 msg/sec/channel with bursts. Composite rollup prevents this;
  without it, alarms pile up in Slack's queue and arrive minutes late.
- **AWS User Notifications + Lambda double-notify.** If both are wired
  to the same SNS topic, every alarm produces two Slack messages.
  Verify Chatbot subscribes to a separate topic.

## Recent AWS features (2024-2026)

- **AWS User Notifications (2024-2025):** Native chat-based delivery
  (Slack, Chime, Teams) for CloudWatch alarm state changes without
  Lambda glue. Configured via Console or `aws notifications` CLI.
  Reduces setup time from hours to minutes; offers less formatting
  control than a Lambda forwarder.
- **Amazon Q operational analysis (2024-2025):** Natural-language
  triage for CloudWatch alarms. Q correlates the alarm with deployments,
  logs, metrics, and prior incidents; produces a "what changed, what to
  check" summary. Layer on top of any notification surface.
- **SNS SMS sandbox lift (2024):** Production SMS subscriptions no
  longer require sandbox exit in most regions. Verify monthly spend via
  AWS Budgets — flapping alarms can exhaust SMS budget.
- **CloudWatch cross-account composite alarms (2024-2025):** Composite
  rules can reference child alarms in other accounts via `AccountId` in
  the Metrics array. Use for multi-account rollups.
- **EventBridge global endpoints (2024-2025):** Multi-region event bus
  failover for cross-region notification workflows. Primary bus in
  us-east-1 with failover to us-west-2.

