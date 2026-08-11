---
name: cloudtrail-alert-automator
description: >-
  Designs and deploys CloudTrail alerting automation across an AWS estate.
  Builds EventBridge rules for security-critical API calls (root console
  login, IAM policy changes, security group modifications, CloudTrail
  disabling), wires SNS topic routing by severity, deploys Lambda
  enrichment functions that use lookup-events to attach actor context,
  source IP correlation, and recent activity. Integrates with Security
  Hub via BatchImportFindings, delivers to Slack/Teams via webhook,
  implements deduplication by event identity, and suppresses known CI/CD
  service-role alerts. Supports multi-account via Organizations trail and
  CloudTrail Insights anomaly alerting. Emits AUTOMATION_DEPLOYED with
  deployable IaC or REVIEW_REQUIRED with the specific gap.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline alert-design. Live deployment
  uses aws events put-rule, put-targets, aws sns create-topic, subscribe,
  aws lambda create-function, aws securityhub batch-import-findings, and
  aws cloudtrail lookup-events, create-event-data-store, start-query —
  AWS CLI v2, SSO or key-based credentials.
keywords:
  - AWS CloudTrail
  - EventBridge
  - SNS alerting
  - Security Hub
  - lookup-events
  - CloudTrail Lake
  - CloudTrail Insights
  - root login alert
  - IAM change alert
  - security group change
  - Slack webhook
  - alert deduplication
  - alert suppression
  - Organizations trail
  - governance automation
tags: [aws-cloudtrail, eventbridge, sns, security-hub, lambda, governance, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Designing CloudTrail alerting automation, wiring EventBridge rules for
    security-critical API calls, building Lambda enrichment with
    lookup-events context, integrating CloudTrail alerts with Security Hub
    custom findings, routing alerts to Slack or Teams, suppressing known
    CI/CD automation noise, or deploying multi-account CloudTrail alerting
    via an Organizations trail.
  activation_triggers:
    - "automate CloudTrail alerts"
    - "EventBridge rule for root login"
    - "IAM change alert"
    - "security group change notification"
    - "CloudTrail SNS alert"
    - "Security Hub custom finding from CloudTrail"
    - "CloudTrail Lake query"
    - "Slack webhook CloudTrail"
    - "alert deduplication"
    - "suppress CI/CD service role alerts"
    - "CloudTrail Insights anomaly"
    - "Organizations trail alerting"
  invocation_schema: >-
    Input: either (a) a set of CloudTrail event names or categories to
    alert on plus the desired notification targets (SNS, Security Hub,
    Slack, Teams), OR (b) an existing alerting setup to audit. Output:
    deterministic ALERT block per rule — RULE/ENRICHMENT/ROUTING/DEDUP/
    SUPPRESSION/VERDICT — where VERDICT is AUTOMATION_DEPLOYED or
    REVIEW_REQUIRED.
---

# CloudTrail Alert Automator

## Mindset

**One-line takeaway:** every CloudTrail alert is a four-stage pipeline —
**detect** (EventBridge rule matching a CloudTrail API event) →
**enrich** (Lambda lookup-events for actor context, source IP, prior
correlation) → **route** (SNS topic by severity, Security Hub finding,
Slack/Teams webhook) → **deduplicate + suppress** (window-based dedup,
service-role suppression list). A gap in ANY stage produces alert
fatigue or missed critical events.

- **Detection** without **enrichment** is a raw event dump: "ConsoleLogin
  by root" tells you nothing about whether it was a legitimate break-glass
  or a compromise. Enrichment with `lookup-events` for the surrounding 15
  minutes adds the actor's recent API activity and the source IP context.
- **Routing** without **severity tiering** means every alert pages the
  on-call equally. Root login is CRITICAL; an IAM user self-rotating their
  access key is LOW. Severity is derived from event name, actor type, and
  resource impact.
- **Deduplication + suppression** is the difference between a useful alert
  and a noisy one. A CI/CD pipeline calling `UpdateStack` 200 times in a
  deploy window produces 200 identical alerts without dedup.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick the right EventBridge event pattern | Step 1 + Appendix A |
| Decide severity tier | Step 2 (severity matrix) |
| Build Lambda enrichment with lookup-events | Step 3 |
| Wire SNS routing by severity | Step 4 |
| Send to Slack or Teams webhook | Step 5 |
| Integrate with Security Hub custom findings | Step 6 |
| Implement deduplication logic | Step 7 |
| Suppress known CI/CD automation | Step 8 |
| Deploy multi-account via Organizations trail | Step 9 |
| Use CloudTrail Lake for historical queries | Step 10 |
| Enable CloudTrail Insights anomaly alerting | Step 11 |
| Avoid common alerting pitfalls | Anti-Patterns |
| Recent features (Insights, Lake) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **EventBridge `detail.eventName` matching is case-sensitive and
   exact.** List every variant explicitly. A common miss: alerting on
   `DeleteSecurityGroup` but not `RevokeSecurityGroupIngress` — the
   revoke is the more dangerous operation and goes undetected.
2. **`lookup-events` has a 15-minute lookback ceiling per call.** For
   enrichment beyond 15 minutes, use CloudTrail Lake queries. A single
   `lookup-events` with no `StartTime` returns only the last 15 minutes.
3. **SNS message size cap is 256 KB.** Enriched events can exceed this.
   Always truncate. A `MessageAttributes` overflow produces a silent SNS
   publish failure logged only in Lambda's CloudWatch Logs.
4. **Security Hub `BatchImportFindings` deduplicates by `Id`.** Use a
   deterministic `Id` (`<accountId>-<eventName>-<eventTime>-<resourceId>`)
   to avoid orphaned findings. Re-importing with the same `Id` updates.
5. **CloudTrail event delivery latency is 3–15 minutes.** Deduplication
   windows must account for arrival-time delta, not event-time delta.
   Two events 2 minutes apart by `eventTime` may arrive 8 minutes apart
   in EventBridge.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| CloudTrail status | `cloudtrail describe-trails` | Events must exist for alerting |
| Event data store (if Lake in scope) | `cloudtrail list-event-data-stores` | Historical query capability |
| Existing EventBridge rules | `events list-rules` | Avoid duplicate rules |
| SNS topics | `sns list-topics` | Reuse or create new |
| Security Hub enabled status | `securityhub describe-hub` | Whether findings can be imported |
| Slack/Teams webhook URLs | Secrets Manager / Parameter Store | Notification delivery |
| Known service roles for suppression | IAM role inventory | CI/CD, auto-scaling, automation roles |
| CloudTrail Insights status | `cloudtrail get-insight-selectors` | Anomaly alerting availability |

**If the input is malformed** (no CloudTrail enabled, no event list), emit:

```text
ALERT: <reference>
EVENT: <event-name>
VERDICT: ERROR
REASON: Cannot design alerting — CloudTrail status and target event list required.
GAP: Enable CloudTrail and supply the event names to alert on.
```

## Configuration dependency graph

```
CloudTrail (trail or org trail)
  │
  ├── EventBridge rule (event pattern match)
  │     ├── Lambda enrichment (lookup-events, severity classification)
  │     ├── SNS topic (severity-tiered: CRITICAL/HIGH/MEDIUM/LOW)
  │     ├── Security Hub (BatchImportFindings)
  │     ├── Slack/Teams webhook (HTTP POST)
  │     ├── Deduplication (DynamoDB TTL)
  │     └── Suppression list (SSM Parameter Store)
  │
  └── CloudTrail Insights → EventBridge → SNS (dedicated topic)
```

## Process — Alert pipeline design (apply in order)

### Step 0: Expert knowledge — non-obvious behaviors

- **EventBridge matches CloudTrail events only if the trail records
  management events.** Data events require a separate
  `AdvancedEventSelector`. An EventBridge rule for `PutObject` silently
  never fires if the trail records management events only.

- **`root` user events have `userIdentity.type: Root`.** NOT
  `AssumedRole` or `User`. The event pattern `"userIdentity": {"type":
  ["Root"]}` is the correct and only match.

- **`ConsoleLogin` events are emitted for every authentication including
  failures.** The `responseElements.ConsoleLogin` field is `"Success"` or
  `"Failure"`. A rule matching `ConsoleLogin` without the response filter
  generates alerts for every failed login — thousands per minute during
  brute-force.

- **Cross-account events from an Organizations trail arrive in the
  management account's EventBridge with `recipientAccountId` = member
  account.** The `accountId` field is the source account. Filter on
  `recipientAccountId` for management-account alerting.

- **`lookup-events` does NOT return data events.** Only management events
  are queryable. For data-event enrichment, use CloudTrail Lake.

- **Security Hub `BatchImportFindings` throttles at ~100 QPS.**
  High-volume alerting can exhaust this. Implement batching and a
  fallback to SNS-only delivery when throttling.

- **Slack webhooks rate-limit at 1 message/second per URL.** Use SQS →
  Lambda consumer to buffer bursts. Direct SNS → Slack webhook produces
  `429 Too Many Requests` on bursts.

- **`StopLogging` and `DeleteTrail` blind your alerting.** Always alert
  on these at CRITICAL with NO suppression. An attacker who calls
  `StopLogging` has up to 15 minutes of blindness before events stop.

### Step 1: Build the EventBridge event pattern

**Root console login (CRITICAL):**

```json
{
  "source": ["aws.signin"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "userIdentity": {"type": ["Root"]},
    "eventName": ["ConsoleLogin"],
    "responseElements": {"ConsoleLogin": ["Success"]}
  }
}
```

**Security-critical IAM changes (HIGH):**

```json
{
  "source": ["aws.iam"],
  "detail": {"eventName": [
    "AttachRolePolicy", "DetachRolePolicy", "PutRolePolicy",
    "DeleteRolePolicy", "CreatePolicyVersion", "DeletePolicy",
    "UpdateAssumeRolePolicy", "CreateAccessKey", "DeleteAccessKey",
    "UpdateAccountPasswordPolicy"
  ]}
}
```

**CloudTrail tampering (CRITICAL — never suppress):**

```json
{
  "source": ["aws.cloudtrail"],
  "detail": {"eventName": [
    "DeleteTrail", "StopLogging", "UpdateTrail",
    "DeleteEventDataStore", "PutEventSelectors"
  ]}
}
```

Common pattern errors:

| Error | Cause | Fix |
|---|---|---|
| Rule never fires | `detail-type` or `source` mismatch | Verify via CloudTrail event JSON |
| Fires on wrong events | Overly broad `eventName` (e.g., `Create*`) | List events explicitly |
| Misses regional events | Rule in one region only | Deploy to all active regions |
| Fires on read-only events | No `readOnly` filter | Add `"readOnly": [false]` |

### Step 2: Severity classification matrix

| Event category | Severity | Rationale |
|---|---|---|
| CloudTrail tampering (DeleteTrail, StopLogging) | **CRITICAL** | Blinds all alerting; never suppress |
| Root login | **CRITICAL** | Root should never be used |
| IAM policy manipulation (AttachRolePolicy, CreatePolicyVersion) | **HIGH** | Privilege escalation vector |
| Access key creation | **HIGH** | Credential exfiltration vector |
| SG open ingress 0.0.0.0/0 | **HIGH** | Lateral movement vector |
| KMS key deletion | **HIGH** | Data loss vector |
| S3 bucket public access | **HIGH** | Data exposure |
| Console login failure (single) | **LOW** | Brute-force indicator (burst → HIGH) |
| Tag changes | **LOW** | Operational noise |
| Stack updates (CI/CD) | **SUPPRESSED** | Known automation, suppress by default |

**Decision rule:** default to **HIGH** unless ALL: (a) reversible within
5 minutes, (b) does not touch IAM policies/credentials, (c) does not
change network exposure, (d) actor is a known service role.

### Step 3: Lambda enrichment function

```python
import json, hashlib, boto3
from datetime import datetime, timedelta, timezone

cloudtrail = boto3.client('cloudtrail')
sns = boto3.client('sns')
ddb = boto3.resource('dynamodb').Table('CloudTrailAlertDedup')

SUPPRESSED_ROLES = [
    'arn:aws:sts::111111111111:assumed-role/cicd-deploy-role',
    'arn:aws:iam::111111111111:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling',
]
SEVERITY_TOPIC = {
    'CRITICAL': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-critical',
    'HIGH': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-high',
    'MEDIUM': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-medium',
    'LOW': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-low',
}

def lambda_handler(event, context):
    detail = event['detail']
    event_name = detail['eventName']
    actor_arn = detail.get('userIdentity', {}).get('arn', 'unknown')

    if actor_arn in SUPPRESSED_ROLES:
        return {'status': 'suppressed', 'reason': f'Known automation: {actor_arn}'}

    dedup_key = hashlib.md5(f'{event_name}|{actor_arn}'.encode()).hexdigest()
    ttl = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    try:
        ddb.put_item(Item={'dedupKey': dedup_key, 'ttl': ttl},
                     ConditionExpression='attribute_not_exists(dedupKey)')
    except Exception:
        return {'status': 'deduplicated'}

    lookback = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    enrichment = {'recent_events': []}
    try:
        resp = cloudtrail.lookup_events(
            LookupAttributes=[{'AttributeKey': 'Username',
                'AttributeValue': detail['userIdentity'].get('userName', '')}],
            StartTime=lookback, MaxResults=20)
        enrichment['recent_events'] = [
            {'eventName': e['EventName'], 'eventTime': e['EventTime'].isoformat()}
            for e in resp.get('Events', [])]
    except Exception as e:
        enrichment['lookup_error'] = str(e)

    severity = classify_severity(event_name, detail)
    enrichment.update(severity=severity,
        source_ip=detail.get('sourceIPAddress', 'unknown'),
        region=detail.get('awsRegion', 'unknown'),
        account_id=detail.get('recipientAccountId', detail.get('accountId')))

    topic = SEVERITY_TOPIC[severity]
    msg = json.dumps({'event_name': event_name, 'severity': severity,
        'actor': actor_arn, 'enrichment': enrichment, 'raw_event': detail},
        default=str)[:250000]
    sns.publish(TopicArn=topic, Message=msg, Subject=f'[{severity}] {event_name}')
    return {'status': 'alerted', 'severity': severity}

def classify_severity(event_name, detail):
    never_suppress = {'DeleteTrail', 'StopLogging', 'UpdateTrail', 'DeleteEventDataStore'}
    if event_name in never_suppress or detail.get('userIdentity', {}).get('type') == 'Root':
        return 'CRITICAL'
    high = {'AttachRolePolicy', 'DetachRolePolicy', 'CreatePolicyVersion', 'CreateAccessKey',
            'DeleteAccessKey', 'ScheduleKeyDeletion', 'PutBucketAcl', 'UpdateAccountPasswordPolicy'}
    if event_name in high:
        return 'HIGH'
    medium = {'AuthorizeSecurityGroupIngress', 'RevokeSecurityGroupIngress',
              'CreateSecurityGroup', 'DeleteSecurityGroup'}
    if event_name in medium:
        return 'MEDIUM'
    return 'LOW'
```

### Step 4: SNS routing by severity

```bash
for sev in critical high medium low; do
  aws sns create-topic --name cloudtrail-${sev}
  aws sns set-topic-attributes \
    --topic-arn arn:aws:sns:us-east-1:111111111111:cloudtrail-${sev} \
    --attribute-name DisplayName --attribute-value "CloudTrail-${sev}"
done
```

| Topic | Typical subscribers | Response SLA |
|---|---|---|
| cloudtrail-critical | PagerDuty, SMS, Slack #sec-incidents | Immediate |
| cloudtrail-high | Email security team, Slack #security | 1 hour |
| cloudtrail-medium | Slack #security, Security Hub dashboard | 1 business day |
| cloudtrail-low | Daily digest, S3 archive | Trend analysis |

### Step 5: Slack and Teams webhook delivery

Slack delivery Lambda (consumed from SQS for rate-limit safety):

```python
import json, urllib.request, os
WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']
def lambda_handler(event, context):
    for record in event['Records']:
        msg = json.loads(json.loads(record['body'])['Message'])
        sev = msg['severity']
        color = {'CRITICAL': '#FF0000', 'HIGH': '#FF8C00',
                 'MEDIUM': '#FFD700', 'LOW': '#36a64f'}
        payload = {'attachments': [{'color': color.get(sev, '#CCC'),
            'title': f'[{sev}] CloudTrail Alert',
            'fields': [
                {'title': 'Event', 'value': msg['event_name'], 'short': True},
                {'title': 'Actor', 'value': msg['actor'], 'short': True},
                {'title': 'Source IP', 'value': msg['enrichment'].get('source_ip'), 'short': True},
                {'title': 'Severity', 'value': sev, 'short': True}]}]}
        req = urllib.request.Request(WEBHOOK_URL,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
```

**Rate-limit mitigation:** SNS → SQS → Lambda consumer. SQS buffers
bursts; Lambda processes at 1 msg/second per webhook URL.

### Step 6: Security Hub custom findings

```python
import boto3, uuid
securityhub = boto3.client('securityhub')
def import_finding(detail, enrichment):
    sev_map = {'CRITICAL': 90.0, 'HIGH': 70.0, 'MEDIUM': 50.0, 'LOW': 20.0}
    fid = str(uuid.uuid5(uuid.NAMESPACE_DNS,
        f'{enrichment["account_id"]}-{detail["eventName"]}-{detail["eventTime"]}'))
    securityhub.batch_import_findings(Findings=[{
        'SchemaVersion': '2018-10-08', 'Id': fid,
        'ProductArn': f'arn:aws:securityhub:us-east-1:{enrichment["account_id"]}:product/default/default',
        'GeneratorId': 'cloudtrail-alert-automator',
        'AwsAccountId': enrichment['account_id'],
        'Types': ['Software and Configuration Checks/AWS Security Best Practices'],
        'CreatedAt': detail['eventTime'],
        'UpdatedAt': datetime.now(timezone.utc).isoformat(),
        'Severity': {'Label': enrichment['severity'], 'Normalized': sev_map[enrichment['severity']]},
        'Title': f'CloudTrail Alert: {detail["eventName"]}',
        'Description': f'{detail["eventName"]} by {enrichment.get("actor", "unknown")}',
        'Resources': [{'Type': 'AwsAccount', 'Id': f'aws://{enrichment["account_id"]}'}],
        'Workflow': {'Status': 'NEW'}
    }])
```

### Step 7: Deduplication logic

```bash
aws dynamodb create-table \
  --table-name CloudTrailAlertDedup \
  --attribute-definitions AttributeName=dedupKey,AttributeType=S \
  --key-schema AttributeName=dedupKey,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --time-to-live-specification AttributeName=ttl,Enabled=true
```

Dedup key: `MD5(eventName + "|" + actorArn + "|" + resourceId)`. TTL:
`now + dedup_window`.

| Event type | Window | Rationale |
|---|---|---|
| CI/CD stack updates | 30 min | Covers full deploy |
| Security group changes | 1 min | Each is individually actionable |
| Console login | 15 min | One alert per session |
| CloudTrail tampering | 0 (never) | Every event independently alerted |

### Step 8: Alert suppression for known automation

```bash
aws ssm put-parameter \
  --name /cloudtrail-alert/suppressed-roles \
  --type StringList \
  --value 'arn:aws:sts::111111111111:assumed-role/cicd-deploy-role,arn:aws:iam::111111111111:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling,arn:aws:iam::111111111111:role/aws-service-role/service-role/lambda.amazonaws.com/AWSServiceRoleForLambda'
```

**Suppression hygiene:**

- NEVER suppress `DeleteTrail`, `StopLogging`, or root events — even for
  known automation roles.
- NEVER suppress a broad pattern (`*:assumed-role/*`). Suppression is
  per-role-ARN only.
- Review the suppression list quarterly.
- Log every suppressed event to `cloudtrail-alert-suppressed` topic for
  auditability.

### Step 9: Multi-account via Organizations trail

Events from all member accounts arrive on the management account's bus:

```bash
aws events put-rule \
  --name cloudtrail-alert-org-iam-changes \
  --event-pattern '{
    "source": ["aws.iam"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventName": ["AttachRolePolicy", "CreateAccessKey"],
      "recipientAccountId": ["111111111111", "222222222222", "333333333333"]
    }
  }'
```

For per-account fan-out, forward to member account custom buses:

```bash
aws events put-targets \
  --rule cloudtrail-alert-org-iam-changes \
  --targets '[{"Id":"forward-to-member","Arn":"arn:aws:events:us-east-1:222222222222:event-bus/default","RoleArn":"arn:aws:iam::111111111111:role/EventBridgeCrossAccountForward"}]'
```

### Step 10: CloudTrail Lake for historical queries

```bash
# Create event data store
aws cloudtrail create-event-data-store \
  --name cloudtrail-alert-eds \
  --advanced-event-selectors '[{"Name":"MgmtEvents","FieldSelectors":[{"Field":"eventCategory","Equals":["Management"]}]}]'

# Query actor activity in last 24h
QUERY_ID=$(aws cloudtrail start-query \
  --query-statement "SELECT eventName, eventTime, sourceIPAddress FROM <EDS_ID> WHERE userIdentity.arn = ''arn:aws:iam::111111111111:user/suspicious'' AND eventTime > timestamp(''2026-08-10T00:00:00Z'')" \
  --query 'QueryId' --output text)
aws cloudtrail get-query-results --query-id $QUERY_ID
```

### Step 11: CloudTrail Insights anomaly alerting

```bash
aws cloudtrail put-insight-selectors \
  --trail-name management-events \
  --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'

aws events put-rule \
  --name cloudtrail-alert-insights \
  --event-pattern '{"source":["aws.cloudtrail"],"detail-type":["AWS API Call via CloudTrail Insights"],"detail":{"insightDetails":{"state":["Start"]}}}'
```

Route Insights to a SEPARATE topic — they are statistical anomalies, not
confirmed security events.

## Output format (STRICT output contract)

```text
ALERT: <reference>
EVENT: <event-name(s)>
RULE:
  - Pattern: <EventBridge event pattern summary>
  - Bus: default | custom
ENRICHMENT:
  - lookup-events: <15-min actor context>
  - Severity: CRITICAL | HIGH | MEDIUM | LOW
ROUTING:
  - SNS: <topic ARN by severity>
  - Security Hub: <configured | not configured>
  - Slack/Teams: <configured | not configured>
DEDUP:
  - Window: <minutes>
  - Key: <dedup key formula>
SUPPRESSION:
  - Roles: <suppressed role list>
  - Non-suppressible: DeleteTrail, StopLogging, root
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or IaC>
```

### Worked example — AUTOMATION_DEPLOYED, root login alert

```text
ALERT: root-login-prod
EVENT: ConsoleLogin (by root)
RULE:
  - Pattern: source=aws.signin, userIdentity.type=Root, eventName=ConsoleLogin, responseElements.ConsoleLogin=Success
  - Bus: default
ENRICHMENT:
  - lookup-events: 15-min lookback for root actor context
  - Severity: CRITICAL
ROUTING:
  - SNS: arn:aws:sns:us-east-1:111111111111:cloudtrail-critical
  - Security Hub: finding import configured (CRITICAL, NEW)
  - Slack: webhook configured (#sec-incidents)
DEDUP:
  - Window: 0 (never dedup root login)
  - Key: N/A
SUPPRESSION:
  - Roles: N/A — root events NEVER suppressed
  - Non-suppressible: DeleteTrail, StopLogging, root
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name cloudtrail-alert-root-login --event-pattern '{"source":["aws.signin"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"userIdentity":{"type":["Root"]},"eventName":["ConsoleLogin"],"responseElements":{"ConsoleLogin":["Success"]}}}'
```

### Worked example — REVIEW_REQUIRED, Security Hub not enabled

```text
ALERT: iam-change-alert
EVENT: AttachRolePolicy, DetachRolePolicy, CreatePolicyVersion
RULE:
  - Pattern: source=aws.iam, eventName=[AttachRolePolicy, DetachRolePolicy, CreatePolicyVersion]
  - Bus: default
ENRICHMENT:
  - lookup-events: configured, 15-min lookback
  - Severity: HIGH
ROUTING:
  - SNS: arn:aws:sns:us-east-1:111111111111:cloudtrail-high
  - Security Hub: NOT CONFIGURED — securityhub describe-hub returns ResourceNotFoundException
  - Slack: webhook configured (#security)
DEDUP:
  - Window: 5 minutes
  - Key: MD5(eventName|actorArn|resourceId)
SUPPRESSION:
  - Roles: cicd-deploy-role, CloudFormation StackSet role
  - Non-suppressible: DeleteTrail, StopLogging, root
VERDICT: REVIEW_REQUIRED
GAP: Security Hub is not enabled. Steps: (1) aws securityhub enable-security-hub; (2) update enrichment Lambda with BatchImportFindings call (Step 6); (3) re-deploy. SNS + Slack are operational.
```

## Anti-Patterns — NEVER do these things

- NEVER create an EventBridge rule for `ConsoleLogin` without filtering
  on `responseElements.ConsoleLogin: Success`. Without the filter, a
  brute-force scenario generates thousands of alerts per minute,
  exhausting Lambda concurrency and throttling ALL alerts including real
  security events.

- NEVER suppress `DeleteTrail`, `StopLogging`, `UpdateTrail`, or
  `DeleteEventDataStore` events. Even when the actor is a known
  automation role, these events blind the entire detection system. A
  compromised service role calling `StopLogging` is an active attack.

- NEVER use the same SNS topic for all severity levels. Routing CRITICAL
  (root login) and LOW (tag changes) to the same topic trains operators
  to ignore the topic. Always create at least 4 severity-tiered topics.

- NEVER omit the deduplication layer. Without dedup, a CI/CD pipeline
  deploying 50 stacks produces 50 identical alerts. Operators mute the
  channel, and the next real security event is invisible.

- NEVER hardcode Slack/Teams webhook URLs in Lambda source code. Store
  in Secrets Manager or Parameter Store. A webhook in source control is
  a credential leak.

- NEVER set the enrichment Lambda timeout below 10 seconds. The
  `lookup-events` API call can take 3-5 seconds under load. A 3-second
  timeout silently degrades to un-enriched alerts.

- NEVER deploy CloudTrail alerts in a single region only. Regional
  services emit regional CloudTrail events. An attacker calling
  `AttachRolePolicy` in `eu-west-1` goes undetected if the rule exists
  only in `us-east-1`. Deploy rules in all active regions or use an
  Organizations trail.

- NEVER use `lookup-events` for data-event enrichment. Data events are
  NOT returned by `lookup-events`. Use CloudTrail Lake with a data-event
  event data store. A silent assumption that `lookup-events` covers data
  events produces empty enrichment.

- NEVER create Security Hub findings without a deterministic `Id`.
  Random UUIDs per invocation produce orphaned findings that accumulate
  forever. Use `uuid5` with event identity for idempotent upserts.

- NEVER wire Slack webhook delivery directly from SNS without a queue.
  Slack enforces 1 message/second. A burst of 10 CRITICAL alerts
  produces `429` for 9. Use SNS → SQS → Lambda.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for event <event> in account
  <account>. Proceed? (yes/no)`

- **Verify CloudTrail is enabled.** `aws cloudtrail describe-trails
  --query 'trailList[?IsLogging==`true`]'`. A disabled trail means all
  alerting is dead configuration.

- **Test each EventBridge rule.** Use `aws events test-event-pattern`
  with a known CloudTrail event JSON before deploying to production.

- **For Security Hub integration, verify it is enabled.**
  `securityhub describe-hub`. `BatchImportFindings` fails silently when
  Security Hub is not enabled.

## Appendix A — Common CloudTrail alert patterns

| Category | source | eventName(s) | Severity | Suppressible |
|---|---|---|---|---|
| Root login | `aws.signin` | `ConsoleLogin` (root) | CRITICAL | No |
| IAM policy change | `aws.iam` | `AttachRolePolicy`, `DetachRolePolicy` | HIGH | Yes |
| Access key creation | `aws.iam` | `CreateAccessKey` | HIGH | Yes |
| SG change | `aws.ec2` | `AuthorizeSecurityGroupIngress` etc. | MEDIUM | Yes |
| Trail tampering | `aws.cloudtrail` | `DeleteTrail`, `StopLogging` | CRITICAL | NEVER |
| Login failure | `aws.signin` | `ConsoleLogin` (Failure) | LOW | Yes |
| KMS deletion | `aws.kms` | `ScheduleKeyDeletion` | HIGH | No |
| S3 ACL change | `aws.s3` | `PutBucketAcl` | HIGH | Yes |
| MFA deletion | `aws.iam` | `DeactivateMFADevice` | HIGH | No |
| Org leave | `aws.organizations` | `LeaveOrganization` | CRITICAL | NEVER |

## Appendix B — Decision tree

```
Is it a CloudTrail management event?
├─ Yes → Security-critical (root, IAM, trail tampering)?
│       ├─ Yes → CRITICAL, never suppress, 0-min dedup
│       └─ No  → Infrastructure change (SG, VPC)?
│               ├─ Yes → MEDIUM/HIGH, SNS, 1-min dedup
│               └─ No  → LOW, daily digest, 15-min dedup
└─ No  → Data event (S3, Lambda)? → Lake query, not lookup-events
```

## Recent AWS features (2024-2026)

- **CloudTrail Lake federated queries (2024-2025):** Query event data
  stores from Athena for cross-account investigation without export.
- **CloudTrail Insights on org trails (2024):** Anomalous API detection
  across all member accounts.
- **EventBridge global endpoints (2024-2025):** Multi-region failover
  for the event bus — critical for CloudTrail alerting resilience.
- **Security Hub custom actions (2024):** CloudTrail-triggered findings
  can now invoke SSM Automation for auto-isolation.
- **CloudTrail Lake partitioning (2025):** Automatic time/account
  partitioning for faster enrichment queries on large data stores.

## Expert heuristic: EventBridge event pattern for specific API calls + lookup-events enrichment for actor context + suppression list for service roles

The highest-leverage CloudTrail alerting pattern is a three-layer funnel:
precise EventBridge detection, context-rich enrichment, and aggressive
suppression of known automation. Each layer is independently necessary.

**The rule (non-negotiable):**

> ALWAYS build the alert as a three-stage funnel: (1) EventBridge event
> pattern matching ONLY the specific API calls (never broad wildcards),
> (2) Lambda enrichment calling lookup-events for the actor's 15-minute
> context, and (3) a suppression list of known service-role ARNs that is
> logged, versioned, and reviewed quarterly. Skipping any stage produces
> alert fatigue or missed critical events.

**Pattern selection techniques:**

| Technique | Mechanism | Impact |
|---|---|---|
| Explicit eventName list | `detail.eventName: ["AttachRolePolicy"]` | Zero false positives |
| readOnly filter | `"readOnly": [false]` | Eliminates Describe/List calls |
| userIdentity.type filter | `"userIdentity": {"type": ["Root"]}` | Isolates root events |
| responseElements filter | `"ConsoleLogin": ["Success"]` | Eliminates failure noise |
| recipientAccountId filter | Per-account routing in org trail | Account-scoped alerts |

**Suppression list maintenance:**

| Cadence | Action |
|---|---|
| On deploy | Seed with CI/CD, CFn, ASG roles |
| Monthly | Review for new service roles |
| Quarterly | Audit trust policies on suppressed roles |
| On incident | Temporarily remove ALL suppression |

**Surface in output:** include `SUPPRESSION_COUNT: <n>` and
`SUPPRESSION_AUDIT_TOPIC: <arn>`. If audit topic is missing, do NOT mark
the pipeline as deployable.

## Domain

AWS CloudOps / Governance Automation — CloudTrail-driven security alerting.

## AWS documentation

- **AWS CloudTrail** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html
- **Amazon EventBridge** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **CloudTrail Insights** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-insights-events.html
- **AWS Security Hub** — https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
