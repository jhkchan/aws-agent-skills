# Advanced Patterns (load on demand) — Cost Anomaly Detection Automator

Expert-knowledge deep dives, Lambda recipes, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious Cost Anomaly behaviors (moved from SKILL.md)

- **Cost Anomaly Detection evaluates cost data daily, not in real time.**
  Anomalies are detected after the daily cost data refresh (8-24 hours
  behind real-time spend). A runaway Lambda function burning $1000/hour
  is NOT caught until the next daily cycle. For real-time protection,
  pair with CloudWatch billing alarms.

- **The ML model requires 10+ days of historical data per monitored
  dimension.** For new services, use Budgets as an interim static guard.

- **`create-anomaly-monitor` is async.** The API returns immediately
  with the monitor ARN, but the monitor state is `PENDING` for minutes.
  Poll `get-anomaly-monitors` until `monitorStatus` is `ACTIVE`. A
  subscription against a `PENDING` monitor silently fails to alert.

- **Severity is operator-defined, not AWS-defined.** The subscription
  `threshold` parameter controls sensitivity (percentage deviation).
  AWS does NOT classify anomalies as Critical/High/Low — the operator
  maps threshold percentages to severity. Recommended: threshold >= 50%
  = Critical, 20-50% = High, < 20% = Low.

- **`get-anomalies` returns `rootCauseService`.** This is ML-inferred,
  not always accurate — cross-reference with Cost Explorer contribution
  analysis before acting on auto-remediation.

- **Anomaly subscriptions support SNS, email, and Lambda targets.** SNS
  is the most flexible (fan-out to multiple endpoints). For any non-
  trivial pipeline, use SNS → Lambda.

- **Budgets and Cost Anomaly Detection alerts are independent.** Both
  can fire for the same event, or only one. Never assume one covers
  the other.

- **`provide-anomaly-feedback` is per-anomaly.** Each anomaly has a
  unique `anomalyId`. Bulk feedback is not supported. For high-volume
  accounts, build a Lambda that auto-submits feedback.

- **Dimension-based monitors filter by a single dimension value**
  (`LINKED_ACCOUNT`, `SERVICE`, `REGION`, `USAGE_TYPE`,
  `INSTANCE_TYPE`, etc.). A dimension-based monitor on `SERVICE=EC2`
  filters BEFORE ML evaluation; a service-level monitor evaluates ALL
  services and identifies the culprit via `rootCauseService`. Choose
  dimension-based for targeted monitoring; service-level for broad
  coverage.

- **Organizations Payer monitors cover ALL linked accounts.** A single
  monitor at the payer level detects anomalies across the entire org.
  More efficient than per-account monitors for large orgs, but requires
  routing logic to identify which linked account caused the anomaly.

---

## Step 5 — Auto-remediation Lambda (full code) (moved from SKILL.md)

```python
import json, boto3, os, urllib.request

ce = boto3.client('ce')
ec2 = boto3.client('ec2')
tagging = boto3.client('resourcegroupstaggingapi')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL', '')

def lambda_handler(event, context):
    for record in event['Records']:
        msg = json.loads(record['Sns']['Message'])
        anomaly_id = msg.get('anomalyId', '')
        root_cause = msg.get('rootCauseService', '')
        impact = msg.get('impact', {}).get('maxImpact', 0)
        severity = 'Critical' if impact >= 500 else 'High' if impact >= 100 else 'Low'

        if 'Elastic Compute Cloud' in root_cause:
            remediate_ec2(anomaly_id, severity)
        else:
            log_anomaly(anomaly_id, severity, root_cause)

        if SLACK_WEBHOOK and severity in ('Critical', 'High'):
            send_slack(anomaly_id, root_cause, impact, severity)
        submit_feedback(anomaly_id, is_true_positive=True)

def remediate_ec2(anomaly_id, severity):
    # 1. Tag untagged EC2 instances
    untagged = tagging.get_resources(ResourceTypeFilters=['ec2:instance'])
    for r in untagged.get('ResourceTagMappingList', []):
        tagging.tag_resources(ResourceARNList=[r['ResourceARN']],
                              Tags={'auto-remediated': 'true', 'anomaly-id': anomaly_id[:50]})
    # 2. Critical: shutdown non-prod instances
    if severity == 'Critical':
        instances = ec2.describe_instances(Filters=[
            {'Name': 'tag:Environment', 'Values': ['non-prod']},
            {'Name': 'instance-state-name', 'Values': ['running']}])
        ids = [i['InstanceId'] for r in instances['Reservations'] for i in r['Instances']]
        if ids:
            ec2.stop_instances(InstanceIds=ids)

def submit_feedback(anomaly_id, is_true_positive):
    try:
        ce.provide_anomaly_feedback(anomalyId=anomaly_id, isTruePositive=is_true_positive)
    except Exception as e:
        print(f"Feedback failed: {e}")

def send_slack(anomaly_id, root_cause, impact, severity):
    payload = json.dumps({'text': f':rotating_light: [{severity}] Cost Anomaly — {root_cause} — ${impact:.2f}'}).encode('utf-8')
    req = urllib.request.Request(SLACK_WEBHOOK, data=payload, headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req)

def log_anomaly(anomaly_id, severity, root_cause):
    print(json.dumps({'anomaly_id': anomaly_id, 'severity': severity, 'root_cause': root_cause}))
```

---

## Step 7 — Multi-account via Organizations Payer (moved from SKILL.md)

For multi-account coverage, create a monitor at the Payer level. This
single monitor detects anomalies across all linked accounts.

```bash
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "org-payer-anomaly-monitor",
    "MonitorType": "DIMENSION",
    "MonitorDimension": "SERVICE",
    "MonitorSpecification": "{\"Dimensions\":{\"Key\":\"LINKED_ACCOUNT\",\"Values\":[],\"MatchOptions\":[\"EQUALS\"]}}"
  }'
```

**Key constraint:** Cost Anomaly Detection must be configured from the
Payer account. Verify the caller's profile is the Payer before creating
monitors. For per-linked-account alerting, the Lambda router extracts
`accountId` from the anomaly event and routes to the appropriate
account-specific SNS topic.

---

## Step 8 — Slack and Teams webhook notifications (moved from SKILL.md)

```python
def format_slack_message(message):
    impact = message.get('impact', {}).get('maxImpact', 0)
    severity = 'Critical' if impact >= 500 else 'High' if impact >= 100 else 'Low'
    color = '#FF0000' if severity == 'Critical' else '#FFA500' if severity == 'High' else '#36a64f'
    return {'attachments': [{'color': color, 'title': f'AWS Cost Anomaly — {severity}',
        'fields': [
            {'title': 'Root Cause', 'value': message.get('rootCauseService', 'Unknown'), 'short': True},
            {'title': 'Impact', 'value': f"${impact:.2f}", 'short': True},
            {'title': 'Monitor', 'value': message.get('monitorName', 'Unknown'), 'short': True},
            {'title': 'Anomaly ID', 'value': message.get('anomalyId', 'Unknown'), 'short': True}]}]}
```

For Microsoft Teams, use an Adaptive Card payload and the Teams webhook
URL format (`https://outlook.office.com/webhook/...`).

---

## Step 9 — Submit anomaly feedback (moved from SKILL.md)

```bash
# Mark as true positive (confirmed real cost spike)
aws ce provide-anomaly-feedback --anomaly-id "<anomaly-id>" --is-true-positive true

# Mark as false positive (expected spend)
aws ce provide-anomaly-feedback --anomaly-id "<anomaly-id>" --is-true-positive false
```

Automated feedback rules in the Lambda router:

```python
FALSE_POSITIVE_SERVICES = ['AWS Premium Support', 'Tax']
TRUE_POSITIVE_THRESHOLD = 200

def should_auto_feedback(message):
    root_cause = message.get('rootCauseService', '')
    impact = message.get('impact', {}).get('maxImpact', 0)
    if any(fp in root_cause for fp in FALSE_POSITIVE_SERVICES):
        return False
    if impact >= TRUE_POSITIVE_THRESHOLD:
        return True
    return None  # manual review
```

---

## Step 10 — Analyze anomalies via Cost Explorer (moved from SKILL.md)

```bash
# Cost breakdown by service for the anomaly period
aws ce get-cost-and-usage \
  --time-period Start=2026-08-05,End=2026-08-11 \
  --granularity DAILY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter '{"Dimensions":{"Key":"LINKED_ACCOUNT","Values":["111111111111"]}}'

# Cost breakdown by usage type for the root-cause service
aws ce get-cost-and-usage \
  --time-period Start=2026-08-05,End=2026-08-11 \
  --granularity DAILY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Compute Cloud - Compute"]}}'
```

Use contribution analysis to confirm the anomaly's `rootCauseService`
before acting on auto-remediation.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Cost Anomaly Detection contribution analysis (2024-2025):**
  Enhanced anomaly payloads include contribution breakdown by
  dimension. Top contributing dimension values (service, usage type,
  linked account) reduce manual Cost Explorer deep-dives.

- **Anomaly feedback API GA (2024):** `provide-anomaly-feedback` is GA.
  Enables automated feedback from Lambda routers, closing the ML
  improvement loop programmatically.

- **Budgets with Budget Actions (2024-2025):** Budgets can trigger IAM
  policy application, SSM execution, or EC2 stop on breach. Provides a
  hard-limit remediation path complementing Anomaly Detection.

- **Multi-account anomaly routing (2025-2026):** Payer-level monitors
  now include richer linked-account context in the anomaly payload.

---

## Expert heuristic: anomaly detection coverage gaps (moved from SKILL.md)

The most dangerous coverage gap is "monitor exists but alerts go
nowhere." An operator creates a Cost Anomaly Monitor (the API succeeds),
assumes coverage exists, and never creates the subscription. Anomalies
are detected — they appear in the console — but no alert is ever
delivered.

**The rule (non-negotiable):**

> A monitor without a subscription is NOT coverage. It is silent
> detection. ALWAYS pair `create-anomaly-monitor` with
> `create-anomaly-subscription` and verify the subscription with
> `get-anomaly-subscriptions` before considering the pipeline deployed.

**Verification protocol:**

| Check | Command | Expected |
|---|---|---|
| Monitor active | `get-anomaly-monitors --monitor-arn-list <arn>` | `monitorStatus: ACTIVE` |
| Subscription exists | `get-anomaly-subscriptions` | `status: ACTIVE` |
| SNS topic policy | `sns get-topic-attributes --topic-arn <arn>` | Includes `events.costanomaly.amazonaws.com` |
| Lambda invocation | CloudTrail `Lambda Invoke` from SNS | Non-zero in 24h |
| Feedback submitted | `get-anomalies --feedback True` | Non-zero count |

**Pre-production validation (3-cycle rule):**

1. **Cycle 1 — Notify-only in non-prod:** Deploy monitor + subscription
   + Slack. Plant a deliberate cost spike. Verify notification within
   24 hours.
2. **Cycle 2 — Auto-remediation in non-prod:** Deploy Lambda with
   tagging-only. Plant a spike from untagged resources. Verify tagging
   and feedback.
3. **Cycle 3 — Production notify-only:** Deploy in production with
   notify-only. Monitor 2 weeks. If false-positive rate < 10%, enable
   auto-remediation for non-prod resources.

**Surface in the output:** for any recommended pipeline, include
`COVERAGE_STATUS: <monitor-active | subscription-active | sns-policy-
verified | lambda-invoking | feedback-loop-active>` and
`VALIDATION_STATUS: <notify-only-nonprod | remediation-nonprod |
notify-only-prod | full-prod>`.
