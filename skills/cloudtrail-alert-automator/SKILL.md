---
name: cloudtrail-alert-automator
description: Designs and deploys CloudTrail alerting automation across an AWS estate. Builds EventBridge rules for security-critical API calls (root console login, IAM policy changes, security group modifications, CloudTrail disabling), wires SNS topic routing by severity, deploys Lambda enrichment functions that use lookup-events to attach actor context, source IP correlation, and recent activity. Integrates with Security Hub via BatchImportFindings, delivers to Slack/Teams via webhook, implements deduplication by event identity, and suppresses known CI/CD service-role alerts. Supports multi-account via Organizations trail and CloudTrail Insights anomaly alerting. Emits AUTOMATION_DEPLOYED with deployable IaC or REVIEW_REQUIRED with the specific gap.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline alert-design. Live deployment uses aws events put-rule, put-targets, aws sns create-topic, subscribe, aws lambda create-function, aws securityhub batch-import-findings, and aws cloudtrail lookup-events, create-event-data-store, start-query — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Designing CloudTrail alerting automation, wiring EventBridge rules for security-critical API calls, building Lambda enrichment with lookup-events context, integrating CloudTrail alerts with Security Hub custom findings, routing alerts to Slack or Teams, suppressing known CI/CD automation noise, or deploying multi-account CloudTrail alerting via an Organizations trail.
  activation_triggers: automate CloudTrail alerts, EventBridge rule for root login, IAM change alert, security group change notification, CloudTrail SNS alert, Security Hub custom finding from CloudTrail, CloudTrail Lake query, Slack webhook CloudTrail, alert deduplication, suppress CI/CD service role alerts, CloudTrail Insights anomaly, Organizations trail alerting
  invocation_schema: 'Input: either (a) a set of CloudTrail event names or categories to alert on plus the desired notification targets (SNS, Security Hub, Slack, Teams), OR (b) an existing alerting setup to audit. Output: deterministic ALERT block per rule — RULE/ENRICHMENT/ROUTING/DEDUP/ SUPPRESSION/VERDICT — where VERDICT is AUTOMATION_DEPLOYED or REVIEW_REQUIRED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS CloudTrail, EventBridge, SNS alerting, Security Hub, lookup-events, CloudTrail Lake, CloudTrail Insights, root login alert, IAM change alert, security group change, Slack webhook, alert deduplication, alert suppression, Organizations trail, governance automation
  tags: aws-cloudtrail, eventbridge, sns, security-hub, lambda, governance, automate
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

## Process — Alert pipeline design (apply in order)

### Step 0: Expert knowledge — non-obvious behaviors

Full catalog: [Advanced patterns](references/advanced-patterns.md) — data events, root identity, ConsoleLogin failures, org-trail routing, throttling, rate limits.

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

Common EventBridge pattern errors (never fires, wrong events, missed regions): [Error handling](references/error-handling.md).

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

Slack/Teams delivery Lambda: [Advanced patterns](references/advanced-patterns.md).

### Step 6: Security Hub custom findings

Security Hub BatchImportFindings implementation: [Advanced patterns](references/advanced-patterns.md).

### Step 7: Deduplication logic

Dedup table setup, key formula, window matrix: [Advanced patterns](references/advanced-patterns.md).

### Step 8: Alert suppression for known automation

Suppression list parameter and hygiene rules: [Advanced patterns](references/advanced-patterns.md).

### Step 9: Multi-account via Organizations trail

Org-trail rule and cross-account fan-out: [Advanced patterns](references/advanced-patterns.md).

### Step 10: CloudTrail Lake for historical queries

Event data store and actor-activity query CLI: [Diagnostic commands](references/diagnostic-commands.md).

### Step 11: CloudTrail Insights anomaly alerting

Insight selectors and Insights rule CLI: [Advanced patterns](references/advanced-patterns.md).

## Output format (STRICT output contract)

### Literal output labels

Every alert design MUST emit exactly one block per rule using the labels
`ALERT_NAME:`, `EVENT:`, `VERDICT:`, `CHECKLIST:`, `GAP:`, and `TEMPLATE:`.
Do NOT preface with prose.

```text
ALERT_NAME: <alert reference name>
EVENT: <CloudTrail eventName(s)>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] EventBridge rule: <rule name + pattern summary>
  [✓|✗] Lambda enrichment: <function ARN, lookup-events lookback>
  [✓|✗] SNS topic: <topic ARN by severity>
  [✓|✗] Security Hub finding: <configured | not configured>
  [✓|✗] Slack/Teams webhook: <configured | not configured>
  [✓|✗] Deduplication: <window minutes, key formula>
  [✓|✗] Suppression list: <role ARNs | N/A>
  [✓|✗] Non-suppressible events enforced: DeleteTrail, StopLogging, root
GAP: <specific missing piece or None>
TEMPLATE: <CLI snippet or IaC>
```

### FORBIDDEN — NEVER do these

1. NEVER create an EventBridge rule for `ConsoleLogin` without filtering
   on `responseElements.ConsoleLogin: Success`. Without the filter a
   brute-force scenario generates thousands of alerts per minute,
   exhausting Lambda concurrency and throttling real security events.

2. NEVER suppress `DeleteTrail`, `StopLogging`, `UpdateTrail`, or
   `DeleteEventDataStore` events. Even when the actor is a known
   automation role, these events blind the entire detection system.
   A compromised service role calling `StopLogging` is an active attack.

3. NEVER use the same SNS topic for all severity levels. Routing
   CRITICAL (root login) and LOW (tag changes) to the same topic trains
   operators to ignore alerts. Always create at least 4 severity-tiered
   topics.

4. NEVER omit the deduplication layer. Without dedup a CI/CD pipeline
   deploying 50 stacks produces 50 identical alerts. Operators mute the
   channel, and the next real security event is invisible.

5. NEVER hardcode Slack/Teams webhook URLs in Lambda source code. Store
   in Secrets Manager or Parameter Store. A webhook committed to source
   control is a credential leak.

6. NEVER set the enrichment Lambda timeout below 10 seconds. The
   `lookup-events` API call can take 3-5 seconds under load. A 3-second
   timeout silently degrades to un-enriched alerts.

7. NEVER wire Slack webhook delivery directly from SNS without a queue.
   Slack enforces 1 message/second per URL. A burst of 10 alerts
   produces `429 Too Many Requests` for 9. Use SNS → SQS → Lambda.

### Worked example — root-login alert with full enrichment

Scenario: root console login in production account. EventBridge detects
the `ConsoleLogin` event by `userIdentity.type: Root`. Lambda enrichment
adds 15-minute actor context via `lookup-events`, classifies as CRITICAL,
publishes to the critical SNS topic, creates a Security Hub finding, and
sends a formatted Slack alert.

```text
ALERT_NAME: root-login-prod
EVENT: ConsoleLogin (by root)
VERDICT: AUTOMATION_DEPLOYED
CHECKLIST:
  [✓] EventBridge rule: cloudtrail-alert-root-login
      pattern: {"source":["aws.signin"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"userIdentity":{"type":["Root"]},"eventName":["ConsoleLogin"],"responseElements":{"ConsoleLogin":["Success"]}}}
  [✓] Lambda enrichment: arn:aws:lambda:us-east-1:111111111111:function:cloudtrail-enrichment
      lookup-events: 15-min lookback for root actor recent API calls
      severity classification: CRITICAL (userIdentity.type == Root → always CRITICAL)
  [✓] SNS topic: arn:aws:sns:us-east-1:111111111111:cloudtrail-critical
  [✓] Security Hub finding: configured (BatchImportFindings, Severity CRITICAL/90.0, deterministic Id via uuid5)
  [✓] Slack webhook: configured (#sec-incidents, via SQS → Lambda consumer for rate-limit safety)
  [✓] Deduplication: window 0 min (never dedup root login), key N/A
  [✓] Suppression list: N/A — root events NEVER suppressed
  [✓] Non-suppressible events enforced: DeleteTrail, StopLogging, root
GAP: None
TEMPLATE:
  aws events put-rule --name cloudtrail-alert-root-login \\
    --event-pattern '{"source":["aws.signin"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"userIdentity":{"type":["Root"]},"eventName":["ConsoleLogin"],"responseElements":{"ConsoleLogin":["Success"]}}}'
  aws events put-targets --rule cloudtrail-alert-root-login \\
    --targets '[{"Id":"enrichment","Arn":"arn:aws:lambda:us-east-1:111111111111:function:cloudtrail-enrichment","InputTransformer":{"InputPathsMap":{"detail":"$.detail"},"InputTemplate":"{\"detail\": <detail>}"}}]'
```

This example's artifacts (Slack payload JSON, deployed enrichment Lambda): [Worked examples](references/worked-examples.md).

### Decision tree

```text
Is the CloudTrail event a management event?
├─ Yes → Security-critical (root login, trail tampering, org leave)?
│        ├─ Yes → CRITICAL, never suppress, 0-min dedup
│        │        Route: SNS critical topic + Security Hub finding + Slack #sec-incidents
│        └─ No → Infrastructure change (SG, VPC, KMS)?
│                 ├─ Yes → HIGH/MEDIUM, suppressible by known roles, 1-5 min dedup
│                 │        Route: SNS high/medium topic + Slack #security
│                 └─ No → LOW (tags, login failure, read-only)
│                          Route: SNS low topic + daily digest
└─ No → Data event (S3, Lambda)? → Not covered by lookup-events
         Use CloudTrail Lake query for enrichment
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

## References (load on demand)

- [Worked examples](references/worked-examples.md) — root-login worked-example artifacts (Slack payload, deployed enrichment Lambda)
- [Error handling](references/error-handling.md) — EventBridge pattern error table and webhook rate-limit mitigation
- [Diagnostic commands](references/diagnostic-commands.md) — CloudTrail Lake event-data-store and query CLI
- [Advanced patterns](references/advanced-patterns.md) — dependency graph, non-obvious behaviors, delivery and integration steps, decision-tree appendix, recent features
- [EventBridge event patterns](references/eventbridge-event-patterns.md) — event pattern library reference

## Domain

AWS CloudOps / Governance Automation — CloudTrail-driven security alerting.

## AWS documentation

- **AWS CloudTrail** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html
- **Amazon EventBridge** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **CloudTrail Insights** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-insights-events.html
- **AWS Security Hub** — https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
