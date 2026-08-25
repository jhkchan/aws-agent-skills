# Advanced Patterns — CloudTrail Alert Automation

Load-on-demand deep dives for the CloudTrail Alert Automator skill: configuration
dependency graph, non-obvious behaviors, delivery and integration steps (Slack/Teams,
Security Hub, dedup, suppression, multi-account, Insights), and the condensed
decision-tree appendix.

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

## Step 0: Expert knowledge — non-obvious behaviors

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

## Step 5: Slack and Teams webhook delivery

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

## Step 6: Security Hub custom findings

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

## Step 7: Deduplication logic

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

## Step 8: Alert suppression for known automation

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

## Step 9: Multi-account via Organizations trail

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

## Step 11: CloudTrail Insights anomaly alerting

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
