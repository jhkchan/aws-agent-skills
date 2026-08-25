# CloudWatch Alarm Notification Patterns and Deployment Reference

Load this reference when designing or deploying any CloudWatch alarm
notification workflow. The procedures below are the canonical sequences
for each notification archetype, with pre-checks, command sequence,
post-verification, and rollback notes.

## Decision tree — which notification archetype

| Scenario | Use | Why |
|---|---|---|
| Standard alarm -> Slack/Teams chat | SNS + Lambda forwarder | Custom formatting (Slack blocks, buttons) |
| Standard alarm -> chat (no custom format) | AWS User Notifications + Chatbot | Native, no Lambda to maintain |
| Alarm -> PagerDuty/Opsgenie (page-the-human) | SNS + Lambda forwarder (Events API v2) | Trigger + auto-resolve via dedup_key |
| Alarm -> SMS (best-effort page) | SNS SMS subscription directly | No Lambda; verify regional SMS spend |
| Alarm -> Jira/ServiceNow ticket | EventBridge + Lambda + REST API | Auto-create on ALARM, auto-resolve on OK |
| Deduplicate N noisy children | Composite alarm (OR rule) | One escalation signal, page once |
| Tiered escalation (primary -> secondary) | Step Functions (Wait + Choice + SNS) | Per-tier ack window, auto-escalate |
| "Why did this fire" triage | Amazon Q operational analysis | NL summary, correlation to deploy/logs |
| Sensor failure (INSUFFICIENT_DATA) | EventBridge on INSUFFICIENT_DATA state | Catches the silent blind spot |

## SNS topic naming + access policy baseline

**Naming convention:** `<severity>-notifications-<service>` (e.g.,
`critical-notifications-checkout`, `warning-notifications-orders`). A
dedicated topic per severity lets you grant different subscriptions and
 IAM policies per tier.

**Access policy baseline** (least-privilege — only CloudWatch may publish,
only the Lambda may subscribe):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "cloudwatch.amazonaws.com" },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:cloudwatch:us-east-1:111111111111:alarm:prod-checkout-critical-rollup"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": ["sns:Subscribe", "sns:Unsubscribe"],
      "Resource": "arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout"
    }
  ]
}
```

**Without the `aws:SourceArn` condition**, any principal with
`sns:Publish` can inject messages into the topic — a notification spoofing
vector during an incident.

## Lambda forwarder deployment (Serverless Application Model)

```yaml
# template.yaml
Resources:
  AlarmSlackForwarder:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: alarm-slack-forwarder
      Runtime: python3.11
      Handler: app.lambda_handler
      Timeout: 10
      MemorySize: 256
      ReservedConcurrentExecutions: 50  # headroom for alarm storms
      Environment:
        Variables:
          SLACK_WEBHOOK_PARAM: /slack/critical-webhook
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action: ssm:GetParameter
              Resource: arn:aws:ssm:us-east-1:111111111111:parameter/slack/*
            - Effect: Allow
              Action: ssm:GetParameter
              Resource: arn:aws:ssm:us-east-1:111111111111:parameter/notifications/kill-switch
            - Effect: Allow
              Action: cloudwatch:DescribeAlarms
              Resource: '*'
      Events:
        SnsTrigger:
          Type: SNS
          Properties:
            Topic: !Ref AlarmTopic
            FilterPolicy:
              # Only forward ALARM and OK transitions (skip INSUFFICIENT_DATA)
              # Or include all and let the Lambda filter
              stateName: ["ALARM", "OK"]
```

**Reserved concurrency:** without it, a burst of 100 alarms in 10s will
throttle the Lambda and silently drop notifications. Reserve at least
50 concurrent executions for the forwarder.

## EventBridge rule patterns by use case

### All ALARM transitions for one service (prefix filter)

```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "stateName": ["ALARM"],
    "alarmName": [{"prefix": "prod-checkout-"}]
  }
}
```

### Critical severity only (composite alarm)

```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "stateName": ["ALARM"],
    "alarmName": ["prod-checkout-critical-rollup"]
  }
}
```

### INSUFFICIENT_DATA (sensor failure alert)

```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "stateName": ["INSUFFICIENT_DATA"],
    "previousState": {"value": ["OK", "ALARM"]}
  }
}
```

This catches the silent blind spot — a metric that was reporting and
stopped. Without this, the alarm goes dark without anyone noticing.

## PagerDuty event action matrix

| Alarm state | PagerDuty event_action | Notes |
|---|---|---|
| ALARM | `trigger` | Create a new incident (or re-trigger if dedup_key exists) |
| OK | `resolve` | Auto-resolve the open incident (matched by dedup_key) |
| INSUFFICIENT_DATA | (no action) | Do NOT auto-resolve on sensor failure — the incident may still be real |

**Dedup key construction:** `<AlarmName>:<Region>` for single-resource
alarms. For composite alarms, use `<CompositeAlarmName>` alone (the
composite represents the service, not a single resource).

## Jira / ServiceNow field mapping

| CloudWatch event field | Jira field | ServiceNow field |
|---|---|---|
| `alarmName` | `summary` (prefixed `[ALARM]`) | `short_description` |
| `stateReason` | `description` | `description` |
| `region` | `labels` | `location` |
| `alarmName` | `labels` (auto-created, alarm-name) | `u_alarm_name` (custom field) |
| severity (derived) | `priority` (Critical/High/Medium) | `urgency` (1/2/3) |
| service (derived from prefix) | `components` | `assignment_group` |
| runbook link (SSM parameter) | `customfield_10001` | `u_runbook_url` |

**DynamoDB dedup table schema:**

```
TableName: alarm-ticket-map
PartitionKey: alarmName (String)
Attributes: issueKey (String), createdAt (String), state (String)
TTL: 30 days (expire resolved tickets to keep the table small)
```

## Composite alarm Rule design patterns

### OR — escalation (any child triggers)

```
ALARM(child-a) OR ALARM(child-b) OR ALARM(child-c)
```

Use for "any signal that this service is degraded." The composite is
the page-the-human trigger; children should have empty actions.

### AND — high-confidence correlation

```
ALARM(error-rate-high) AND ALARM(latency-anomaly)
```

Use when both symptoms must be present to confirm a real incident.
Fragile — if error-rate clears before latency fires, the composite never
enters ALARM. Use with care; OR is almost always the safer default.

### NOT — anti-signal (missing expected alarm)

```
ALARM(backup-expected-by-0200) AND NOT OK(backup-actually-completed)
```

Use for "should-have-fired-but-didn't" detection. The composite fires
when a heartbeat alarm that SHOULD be in ALARM (because backup didn't
complete) is NOT in OK state. Advanced pattern; test carefully.

## Escalation timing matrix (2026)

| Severity | Tier 1 (primary) | Tier 2 (secondary) | Tier 3 (manager) |
|---|---|---|---|
| SEV-1 (critical) | Immediate | +2 min if unacked | +2 min simultaneously with T2 |
| SEV-2 (high) | Immediate | +5 min if unacked | +15 min if unacked |
| SEV-3 (medium) | Immediate | +15 min if unacked | (none) |
| SEV-4 (low) | Immediate (Slack only, no page) | (none) | (none) |

**Ack SLA tracking:** the Step Functions state machine records the ack
timestamp in DynamoDB. A weekly report on ack SLA (median, p90, p99)
goes to the on-call manager. Persistent ack-SLA misses indicate either
too many false positives (revisit thresholds) or understaffing.

## AWS User Notifications vs Lambda forwarder — decision matrix

| Need | User Notifications (Chatbot) | Lambda forwarder |
|---|---|---|
| Setup time | Minutes (console) | Hours (code + deploy) |
| Message formatting | AWS-default (limited) | Full custom (Slack blocks, buttons) |
| Interactive ack buttons | Limited (Chatbot-native) | Full (custom actions) |
| Multi-channel fan-out | Built-in (Slack + Chime + email) | One Lambda per channel |
| Runbook link in message | Auto-included | Custom |
| Correlation across alarms | Basic | Full (via composite + custom logic) |
| Cost | Per-message (Chatbot) + Chatbot role | Per-invocation (Lambda) |
| Use when | Standard alarm -> chat (greenfield) | Custom formatting / interactive / multi-step |

**Migration path:** start with User Notifications for greenfield
deployments (faster TTR). Migrate to Lambda forwarder when you need
interactive Slack buttons, custom routing, or multi-channel fan-out that
Chatbot does not support. Both can coexist (subscribe Chatbot to one
topic, Lambda to another).

## Cost reference (2026, us-east-1)

- SNS: $0.50 per million publishes; SMS $0.00645/message (US).
- Lambda: $0.00000001667 per ms (256MB). A 200ms forwarder = ~$0.0000008/invocation.
- 1000 alarm notifications/day via Lambda = ~$0.03/day in Lambda cost.
- SMS for 100 pages/day = $0.65/day. Watch for flapping alarms.
- PagerDuty/Opsgenie: per-user licensing, not per-event.
- AWS User Notifications: per-message pricing on the Chatbot integration;
  see AWS User Notifications pricing page.
- Step Functions: $0.025 per million state transitions. A 3-tier
  escalation (7 states) = $0.000000175/escalation.

For a fleet of 200 alarms averaging 5 notifications/day each: ~$0.50/day
in Lambda cost + ~$0.01/day in SNS + negligible Step Functions.

## Audit trail checklist

Every notification workflow MUST be auditable end-to-end:

- [ ] CloudTrail covers `sns:Publish`, `lambda:InvokeFunction`,
      `events:PutEvents` in the account/region.
- [ ] CloudWatch Logs for the Lambda forwarder retained >= 30 days
      (default is infinite; set explicit retention).
- [ ] DynamoDB dedup table records `createdAt`, `issueKey`, `state`
      for every ticket created.
- [ ] PagerDuty/Jira/ServiceNow incident records include the CloudWatch
      alarm name and Step Functions execution ARN (if escalation used).
- [ ] Step Functions execution history retained >= 90 days.
- [ ] A post-incident Athena query on CloudTrail can reconstruct the
      full notification timeline (publish -> invoke -> webhook POST).

## Common failure modes and fixes

| Failure | Symptom | Fix |
|---|---|---|
| Unconfirmed subscription | Alarm fires, no Slack message | Confirm subscription (email click) or add lambda:add-permission |
| Missing lambda:add-permission | Lambda never invoked, no CloudWatch Logs | aws lambda add-permission --principal sns.amazonaws.com |
| Hardcoded webhook in env var | Webhook leaks via CloudTrail | Move to Parameter Store; rotate the webhook |
| Alarm flapping without dedup | 60 pages/hour, on-call burnout | Build composite OR add DynamoDB dedup in forwarder |
| Chatbot + Lambda double-notify | Two Slack messages per alarm | Subscribe Chatbot to separate aws-chatbot topic |
| PagerDuty creates N incidents | One per state change, never auto-resolves | Use stable dedup_key (AlarmName:Region) |
| Lambda timeout on PagerDuty API | Forwarder errors, no page delivered | Set timeout to 10s+, add reserved concurrency |
| SMS budget exhausted | No SMS delivered | AWS Budgets alert; composite rollup to reduce count |
| EventBridge rule too broad | Pages on test/staging alarms | Add `alarmName.prefix` filter (e.g., `prod-`) |
| Ticket duplicate storm | Dozens of Jira tickets per hour | Idempotency check in DynamoDB keyed by alarmName |

## Worked example — AUTOMATED Slack + PagerDuty + composite correlation

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
  AWS User Notifications hub: arn:aws:notifications::111111111111:hub/prod
SAFETY:
  - [PASS] Kill-switch: Parameter Store /notifications/kill-switch
  - [PASS] Both Lambda subscriptions confirmed (SubscriptionArn populated)
  - [PASS] Test publish delivered to Slack and PagerDuty within 12s
  - [PASS] Lambda IAM scoped to ssm:GetParameter on /slack/*, /pagerduty/*, /notifications/*
  - [PASS] Slack webhook in Parameter Store /slack/critical-webhook (encrypted)
  - [PASS] PagerDuty routing key in Parameter Store /pagerduty/integration-key (encrypted)
  - [PASS] Composite rollup deduplicates 3 child alarms (flap-safe)
FINDINGS:
  - [INFO] Composite alarm OR rule covers alb-error-ratio-prod, alb-latency-anomaly-prod, lambda-errors-high-prod-checkout
  - [INFO] PagerDuty dedup_key = AlarmName:Region for auto-resolve
  - [WARN] AWS User Notifications hub also configured — may double-notify if Chatbot subscribes to the same topic. Verify Chatbot subscribes to aws-chatbot topic, not critical-notifications-checkout.
REMEDIATION: Deploy via CloudFormation:
  aws cloudformation deploy --stack-name prod-alarm-notifications \
    --template-file alarm-notifications.yaml \
    --capabilities CAPABILITY_NAMED_IAM
```

## Worked example — MANUAL_STEP_REQUIRED (missing lambda:add-permission)

```text
NOTIFICATION_SOURCE: api-error-rate-prod
SCOPE: Slack #ops-alerts
VERDICT: MANUAL_STEP_REQUIRED
WORKFLOW:
  EventBridge rule: alarm-state-change-to-sns
  SNS topic: arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout
  Lambda forwarder(s): alarm-slack-forwarder
  Subscription status: PENDING (Lambda subscription added but SNS invoke permission missing)
SAFETY:
  - [PASS] Kill-switch implemented
  - [FAIL] Subscription NOT functional: lambda:add-permission for AllowSNSInvoke missing. SNS cannot invoke the Lambda.
  - [PASS] Lambda IAM least-privilege
  - [PASS] Secrets in Parameter Store
FINDINGS:
  - [CRITICAL] SNS topic -> Lambda subscription is broken: the Lambda resource policy does not grant sns.amazonaws.com lambda:InvokeFunction for this topic ARN. The alarm will fire, SNS will publish, but the Lambda will never be invoked. This is the silent-drop failure mode.
  - [HIGH] Test publish was never run after the subscription was added.
REMEDIATION:
  1. aws lambda add-permission --function-name alarm-slack-forwarder --statement-id AllowSNSInvoke --action lambda:InvokeFunction --principal sns.amazonaws.com --source-arn arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout
  2. aws sns publish --topic-arn arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout --message '{"test": true}' --subject "TEST after fix"
  3. Verify the test message appears in Slack within 30s.
```

<!-- Appended from SKILL.md (progressive-disclosure restructure); content above is unchanged. -->

## Lambda forwarder handler (Slack incoming webhook) — inline code

```python
import json, urllib.request, os, boto3

WEBHOOK_PARAM = os.environ['SLACK_WEBHOOK_PARAM']  # Parameter Store name

def lambda_handler(event, context):
    ssm = boto3.client('ssm')
    if ssm.get_parameter(Name='/notifications/kill-switch')['Parameter']['Value'] == 'disabled':
        return {'status': 'killed'}
    webhook = ssm.get_parameter(Name=WEBHOOK_PARAM, WithDecryption=True)['Parameter']['Value']
    record = event['Records'][0]['Sns']
    alarm = json.loads(record['Message'])
    msg = {
        'text': f":rotating_light: *{alarm.get('AlarmName', 'unknown')}* -> {alarm.get('NewStateValue', 'ALARM')}",
        'blocks': [
            {'type': 'header', 'text': {'type': 'plain_text', 'text': f"Alarm: {alarm.get('AlarmName')}"}},
            {'type': 'section', 'fields': [
                {'type': 'mrkdwn', 'text': f"*State:* {alarm.get('NewStateValue')} (was {alarm.get('OldStateValue')})"},
                {'type': 'mrkdwn', 'text': f"*Reason:* {alarm.get('NewStateReason', 'N/A')[:300]}"},
                {'type': 'mrkdwn', 'text': f"*Region:* {alarm.get('Region')}"}]},
            {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f"*Runbook:* {alarm.get('RunbookLink', 'https://runbooks.example.com/')}"}}
        ]}
    urllib.request.urlopen(urllib.request.Request(
        webhook, json.dumps(msg).encode(), {'Content-Type': 'application/json'}))
    return {'status': 'sent'}
```

**Secret storage:** Parameter Store for webhooks (free, encrypted by
default); Secrets Manager for OAuth tokens (paid, rotation). NEVER
hardcode in Lambda environment variables — they are visible in
CloudTrail `GetFunctionConfiguration` and the console.

## PagerDuty Events API v2 forwarder — inline code

```python
import json, urllib.request, boto3

def lambda_handler(event, context):
    ssm = boto3.client('ssm')
    routing_key = ssm.get_parameter(Name='/pagerduty/integration-key', WithDecryption=True)['Parameter']['Value']
    alarm = json.loads(event['Records'][0]['Sns']['Message'])
    action = 'trigger' if alarm.get('NewStateValue') == 'ALARM' else 'resolve'
    dedup = alarm.get('AlarmName', 'alarm') + ':' + alarm.get('Region', '')
    payload = {
        'routing_key': routing_key, 'event_action': action, 'dedup_key': dedup,
        'payload': {
            'summary': f"{alarm.get('AlarmName')} -> {alarm.get('NewStateValue')}",
            'severity': 'critical' if 'critical' in alarm.get('AlarmName', '').lower() else 'error',
            'source': f"aws:cloudwatch:{alarm.get('Region')}",
            'custom_details': {'reason': alarm.get('NewStateReason', 'N/A')[:500]}}}
    urllib.request.urlopen(urllib.request.Request(
        'https://events.pagerduty.com/v2/enqueue',
        json.dumps(payload).encode(), {'Content-Type': 'application/json'}))
    return {'status': 'paged'}
```

**Dedup key:** PagerDuty correlates trigger/resolve by `dedup_key`. Use
`AlarmName:Region` so a fire-then-clear auto-resolves the same incident.
Without a stable dedup key, every state change creates a NEW incident —
the #1 PagerDuty integration bug.

## Subscription + confirmation commands (MANDATORY verification)

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:alarm-notifications-prod \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:alarm-slack-forwarder

# GRANT SNS permission to invoke the Lambda (commonly missed!)
aws lambda add-permission \
  --function-name alarm-slack-forwarder \
  --statement-id AllowSNSInvoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:111111111111:alarm-notifications-prod

# VERIFY (SubscriptionArn must NOT be "PendingConfirmation")
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:alarm-notifications-prod
```

Lambda subscriptions auto-confirm but require `lambda:add-permission`.
HTTPS/email/SMS subscriptions require explicit endpoint confirmation.
Always verify `SubscriptionArn` is populated.

## Test publish (run after every subscription change)

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:alarm-notifications-prod \
  --subject "TEST alarm notification" \
  --message '{"AlarmName":"test-alarm","NewStateValue":"ALARM","OldStateValue":"OK","NewStateReason":"Manual test publish","Region":"us-east-1"}'
```

If the test does not arrive in Slack/PagerDuty within 30 seconds, the
subscription is unconfirmed OR the Lambda errored. Check CloudWatch Logs
before relying on the workflow.

## Alarm-to-ticket Lambda (Jira auto-create / auto-resolve) — inline code

```python
import json, urllib.request, os, boto3, base64

def lambda_handler(event, context):
    ssm = boto3.client('ssm')
    token = ssm.get_parameter(Name='/jira/api-token', WithDecryption=True)['Parameter']['Value']
    email = ssm.get_parameter(Name='/jira/email')['Parameter']['Value']
    project = os.environ['JIRA_PROJECT']
    detail = event['detail']
    alarm_name, state = detail['alarmName'], detail['stateName']
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    dynamo = boto3.client('dynamodb')

    if state == 'ALARM':
        # Idempotency: check for existing open ticket
        existing = dynamo.get_item(TableName='alarm-ticket-map',
            Key={'alarmName': {'S': alarm_name}}).get('Item')
        if existing:
            return {'status': 'duplicate-suppressed'}
        body = {'fields': {
            'project': {'key': project},
            'summary': f"[ALARM] {alarm_name} -> ALARM",
            'description': f"Reason: {detail.get('stateReason', 'N/A')}\nRunbook: https://runbooks.example.com/",
            'issuetype': {'name': 'Incident'},
            'labels': ['auto-created', 'cloudwatch-alarm']}}
        req = urllib.request.Request(
            f"https://your-domain.atlassian.net/rest/api/3/issue",
            json.dumps(body).encode(),
            {'Content-Type': 'application/json', 'Authorization': f'Basic {auth}'})
        issue_key = json.loads(urllib.request.urlopen(req).read())['key']
        dynamo.put_item(TableName='alarm-ticket-map',
            Item={'alarmName': {'S': alarm_name}, 'issueKey': {'S': issue_key}})
    elif state == 'OK':
        item = dynamo.get_item(TableName='alarm-ticket-map',
            Key={'alarmName': {'S': alarm_name}}).get('Item')
        if item:
            key = item['issueKey']['S']
            # Transition to Resolved
            urllib.request.urlopen(urllib.request.Request(
                f"https://your-domain.atlassian.net/rest/api/3/issue/{key}/transitions",
                json.dumps({'transition': {'id': '31'}}).encode(),
                {'Content-Type': 'application/json', 'Authorization': f'Basic {auth}'}))
    return {'status': state}
```

**Idempotency is MANDATORY.** Without the DynamoDB dedup check, alarm
flapping (OK -> ALARM every 60s) creates dozens of tickets per hour.
ServiceNow follows the same pattern: `POST /api/now/table/incident` with
`short_description`, store `sys_id` in DynamoDB keyed by alarm name,
auto-resolve via `PATCH` with `state=6` when alarm clears.

## Tiered escalation state machine (Step Functions JSON, ack mechanism, timing)

```json
{
  "StartAt": "PagePrimary",
  "States": {
    "PagePrimary": {
      "Type": "Task",
      "Resource": "arn:aws:sns:us-east-1:111111111111:on-call-primary",
      "Next": "WaitForAck"
    },
    "WaitForAck": {"Type": "Wait", "Seconds": 300, "Next": "CheckAck"},
    "CheckAck": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.acknowledged", "BooleanEquals": true, "Next": "Done"}],
      "Default": "PageSecondary"
    },
    "PageSecondary": {
      "Type": "Task",
      "Resource": "arn:aws:sns:us-east-1:111111111111:on-call-secondary",
      "Next": "WaitForAck2"
    },
    "WaitForAck2": {"Type": "Wait", "Seconds": 300, "Next": "CheckAck2"},
    "CheckAck2": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.acknowledged", "BooleanEquals": true, "Next": "Done"}],
      "Default": "PageManager"
    },
    "PageManager": {
      "Type": "Task",
      "Resource": "arn:aws:sns:us-east-1:111111111111:on-call-manager",
      "Next": "Done"
    },
    "Done": {"Type": "Succeed"}
  }
}
```

**Ack mechanism:** the SNS message includes a one-click ack URL (API
Gateway + Lambda writing to DynamoDB). After each `Wait`, the state
machine reads the ack state. If acknowledged, exit; otherwise escalate.

**Tier timing baseline (2026):**
- Standard: Primary -> 5 min -> Secondary -> 5 min -> Manager.
- Critical (SEV-1): Primary -> 2 min -> Secondary + Manager simultaneously.
- Low-severity: Primary only, no escalation.

