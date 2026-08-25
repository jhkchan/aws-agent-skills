# Destinations and Actions — OpenSearch Alerting Deployer

Deep reference on destination configuration (Slack, SNS, Chime,
custom webhook), the notification plugin (notification.yaml) for
SNS actions, message templating (Mustache with ctx fields), action
retries, and alert acknowledgment workflow. Loaded on demand by
the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Destination types

| Type | Authentication | Notification plugin required? | Use case |
|---|---|---|---|
| Slack | Webhook URL (stored in keystore) | No | Team chat notifications |
| Amazon SNS | SNS topic ARN + IAM role | Yes (notification.yaml) | Fan-out to email, SMS, Lambda, PagerDuty |
| Amazon Chime | Webhook URL (stored in keystore) | No | Chime chat notifications |
| Custom webhook | URL + optional auth headers | No | Custom integrations |

## Slack destination

### Create a Slack destination

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "slack",
    "name": "ops-alerts-slack",
    "slack": {
      "url": "https://hooks.slack.com/services/T000/B000/XXXXX"
    }
  }'
```

**Response:** returns a destination ID (e.g., `dest-xxxx`).

### Slack message formatting

Slack supports message attachments with color coding by severity:

```json
{
  "message_template": {
    "source": "{\"attachments\":[{\"color\":\"danger\",\"title\":\"Alert: {{ctx.monitor.name}}\",\"text\":\"Severity {{ctx.trigger.severity}} — Errors: {{ctx.results[0].aggregations.error_count.value}}\"}]}"
  }
}
```

**Severity colors:**
- Severity 1 (high): `danger` (red)
- Severity 2 (medium-high): `warning` (orange)
- Severity 3 (medium): `#FFCC00` (yellow)
- Severity 4-5 (low): `#36a64f` (green)

### Slack webhook setup

1. Go to the Slack workspace → Apps → Incoming Webhooks.
2. Create a new webhook for the target channel.
3. Copy the webhook URL (format:
   `https://hooks.slack.com/services/Txxx/Bxxx/xxx`).
4. Store the URL in the OpenSearch destination.

**Security:** the webhook URL is a secret. Store it in the
destination (keystore-backed), not in the monitor definition.

## Amazon SNS destination

### Prerequisites

SNS actions require the **notification plugin** (notification.yaml)
configured at the OpenSearch domain level. This is a domain-level
configuration, not a per-monitor configuration.

**1. Create an SNS topic:**

```bash
aws sns create-topic --name alert-topic --region us-east-1
# Returns: arn:aws:sns:us-east-1:123456789012:alert-topic
```

**2. Create an IAM role with sns:Publish permission:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:us-east-1:123456789012:alert-topic"
    }
  ]
}
```

**Trust policy** (allows OpenSearch to assume the role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "es.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**3. Configure notification.yaml on the domain:**

Via the OpenSearch Service console (Advanced options) or the
`--advanced-security-options` CLI parameter:

```yaml
plugin:
  notification:
    sns:
      role_arn: arn:aws:iam::123456789012:role/os-alerting-sns
      topic_arn: arn:aws:sns:us-east-1:123456789012:alert-topic
```

**4. Create the SNS destination in OpenSearch:**

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "sns",
    "name": "ops-alerts-sns",
    "sns": {
      "topic_arn": "arn:aws:sns:us-east-1:123456789012:alert-topic"
    }
  }'
```

### SNS message format

SNS messages are plain text (no rich formatting). Include monitor
name, trigger, severity, and key metrics:

```
Alert: {{ctx.monitor.name}}
Trigger: {{ctx.trigger.name}}
Severity: {{ctx.trigger.severity}}
Errors: {{ctx.results[0].aggregations.error_count.value}}
Time: {{ctx.periodStart}} to {{ctx.periodEnd}}
```

### SNS fan-out

SNS fans out to multiple endpoints via subscriptions:
- Email (simple SMTP)
- SMS (text message)
- Lambda (custom processing, PagerDuty integration)
- HTTP/HTTPS endpoint (webhook)

```bash
# Add email subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:alert-topic \
  --protocol email \
  --notification-endpoint ops@example.com

# Add Lambda subscription (for PagerDuty integration)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:alert-topic \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456789012:function:pagerduty-relay
```

## Amazon Chime destination

### Create a Chime destination

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "chime",
    "name": "ops-chime-webhook",
    "chime": {
      "url": "https://hooks.chime.aws/incomingwebhooks/xxxxx"
    }
  }'
```

Chime webhooks accept the same JSON message format as Slack
(attachments with color coding).

## Custom webhook destination

### Create a custom webhook destination

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "custom_webhook",
    "name": "per-user-webhook",
    "custom_webhook": {
      "url": "https://api.example.com/alerts",
      "header_params": {
        "Authorization": "Bearer xxxxx",
        "Content-Type": "application/json"
      },
      "message_body": "{\"alert\":\"{{ctx.monitor.name}}\",\"user\":\"{{ctx.docs[0].user_id}}\"}"
    }
  }'
```

**Use cases:**
- Custom incident management system (ServiceNow, Jira).
- Per-user notification (each matching document triggers a separate
  webhook call).
- Integration with monitoring platforms (Datadog, New Relic).

## Message templating (Mustache)

Action messages use Mustache templates with access to the `ctx`
object.

### Template variables

| Variable | Description |
|---|---|
| `{{ctx.monitor.name}}` | Monitor name |
| `{{ctx.monitor.type}}` | Monitor type |
| `{{ctx.trigger.name}}` | Trigger name |
| `{{ctx.trigger.severity}}` | Severity (1-5) |
| `{{ctx.results[0].hits.total.value}}` | Total hit count |
| `{{ctx.results[0].aggregations.*}}` | Aggregation results |
| `{{ctx.periodStart}}` | Execution window start |
| `{{ctx.periodEnd}}` | Execution window end |
| `{{ctx.docs[0].*}}` | Document fields (per-document monitors) |
| `{{ctx.alert.id}}` | Alert ID (on alert actions) |

### Conditional blocks

```mustache
Alert: {{ctx.monitor.name}}
{{#ctx.results[0].aggregations.error_count}}
Error count: {{ctx.results[0].aggregations.error_count.value}}
{{/ctx.results[0].aggregations.error_count}}
```

### Looping over aggregation buckets

```mustache
Top error sources:
{{#ctx.results[0].aggregations.by_source.buckets}}
- {{key}}: {{doc_count}} errors
{{/ctx.results[0].aggregations.by_source.buckets}}
```

## Action retries

Actions are retried up to 3 times on failure (network timeout,
destination unreachable, HTTP 5xx). After 3 failures, the action is
marked as `ERROR` in the alert history.

**Not retried:** HTTP 4xx errors (authentication failure, invalid
payload). These indicate a configuration problem, not a transient
failure.

## Alert states and acknowledgment

### Alert lifecycle

```text
ACTIVE → ACKNOWLEDGED → COMPLETED
  ↓
ERROR (action delivery failed after retries)
```

- `ACTIVE`: trigger condition met; alert fired.
- `ACKNOWLEDGED`: an operator acknowledged the alert.
- `COMPLETED`: trigger condition no longer met (resolved).
- `ERROR`: action delivery failed.

### Acknowledge an alert

```bash
curl -X PUT "<endpoint>/_plugins/_alerting/acks/<alert-id>" \
  -u "<user>:<pass>"
```

Acknowledging does NOT:
- Stop the monitor from running on schedule.
- Suppress future alerts from the same trigger.
- Change the trigger condition.

Acknowledging DOES:
- Mark the alert as `ACKNOWLEDGED` in the UI.
- Signal to the team that someone is aware and working on it.

### View active alerts

```bash
curl "<endpoint>/.plugins-alerting-alerts/_search?size=50&sort=start_time:desc" \
  -u "<user>:<pass>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          { "term": { "state": "ACTIVE" } }
        ]
      }
    }
  }'
```

### Alert history per monitor

```bash
curl "<endpoint>/.plugins-alerting-alerts/_search" \
  -u "<user>:<pass>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": { "monitor_id": "<monitor-id>" }
    },
    "sort": [{ "start_time": "desc" }],
    "size": 20
  }'
```

## Common pitfalls

1. **SNS action without notification plugin.** The SNS action fails
   silently at trigger time. Always configure notification.yaml at
   the domain level before creating SNS destinations.

2. **Inlining webhook URLs in the monitor config.** Webhook URLs
   should be stored in the destination resource (keystore-backed).
   Inlining them in the monitor definition exposes the URL in the
   monitor API response.

3. **Not testing the destination before relying on it.** Send a
   test notification (via the Destinations UI or a test monitor) to
   verify delivery before creating production monitors.

4. **Using severity to route alerts.** Severity is metadata only.
   To route by severity, create separate triggers with different
   actions (e.g., trigger 1 severity 1 → PagerDuty, trigger 2
   severity 3 → Slack).

5. **Expecting acknowledgment to mute alerts.** Acknowledging marks
   the alert but does NOT prevent new alerts from the same trigger.
   To mute, disable the monitor or adjust the trigger condition.

## Expert heuristic: destination must be configured before monitor

A baseline model creates the monitor and destination in any order.
The correct heuristic recognizes that the destination MUST exist
before the monitor references it, because the monitor validates
the destination ID at creation only for the API contract — but
the actual delivery happens at trigger time.

```text
Provisioning order:
  1. Configure notification plugin (notification.yaml) for SNS
     → domain-level config; required before SNS destinations work
  2. Create the destination (Slack webhook URL, SNS topic ARN,
     Chime webhook URL, custom webhook URL)
     → returns a destination ID
  3. Create the monitor referencing the destination ID
     → monitor creates successfully
  4. Test the destination (optional but recommended)
     → send a test notification to verify delivery
  5. Create the trigger with action referencing the destination
     → trigger fires the action when the condition is met
```

**Key implication:** if the destination does not exist or the
notification plugin is not configured for SNS, the monitor creates
successfully but the FIRST alert fails silently (logged in the
alerting plugin error log, not surfaced to the user).

## Expert heuristic: SNS action requires notification.yaml plugin

SNS is the most common destination for production alerting (it
fans out to email, SMS, Lambda, and other endpoints). But it
requires the notification plugin to be configured at the domain
level.

```text
SNS destination setup:
  1. Create an SNS topic (aws sns create-topic)
  2. Create an IAM role with sns:Publish permission for the topic
  3. Configure notification.yaml on the OpenSearch domain:
     plugin:
       notification:
         sns:
           role_arn: arn:aws:iam::<acct>:role/os-alerting-sns
           topic_arn: arn:aws:sns:<region>:<acct>:alert-topic
  4. Create the destination in OpenSearch pointing to the SNS topic
  5. Reference the destination in the monitor action

Without step 3, the SNS action fails at trigger time with
"notification plugin not configured."
```

**Key implication:** always verify the notification plugin is
configured before relying on SNS actions. For Slack/Chime/webhook
destinations, the plugin is not required (credentials are stored
in the destination config directly).

## Destination creation examples (curl — Slack and SNS)

**Create a destination (Slack example):**

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "slack",
    "name": "ops-alerts-slack",
    "slack": {
      "url": "https://hooks.slack.com/services/T000/B000/XXXXX"
    }
  }'
```

**Create a destination (SNS example):**

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "sns",
    "name": "ops-alerts-sns",
    "sns": {
      "topic_arn": "arn:aws:sns:us-east-1:123456789012:alert-topic"
    }
  }'
```
