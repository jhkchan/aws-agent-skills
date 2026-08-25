---
name: cost-anomaly-detection-automator
description: Designs and implements automated AWS Cost Anomaly Detection workflows spanning Cost Anomaly Monitor creation (service-level, linked account, dimension-based monitor), anomaly alert subscription (SNS topic, email recipient, Lambda webhook), severity-based anomaly routing (Critical = page on-call, High = notify channel, Low = log to dashboard), auto-remediation Lambda functions (tag untagged resources, right-size over-provisioned instances, shutdown non-production environments after-hours), AWS Budgets integration for hard spend limits with threshold alerts, Cost Explorer anomaly analysis for deep-dive on detected anomalies, multi-account coverage via Organizations Payer monitor, Slack and Microsoft Teams webhook notifications, anomaly feedback submission (true positive versus false positive) to improve ML model accuracy, and historical baseline establishment using contribution analysis. Emits AUTOMATION_DEPLOYED with a fully wired monitor-alert- remediation pipeline or REVIEW_REQUIRED with the specific...
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws ce create-anomaly-monitor, create-anomaly-subscription, get-anomalies, provide-anomaly-feedback, aws budgets create-budget, and aws ce get-cost-and-usage — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Building cost anomaly detection automation, creating Cost Anomaly Monitors (service, linked-account, or dimension-based), wiring severity-routed alert subscriptions, integrating Budgets hard-limits with anomaly detection, deploying auto-remediation Lambda for spend spikes, setting up multi-account coverage via Organizations Payer, or adding Slack/Teams webhook notifications for cost anomalies.
  activation_triggers: automate cost anomaly detection, create Cost Anomaly Monitor, create-anomaly-subscription, severity routing cost anomaly, Budgets integration anomaly, auto-remediation cost spike, tag untagged resources Lambda, Organizations Payer anomaly, Slack webhook cost alert, anomaly feedback true positive
  invocation_schema: 'Input: either (a) a cost anomaly detection requirement ("alert on EC2 spend spikes", "auto-tag untagged resources causing cost anomalies"), OR (b) an existing Cost Anomaly Monitor configuration to extend with severity routing or auto-remediation. Output: deterministic ANOMALY block per monitor — MONITOR/SUBSCRIPTION/ROUTING/REMEDIATION/AUDIT/ VERDICT — where VERDICT is AUTOMATION_DEPLOYED (pipeline ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Cost Anomaly Detection, Cost Anomaly Monitor, Anomaly Subscription, AWS Budgets, Cost Explorer, contribution analysis, service-level monitor, linked account monitor, Organizations Payer, severity routing, auto-remediation Lambda, tag untagged resources, Slack webhook, anomaly feedback, FinOps
  tags: aws-cost-anomaly-detection, aws-budgets, cost-explorer, finops, auto-remediation, anomaly-detection, automate
---

# Cost Anomaly Detection Automator

## Mindset

**One-line takeaway:** cost anomaly automation is a four-stage pipeline —
**detect** (Cost Anomaly Monitor uses ML on historical spend) → **alert**
(anomaly subscription routes to SNS, email, or Lambda webhook) → **react**
(severity-based routing: Critical = page, High = notify, Low = log) →
**remediate** (Lambda auto-remediation: tag untagged resources, right-size,
shutdown non-prod). A gap in ANY stage produces silent cost leakage.

- **Detection** without **subscription** is invisible: the monitor
  detects anomalies but no alert is emitted. This is the most common
  misconfiguration — operators create the monitor and forget the
  subscription.
- **Cost Anomaly Detection and AWS Budgets are complementary, not
  redundant.** Cost Anomaly Detection uses ML on historical spend patterns.
  Budgets use static thresholds. Service-level monitors catch per-service
  spikes; account-level monitors catch total spend. Use both.
- **Severity routing is the operator's lever.** Critical anomalies page
  the on-call; High anomalies notify a Slack channel; Low anomalies log
  to a dashboard. Without severity routing, every anomaly pages — or
  worse, none do because the team muted everything.

## Quick navigation

| You want to... | Go to |
|---|---|
| Create a service-level Cost Anomaly Monitor | Step 2 + Appendix A |
| Decide monitor type (service vs linked-account vs dimension) | Step 1 + Step 2 |
| Wire anomaly subscription with severity routing | Step 3 + Step 4 |
| Build auto-remediation Lambda for cost spikes | Step 5 |
| Integrate Budgets for hard limits | Step 6 |
| Set up multi-account via Organizations Payer | Step 7 |
| Add Slack or Teams webhook notifications | Step 8 |
| Submit anomaly feedback (true/false positive) | Step 9 |
| Analyze a detected anomaly via Cost Explorer | Step 10 |
| Avoid common pitfall patterns | Anti-Patterns |
| Recent features (contribution analysis, feedback) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **A Cost Anomaly Monitor without a subscription detects anomalies
   silently.** `create-anomaly-monitor` creates the detection engine;
   `create-anomaly-subscription` creates the alert delivery. Separate
   API calls. Operators frequently create the monitor and assume alerts
   are wired. Always pair them and verify with
   `get-anomaly-subscriptions`.
2. **Cost Anomaly Detection needs at least 10 days of data to establish
   a baseline.** A brand-new account or a newly enabled service has
   insufficient history. The first 10 days are a warm-up period with
   reduced sensitivity.
3. **Budgets are static thresholds; Cost Anomaly Detection is dynamic
   (ML-based).** Budgets catch "we spent more than $X total." Anomaly
   Detection catches "EC2 spend on Tuesday is 3x the normal pattern."
   Never substitute one for the other — use both.
4. **Service-level and account-level monitors catch DIFFERENT
   anomalies.** A service-level monitor on EC2 catches an EC2 spike even
   if total account spend looks normal. An account-level monitor catches
   total spend deviations regardless of which service caused them.
   Deploy both for full coverage.
5. **Anomaly feedback improves the ML model.** `provide-anomaly-feedback`
   with `isTruePositive: true|false` trains the model to reduce false
   positives over time. Without feedback, false positive rate stays flat.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Account ID or Payer ID | `aws organizations list-accounts` | Scope of monitor |
| Monitor type | Service, linked-account, or dimension-based | Detection granularity |
| Target service(s) | `aws ce get-cost-and-usage --group-by Type=DIMENSION,Value=SERVICE` | For service-level monitors |
| SNS topic ARN | `aws sns create-topic` | Alert delivery endpoint |
| Lambda function ARN | `aws lambda create-function` | Auto-remediation endpoint |
| Existing monitors | `aws ce get-anomaly-monitors` | Don't duplicate |
| Existing subscriptions | `aws ce get-anomaly-subscriptions` | Don't overwrite blindly |
| Existing budgets | `aws budgets describe-budgets --account-id <id>` | Check before creating new |
| Slack/Teams webhook URL | Incoming webhook config | Notification channel |

**If the input is malformed** (missing account ID, ambiguous monitor
type), emit:

```text
ANOMALY: <reference>
MONITOR: <monitor-name>
VERDICT: ERROR
REASON: Cannot design anomaly pipeline — account ID and monitor type are required.
GAP: Re-supply the account ID, desired monitor type, and target service or dimension.
```

## Process — Pipeline design (apply in order)

### Step 0: Expert knowledge — non-obvious Cost Anomaly behaviors

Step 0 expert knowledge (daily-not-real-time evaluation, 10-day ML warm-up, async monitor PENDING state, operator-defined severity thresholds, rootCauseService accuracy, SNS/email/Lambda targets, Budgets independence, per-anomaly feedback, dimension vs service monitors, Payer coverage) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before designing the pipeline..

### Step 1: Classify the monitoring requirement

| Requirement | Monitor type | Example |
|---|---|---|
| Catch total spend deviations | `DIMENSION` on `PAYER_ACCOUNT` | "Alert if total monthly spend spikes" |
| Catch per-service spikes | `DIMENSION` on `SERVICE` | "Alert if EC2 or S3 spend spikes" |
| Catch per-account spend (multi-account) | `DIMENSION` on `LINKED_ACCOUNT` | "Alert if linked account 2222 spend spikes" |
| Catch per-region/instance-type spikes | `DIMENSION` on `REGION` or `INSTANCE_TYPE` | "Alert if GPU instance spend spikes" |
| Broad ML-based detection across all services | `DIMENSION` on `SERVICE` (all values) | Default Coverage monitor |

If ambiguous, default to `DIMENSION` on `SERVICE` for the top 3 services
by spend (query Cost Explorer to identify them).

### Step 2: Create the Cost Anomaly Monitor

```bash
# Service-level monitor (EC2)
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "ec2-spend-anomaly-monitor",
    "MonitorType": "DIMENSION",
    "MonitorDimension": "SERVICE",
    "MonitorSpecification": "{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Compute Cloud - Compute\"],\"MatchOptions\":[\"EQUALS\"]}}"
  }'
```

Linked-account monitor:

```bash
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "linked-account-2222-anomaly",
    "MonitorType": "DIMENSION",
    "MonitorDimension": "LINKED_ACCOUNT",
    "MonitorSpecification": "{\"Dimensions\":{\"Key\":\"LINKED_ACCOUNT\",\"Values\":[\"222222222222\"],\"MatchOptions\":[\"EQUALS\"]}}"
  }'
```

Verify the monitor is ACTIVE before proceeding:

```bash
aws ce get-anomaly-monitors \
  --monitor-arn-list <monitor-arn> \
  --query 'AnomalyMonitors[0].[MonitorName,MonitorType,MonitorStatus]'
```

If `MonitorStatus` is `PENDING`, wait and re-check. A subscription
against a `PENDING` monitor silently fails to alert.

### Step 3: Create the anomaly subscription with severity routing

Severity routing is achieved by creating multiple subscriptions with
different thresholds targeting different endpoints.

```bash
# Critical: threshold >= 50% -> SNS topic that pages on-call
aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "SubscriptionName": "critical-cost-anomaly",
    "Threshold": 50.0,
    "Frequency": "IMMEDIATE",
    "MonitorArn": "<monitor-arn>",
    "Subscribers": [
      {"Address": "arn:aws:sns:us-east-1:111111111111:critical-cost-alerts", "Type": "SNS"}
    ]
  }'

# High: threshold >= 20% -> SNS topic that notifies Slack
aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "SubscriptionName": "high-cost-anomaly",
    "Threshold": 20.0,
    "Frequency": "DAILY",
    "MonitorArn": "<monitor-arn>",
    "Subscribers": [
      {"Address": "arn:aws:sns:us-east-1:111111111111:high-cost-alerts", "Type": "SNS"}
    ]
  }'
```

**Severity threshold mapping (recommended starting point):**

| Severity | Threshold | Frequency | Routing |
|---|---|---|---|
| Critical | >= 50% deviation | IMMEDIATE | Page on-call (PagerDuty via SNS) |
| High | 20-50% deviation | DAILY | Slack/Teams notification via SNS → Lambda |
| Low | < 20% deviation | WEEKLY | Log to dashboard; no active notification |

Step 3 subscription-creation error table (ValidationException on PENDING monitor, AccessDeniedException, LimitExceededException, no-alerts SNS policy) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when the subscription API fails..

### Step 4: Wire SNS fan-out for multi-channel routing

SNS is the recommended subscriber type — it fans out to Lambda, email,
SQS, and HTTPS webhooks from a single subscription.

```bash
aws sns create-topic --name critical-cost-alerts

# Lambda subscriber for severity routing and Slack formatting
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:critical-cost-alerts \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:cost-anomaly-router
```

SNS topic policy — allow Cost Anomaly Detection to publish:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.costanomaly.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:111111111111:critical-cost-alerts"
  }]
}
```

A missing topic policy entry for `events.costanomaly.amazonaws.com` is
the single most common cause of "subscription created but no alerts
received."

### Step 5: Build the auto-remediation Lambda

The Lambda receives the SNS message containing the anomaly JSON and
performs remediation based on the root cause.

Step 5 auto-remediation Lambda (full Python: severity from maxImpact, EC2 tag-and-stop remediation, Slack notify, auto feedback) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when building the remediation function..

**Decision rule:** default to **notify-only** unless ALL of the
following are true: (a) the remediation is reversible within 15
minutes, (b) the Lambda has been tested in non-production, (c) the
remediation is scoped to non-prod resources (or has an explicit
production-impact assessment), (d) the action is logged to CloudTrail.

### Step 6: Integrate AWS Budgets for hard limits

Budgets complement anomaly detection with static thresholds.

Step 6 create-budget CLI (ACTUAL 80% + FORECASTED 100% notifications with SNS subscribers) moved verbatim to [references/budgets-and-anomaly-integration.md](references/budgets-and-anomaly-integration.md).
Load on demand when wiring Budgets hard limits..

| Dimension | Cost Anomaly Detection | AWS Budgets |
|---|---|---|
| Detection method | ML on historical patterns | Static threshold |
| Sensitivity | Dynamic (adapts to trends) | Fixed (operator-defined) |
| Best for | Unexpected pattern deviations | Hard spend limits |
| False positive rate | Decreases with feedback | Zero (threshold is exact) |

### Step 7: Multi-account via Organizations Payer

Step 7 Payer-level monitor CLI and the Payer-account constraint + per-linked-account Lambda routing moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for multi-account coverage..

### Step 8: Slack and Teams webhook notifications

The Lambda router formats and sends notifications. Configure the webhook
URL as a Lambda environment variable.

Step 8 Slack message formatter (severity-colored attachments) and Teams Adaptive Card note moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when wiring webhooks..

### Step 9: Submit anomaly feedback

Step 9 provide-anomaly-feedback CLI and automated feedback rules (false-positive service list, impact threshold) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when closing the feedback loop..

### Step 10: Analyze anomalies via Cost Explorer

Step 10 Cost Explorer breakdown queries (by service, by usage type for the root-cause service) and contribution-analysis confirmation moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when deep-diving a detected anomaly..

## Output format

```text
ANOMALY: <reference>
MONITOR:
  - Name: <monitor-name>
  - Type: DIMENSION (SERVICE | LINKED_ACCOUNT | REGION)
  - Status: ACTIVE | PENDING
  - Scope: <service or account coverage>
SUBSCRIPTION:
  - Severity routing: Critical (>=50%), High (20-50%), Low (<20%)
  - Endpoints: SNS topic(s), email(s), Lambda ARN(s)
  - Frequency: IMMEDIATE | DAILY | WEEKLY
ROUTING:
  - Critical: <on-call page mechanism>
  - High: <Slack/Teams notification>
  - Low: <dashboard log>
REMEDIATION:
  - Actions: <tag untagged, right-size, shutdown non-prod, notify-only>
  - Lambda: <function ARN or "NOT WIRED">
  - Scope: <production | non-production | all>
  - Safety: <dry-run, approval gate, production-impact assessment>
AUDIT:
  - Budgets: <budget name(s) and threshold(s)>
  - Feedback: <auto-feedback rules>
  - Baseline: <trailing 90-day average>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet for the monitor + subscription>
```

### Worked example — AUTOMATION_DEPLOYED, EC2 service-level monitor

```text
ANOMALY: ec2-spend-anomaly
MONITOR:
  - Name: ec2-spend-anomaly-monitor
  - Type: DIMENSION (SERVICE=Amazon Elastic Compute Cloud - Compute)
  - Status: ACTIVE
  - Scope: EC2 spend in account 111111111111
SUBSCRIPTION:
  - Severity routing: Critical (>=50%), High (20-50%), Low (<20%)
  - Endpoints: SNS arn:aws:sns:us-east-1:111111111111:critical-cost-alerts
  - Frequency: IMMEDIATE for Critical, DAILY for High
ROUTING:
  - Critical: SNS → Lambda → PagerDuty + Slack #finops-critical
  - High: SNS → Lambda → Slack #finops-alerts
  - Low: CloudWatch dashboard log
REMEDIATION:
  - Actions: tag untagged EC2 instances; shutdown non-prod if Critical
  - Lambda: arn:aws:lambda:us-east-1:111111111111:function:cost-anomaly-router
  - Scope: non-production only (production = notify-only)
  - Safety: dry-run tagging; production-impact assessment before shutdown
AUDIT:
  - Budgets: monthly-cost-budget ($10K, 80% actual, 100% forecast)
  - Feedback: auto-true-positive for impact >= $200
  - Baseline: trailing 90-day EC2 average $2,340/day
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws ce create-anomaly-monitor --anomaly-monitor '{"MonitorName":"ec2-spend-anomaly-monitor","MonitorType":"DIMENSION","MonitorDimension":"SERVICE","MonitorSpecification":"{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Compute Cloud - Compute\"],\"MatchOptions\":[\"EQUALS\"]}}"}'
  aws ce create-anomaly-subscription --anomaly-subscription '{"SubscriptionName":"critical-cost-anomaly","Threshold":50.0,"Frequency":"IMMEDIATE","MonitorArn":"<monitor-arn>","Subscribers":[{"Address":"arn:aws:sns:us-east-1:111111111111:critical-cost-alerts","Type":"SNS"}]}'
```

### Worked example — REVIEW_REQUIRED, monitor without subscription

Worked example — REVIEW_REQUIRED, monitor without subscription (NOT-WIRED routing/remediation/audit rows) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the REVIEW_REQUIRED output shape..

## Anti-Patterns — NEVER do these things

- NEVER create a Cost Anomaly Monitor without a corresponding anomaly
  subscription. The monitor detects; the subscription delivers. Without
  the subscription, anomalies are detected silently — operators believe
  coverage exists but receive zero alerts.

- NEVER substitute AWS Budgets for Cost Anomaly Detection or vice versa.
  Budgets use static thresholds; Anomaly Detection uses ML on patterns.
  They catch different anomaly classes. Use both.

- NEVER expect real-time anomaly detection. Cost Anomaly Detection
  evaluates daily data (8-24 hour lag). For real-time protection, pair
  with CloudWatch billing alarms.

- NEVER configure auto-remediation Lambda for production resources
  without an impact assessment. A Critical anomaly that triggers
  `stop_instances` on production EC2 causes an immediate outage. Scope
  auto-remediation to non-prod by default.

- NEVER omit the SNS topic policy entry for
  `events.costanomaly.amazonaws.com`. Without this principal, Cost
  Anomaly Detection cannot publish to the SNS topic. The subscription
  appears correct but no alerts are ever delivered.

- NEVER assume the `rootCauseService` field is always accurate. It is
  ML-inferred. Cross-reference with Cost Explorer contribution analysis
  before acting on auto-remediation.

- NEVER skip anomaly feedback submission. Without feedback, the ML
  model never improves its false-positive rate. Alert fatigue increases
  and operators mute all anomaly alerts.

- NEVER create a dimension-based monitor with a dimension value that
  does not exist in Cost Explorer billing data. The monitor is created
  successfully but never detects anomalies (zero cost data). Always
  verify the dimension value via `get-cost-and-usage` first.

- NEVER deploy a single subscription for all severity levels. A
  threshold of 10% floods the on-call with low-impact anomalies. Create
  separate subscriptions per severity tier.

- NEVER assume a Payer-level monitor provides per-linked-account alert
  routing. The Lambda router must extract `accountId` from the payload
  and route accordingly.

- NEVER set the auto-remediation Lambda timeout below 60 seconds.
  Tagging resources and calling EC2 APIs take time. A 3-second default
  timeout produces partial remediation with no retry.

- NEVER forget to verify the monitor's `monitorStatus` is `ACTIVE`
  before creating subscriptions. A subscription against a `PENDING`
  monitor silently fails.

- NEVER omit the Lambda DLQ for the auto-remediation Lambda. Failed
  invocations are lost without a DLQ. Configure SQS DLQ and alarm on
  queue depth.

- NEVER use `Frequency: IMMEDIATE` for all severity tiers. Reserve
  `IMMEDIATE` for Critical; use `DAILY` for High and `WEEKLY` for Low.

- NEVER create Budgets without verifying existing budgets first. AWS
  Budgets has per-account limits. Always call `describe-budgets` before
  `create-budget`.

## Pre-flight safety checks (run before applying any pipeline CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for account <account>. This affects
  <consequence>. Proceed? (yes/no)`

- **Back up the current configuration** before modifying:
  `aws ce get-anomaly-monitors > /tmp/monitors-backup-$(date +%s).json`
  `aws ce get-anomaly-subscriptions > /tmp/subscriptions-backup-$(date +%s).json`

- **Before deploying auto-remediation Lambda**, test against a synthetic
  anomaly event in non-production. Verify tagging, right-sizing, and
  shutdown actions execute correctly.

- **Before enabling Critical-severity auto-remediation**, verify the
  tagging policy correctly identifies non-prod resources. A mistagged
  production instance is treated as non-prod and shut down.

- **For multi-account deployments**, verify the Lambda IAM role has
  cross-account AssumeRole permissions for each linked account.

## Appendix A — Monitor type comparison

Appendix A monitor-type comparison table (service-level, linked-account, region, instance-type, all-services) moved verbatim to [references/cost-anomaly-monitor-types.md](references/cost-anomaly-monitor-types.md).
Load on demand when choosing a monitor type..

## Appendix B — Decision tree

```
Is real-time cost protection required?
├─ Yes → Cost Anomaly Detection alone is NOT sufficient.
│        Add CloudWatch billing alarms + Cost Anomaly Detection.
└─ No  → Single account or multi-account?
        ├─ Single → Create service-level + account-level monitors.
        └─ Multi  → Create Payer-level monitor + per-account routing.

For each monitor:
  Auto-remediation required?
  ├─ Yes → Reversible within 15 min?
  │       ├─ Yes → Tested in non-prod? ── Yes → DEPLOY Lambda (Step 5)
  │       │                                └── No → REVIEW_REQUIRED
  │       └─ No  → REVIEW_REQUIRED (destructive; manual gate)
  └─ No  → Notify-only (SNS + Slack). AUTOMATION_DEPLOYED.
```

## Recent AWS features (2024-2026)

Recent AWS features (contribution analysis, feedback API GA, Budget Actions, multi-account routing context) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing recent setups..

## Expert heuristic: anomaly detection coverage gaps

Expert heuristic deep dive (monitor-without-subscription rule, verification protocol table, 3-cycle pre-production validation, COVERAGE_STATUS / VALIDATION_STATUS output fields) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before declaring the pipeline deployed..

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, Steps 5/7/8/9/10 recipes (remediation Lambda, Payer monitor, Slack/Teams, feedback, Cost Explorer), Recent AWS features, and the coverage-gap expert heuristic moved from SKILL.md.
- [references/worked-examples.md](references/worked-examples.md) — the REVIEW_REQUIRED worked example moved from SKILL.md.
- [references/error-handling.md](references/error-handling.md) — the Step 3 subscription error table moved from SKILL.md.
- [references/budgets-and-anomaly-integration.md](references/budgets-and-anomaly-integration.md) — now also holds the Step 6 Budgets hard-limit CLI moved from SKILL.md.
- [references/cost-anomaly-monitor-types.md](references/cost-anomaly-monitor-types.md) — now also holds the Appendix A monitor-type comparison moved from SKILL.md.

## Domain

AWS CloudOps / FinOps Automation — Cost Anomaly Detection and Budgets.

## AWS documentation

- **AWS Cost Anomaly Detection** — https://docs.aws.amazon.com/cost-management/latest/userguide/ad-acm.html
- **AWS Budgets** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- **Cost Explorer API** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-api.html
- **Anomaly Feedback API** — https://docs.aws.amazon.com/cost-management/latest/userguide/anomaly-subscriptions.html
- **Budget Actions** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html
