---
name: cost-anomaly-response-automator
description: >-
  Designs automated AWS cost-anomaly detection and response workflows
  across AWS Cost Anomaly Detection (CAD) monitors (service, linked
  account, daily/weekly/monthly cadence), anomaly subscriptions (SNS),
  automated response patterns (EventBridge to Lambda: notify Slack or
  Teams, tag suspect resources, trigger a Budgets action), AWS Budgets
  cost-budget auto-actions (IAM policy attach, EC2 stop), Cost Explorer
  anomaly views, and CUR (Cost and Usage Report) analysis automation
  (Athena top-spenders queries). Layers in the latest: CAD with ML
  impact evaluation, Amazon Q cost-optimization recommendations, and
  Budgets advanced actions. Enforces guardrails: dry-run first,
  human-approval gate for any resource-stopping action, scoped IAM,
  idempotency, full CloudTrail audit. Emits AUTOMATED with response
  plan or MANUAL_STEP_REQUIRED with the specific gap. Use when wiring
  Cost Anomaly Detection or Budgets to a notification or remediation
  pipeline.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan authoring. Live
  deployment uses aws ce create-anomaly-monitor, create-anomaly-
  subscription, get-anomalies; aws budgets create-budget,
  put-budget-action; aws cur describe-report-definitions; aws athena
  start-query-execution; aws sns create-topic / subscribe; aws
  events put-rule / put-targets; aws lambda create-function; aws
  resourcegroupstaggingapi tag-resources; aws cost-optimization-hub
  get-recommendations. Requires AWS CLI v2 with ce, budgets, cur,
  athena, sns, events, lambda, iam, ec2, s3, and
  resourcegroupstaggingapi access (SSO or key-based).
keywords:
  - Cost Anomaly Detection
  - CAD
  - AWS Budgets
  - cost budget
  - budget action
  - anomaly subscription
  - SNS alert
  - Cost Explorer
  - Cost and Usage Report
  - CUR
  - Athena top spenders
  - Amazon Q cost optimization
  - EventBridge
  - Lambda remediation
  - Slack notification
  - Teams notification
  - FinOps
  - cost governance
  - EC2 stop budget action
  - IAM policy budget action
  - spend automation
tags:
  - finops
  - cost-anomaly
  - budgets
  - automation
  - cost-explorer
  - cur
  - eventbridge
  - lambda
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: FinOps
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATED | MANUAL_STEP_REQUIRED"
  when_to_use: >-
    Designing an automated cost-anomaly response for AWS, wiring Cost
    Anomaly Detection or AWS Budgets to a notification (Slack, Teams,
    email) or remediation (tag suspect resources, attach an IAM deny
    policy, stop EC2), building the CUR Athena top-spenders query that
    feeds the response pipeline, layering Amazon Q cost-optimization
    recommendations onto anomaly alerts, or hardening an existing
    spend-response workflow with dry-run, approval gate, and audit.
  when_not_to_use:
    - "Manual cost triage — this skill designs automation; use a human-driven cost review for one-off investigations."
    - "RI/SP purchasing strategy — commitment decisions are strategic; use a Savings Plan negotiation skill, not a real-time response pipeline."
    - "Billing accuracy disputes — use AWS Support; this skill automates response, not charge correction."
    - "Showback/chargeback reporting — use CUR + Athena + QuickSight; this skill is for anomaly response, not periodic reporting."
  activation_triggers:
    - "automate cost anomaly response"
    - "Cost Anomaly Detection to Slack"
    - "Budgets action on cost overrun"
    - "SNS alert on spend anomaly"
    - "EventBridge Lambda cost remediation"
    - "stop EC2 on budget breach"
    - "IAM deny policy budget action"
    - "CUR Athena top spenders"
    - "Amazon Q cost optimization"
    - "cost budget auto-action"
    - "tag resources on anomaly"
    - "anomaly subscription SNS"
  invocation_schema:
    type: object
    required: [detection_source, response_scope]
    properties:
      detection_source:
        type: enum
        enum: [cad, budgets, ce-anomaly, cur, q-recommendations]
        description: The detection source that triggers the workflow.
      response_scope:
        type: enum
        enum: [notify, tag, budget-action, full-playbook, cur-analysis]
        description: Which response phases to automate.
      severity_threshold:
        type: number
        description: USD impact (CAD) or % of budget (Budgets). Default 100 USD / 80%.
      existing_workflow:
        type: object
        description: Existing EventBridge rule + Lambda or Step Functions definition. When provided, runs the guardrail + audit gate.
    output: >-
      Deterministic block: DETECTION_SOURCE / RESPONSE_SCOPE / VERDICT /
      WORKFLOW / GUARDRAILS / AUDIT / FINDINGS / REMEDIATION. VERDICT is
      AUTOMATED when complete with dry-run, scoped IAM, approval gate
      before resource-stopping actions, and CloudTrail-auditable record;
      MANUAL_STEP_REQUIRED when a guardrail or coverage gate fails.
---

# Cost Anomaly Response Automator

## What this skill does

Designs automated AWS cost-anomaly response workflows that move a
spend spike from detection to actionable notification (or scoped
remediation) without human latency. Supports five detection sources
(Cost Anomaly Detection, AWS Budgets, Cost Explorer anomaly view, CUR
Athena analysis, Amazon Q cost-optimization recommendations), five
response patterns (notify, tag, budget-action, CUR top-spenders
drill-down, full-playbook), and three orchestration surfaces
(EventBridge + Lambda, EventBridge + Step Functions, Budgets native
actions).

The verdict is binary: **AUTOMATED** when the workflow is complete,
includes dry-run, has scoped IAM, lands an approval gate before any
resource-stopping action, and writes a CloudTrail-auditable record;
**MANUAL_STEP_REQUIRED** when any guardrail or coverage gate fails,
with the specific gap enumerated in FINDINGS.

## STRICT output contract

Every invocation MUST emit exactly one design or validation block in
this shape — no prose before, no commentary after:

```text
DETECTION_SOURCE: <cad | budgets | ce-anomaly | cur | q-recommendations>
RESPONSE_SCOPE: <notify | tag | budget-action | cur-analysis | full-playbook>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
WORKFLOW:
  Detection: <monitor or budget name + ARN>
  EventBridge rule: <name or "n/a (Budgets native)">
  Lambda / Step Functions: <arn or name>
  Budgets action: <action name or "none">
  SNS topic: <arn>
  Notification target: <Slack / Teams / email / PagerDuty>
GUARDRAILS:
  - [PASS|FAIL] Dry-run mode implemented
  - [PASS|FAIL] Approval gate before resource-stopping action
  - [PASS|FAIL] Scoped IAM (least privilege)
  - [PASS|FAIL] Idempotency check on Lambda
  - [PASS|FAIL] Kill-switch (Parameter Store or EventBridge disable)
AUDIT:
  - [PASS|FAIL] CloudTrail covers the account
  - [PASS|FAIL] Notification includes anomaly ID + impact USD
  - [PASS|FAIL] Budgets action execution logged
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command>
```

A block missing VERDICT, GUARDRAILS, or REMEDIATION is a contract
violation — re-emit the full block.

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [STRICT output contract](#strict-output-contract) | Confirm the exact block shape before emitting |
| 2 | [Decision tree](#decision-tree--orchestration-selection) | Picking the right orchestration surface |
| 3 | [Detection sources](#detection-sources) | CAD / Budgets / CE / CUR / Q |
| 4 | [Response patterns](#response-patterns) | Notify / tag / budget-action / CUR |
| 5 | [Step Functions orchestration](#step-functions-orchestration) | Multi-phase full-playbook |
| 6 | [Guardrails](#guardrails-mandatory) | Dry-run, approval gate, kill-switch |
| 7 | [Output format](#output-format--worked-examples) | Full AUTOMATED and MANUAL_STEP_REQUIRED examples |
| 8 | [NEVER anti-patterns](#never-these-things) | Top taboos for spend-response automation |
| 9 | [Expert heuristic](#expert-heuristic--the-60-second-triage) | The 60-second design triage |
| 10 | [Recent AWS features](#recent-aws-features-2024-2026) | What changed in CAD/Budgets/Q in 24 months |

## Mindset

**One-line takeaway:** spend-response automation trades blast radius
for speed — a fast wrong action (stopping every EC2 instance in prod)
is more expensive than the anomaly you are trying to contain. The
workflow's job is to surface the spike; the guardrail's job is to
ensure the automation does not amplify the damage.

Three facts shape every cost-anomaly automation decision:

- **Notification is reversible; remediation is not.** Posting a Slack
  message is reversible. Attaching an IAM deny policy is reversible.
  Stopping an EC2 instance causes an outage. Terminating is
  irreversible. Default to notify + tag; require a human-approval gate
  before any availability-affecting action.
- **CAD detects anomalies on a 6-24 hour lag, not in real time.** CAD
  evaluates daily or weekly cadences; the spike at 09:00 UTC likely
  started 12-24 hours ago. Budgets are similar. Near-real-time
  detection requires CloudWatch billing alarms (4h poll) or
  CUR/Athena on a schedule.
- **The kill-switch is more important than the trigger.** A workflow
  that fires on every CAD anomaly above USD 100 is fine if scoped.
  Without a kill-switch, a misconfigured monitor, load test, or
  marketing launch can trigger dozens of actions per hour.

## Pre-flight: spec gate (run before generation)

| Attribute | Required | Effect on plan |
|---|---|---|
| `detection_source` | YES | Determines the EventBridge source or Budgets native trigger |
| `response_scope` | YES | Determines the actions (notify only, full-playbook, etc.) |
| `severity_threshold` | Recommended | USD impact (CAD) or % of budget (Budgets). Default 100 USD / 80%. |
| `target_regions` | Recommended | Cost is global; Budgets actions are per-region. |
| `approval_required` | RECOMMENDED | Required true if response_scope includes budget-action with stop. |
| `existing_workflow` | For validation | Skip generation; run guardrail + audit gates. |

**If the spec is incomplete**, emit:

```text
DETECTION_SOURCE: <unknown>
RESPONSE_SCOPE: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>).
REQUIRED:
  - detection_source (cad | budgets | ce-anomaly | cur | q-recommendations)
  - response_scope (notify | tag | budget-action | cur-analysis | full-playbook)
REMEDIATION: Provide both fields. Example: "notify Slack on any CAD
  anomaly above USD 500" maps to detection_source=cad,
  response_scope=notify, severity_threshold=500.
```

**Live-account pre-flight (skip for offline authoring):**
1. `aws ce get-anomaly-monitors` (CAD enabled).
2. `aws cur describe-report-definitions` (CUR exists).
3. SNS topic exists or is in the template.
4. Lambda role has `ce:GetAnomalies` (read) + scoped action perms.
5. `aws budgets describe-budgets --account-id <payer>` (Budgets enabled).

## Decision tree — orchestration selection

Apply top-to-bottom. First matching rule wins.

```
START
  |
  +-- notify only? -------------> EventBridge rule + Lambda
  |                               (Lambda formats and posts to Slack/Teams/email)
  +-- tag resources? -----------> EventBridge rule + Lambda
  |                               (Lambda calls resourcegroupstaggingapi:TagResources)
  +-- budget-action? -----------> AWS Budgets native action
  |                               (IAM policy attach, EC2 stop, SNS notify)
  +-- cur-analysis? ------------> EventBridge schedule + Lambda/Athena
  |                               (Athena top-spenders, post summary to Slack)
  +-- full-playbook? -----------> EventBridge rule + Step Functions
  |                               (notify -> tag -> wait for approval -> action)
  +-- q-recommendations? -------> EventBridge schedule + Lambda
  |                               (poll Q, dedupe, post to Slack)
  +-- (unrecognized) -----------> MANUAL_STEP_REQUIRED with mapping hint
```

**Orchestration surface selection:**

- **Lambda-only:** single-action responses <15 min (Lambda max).
  Cheapest and simplest.
- **Step Functions:** multi-phase, parallel, or approval-gated
  responses. Required when a destructive action needs an approval gate.
- **Budgets native actions:** IAM policy attach and EC2 stop triggered
  directly by budget breach. No EventBridge wiring; limited to a
  single threshold and a single action per budget.
- **Athena scheduled query:** CUR top-spenders on a schedule. Athena
  writes to S3; a Lambda posts the summary to Slack.

## Step 0: Expert knowledge — non-obvious cost behaviors

- **CAD evaluates daily or weekly, not in real time.** An anomaly at
  09:00 UTC Tuesday reflects spend through Monday end-of-day. For
  near-real-time, use CloudWatch billing alarms (4h poll) or
  CUR/Athena hourly.
- **CAD `Impact.TotalImpact` is the dollar deviation, not total spend.**
  An Impact of USD 500 means spend deviated USD 500 from baseline —
  total spend could be much higher. Filter on Impact for severity but
  include actual spend in the notification.
- **AWS Budgets evaluates every ~8-12 hours.** A budget at 80% may
  not fire until 85-90%. Pair with CAD for finer-grained detection.
- **Budgets `TimeUnit=MONTHLY` resets on the calendar month.** A
  budget set on the 15th covers only half a month. Use
  `TimePeriod.Start` to align with the billing cycle.
- **Budgets actions have a single threshold per action.** A budget
  can have multiple actions (notify at 80%, IAM deny at 100%), but
  each is a separate `put-budget-action` call. A common mistake:
  setting one action at 80% that both notifies AND stops EC2, instead
  of two actions at 80% and 100%.
- **`BudgetsAction` IAM policy applies to users/roles, NOT root.** It
  attaches a deny-all policy to specified IAM principals. Does not
  affect root or federated identities outside the listed principals.
- **`BudgetsAction` EC2 stop targets specific instances and regions.**
  It does NOT stop all EC2 globally. Specify exact instance IDs and
  regions in `SubscriberResourceList`. A misconfigured action silently
  does nothing if instances don't match.
- **CUR delivery latency is 8-24 hours.** A CUR for yesterday lands in
  S3 between 08:00-24:00 UTC today. An Athena query at 06:00 UTC runs
  against stale data; schedule for 12:00 UTC or later.
- **CUR Athena needs Glue partitions.** A CUR report in S3 is
  partitioned by `year/month`. The Athena table must use
  `PARTITIONED BY (year string, month string)` and partitions loaded
  via `MSCK REPAIR TABLE`. A new CUR without partitions returns zero
  rows.
- **SNS subscription must be confirmed before delivery.** A new SNS
  topic with an unconfirmed email/HTTPS subscription silently drops
  messages. Always send a test message.
- **Slack/Teams needs an incoming webhook or Lambda.** SNS does not
  natively post to Slack. Pattern: SNS -> Lambda -> webhook POST.
  Store the webhook URL in Parameter Store (or Secrets Manager for
  tokens) — never hardcode.
- **EventBridge does not natively emit events for CAD anomalies.**
  CAD surfaces via SNS subscriptions (CAD -> SNS -> Lambda).
  EventBridge schedules drive CUR/Athena and Q recommendation polling.
- **Amazon Q cost recommendations are account-scoped.** Q Business
  returns recommendations for the account it is deployed in. For
  multi-account, deploy Q in each member or use Cost Optimization Hub
  (`aws cost-optimization-hub get-recommendations`).
- **Cost Optimization Hub dedupes by resource ARN.** A Lambda polling
  daily must dedupe by `recommendationId` to avoid re-posting. Track
  last-seen in DynamoDB or Parameter Store.
- **CAD `MonitorType=CUSTOM` uses an Expression (MetricSource), not a
  service filter.** Service monitors (`SERVICE`) filter by AWS service
  name. Linked account monitors (`LINKED_ACCOUNT`) monitor member
  accounts.

## Detection sources

### AWS Cost Anomaly Detection (CAD)

```bash
aws ce get-anomaly-monitors --output json  # list existing

# Service monitor for EC2 spend
aws ce create-anomaly-monitor --anomaly-monitor '{
  "MonitorName": "ec2-spend-monitor", "MonitorType": "SERVICE",
  "MonitorSpecification": "{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Compute Cloud - Compute\"]}}"
}'

# Linked account monitor
aws ce create-anomaly-monitor --anomaly-monitor '{
  "MonitorName": "member-111122223333-monitor", "MonitorType": "LINKED_ACCOUNT",
  "MonitorSpecification": "{\"Dimensions\":{\"Key\":\"LINKED_ACCOUNT\",\"Values\":[\"111122223333\"]}}"
}'

# Anomaly subscription wired to SNS (threshold USD 100, daily)
TOPIC_ARN=$(aws sns create-topic --name cost-anomaly-alerts --output text)
aws ce create-anomaly-subscription --anomaly-subscription '{
  "Name": "prod-cost-anomaly-sub", "Threshold": 100.0, "Frequency": "DAILY",
  "MonitorArnList": ["<monitor-arn>"],
  "Subscribers": [{"Address": "'"$TOPIC_ARN"'", "Type": "SNS"}]
}'

aws ce get-anomalies --monitor-arn <monitor-arn> \
  --start-date 2026-08-01 --end-date 2026-08-10 --output json
```

### AWS Budgets

```bash
aws budgets create-budget --account-id 111122223333 --budget '{
  "BudgetName": "monthly-ec2-budget", "BudgetType": "COST", "TimeUnit": "MONTHLY",
  "BudgetLimit": {"Amount": "10000", "Unit": "USD"},
  "CostFilters": {"Service": ["Amazon Elastic Compute Cloud - Compute"]}
}'

# Notify at 80% via SNS
aws budgets create-notification --account-id 111122223333 \
  --budget-name monthly-ec2-budget \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' \
  --subscribers SubscriptionType=SNS,Address=<topic-arn>

# IAM deny policy action at 100% (ApprovalModel=AUTOMATIC OK for reversible)
aws budgets put-budget-action --account-id 111122223333 --budget-name monthly-ec2-budget \
  --notification-type ACTUAL --action-type APPLY_IAM_POLICY \
  --action-threshold ActionThresholdValue=100,ActionThresholdType=PERCENTAGE \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111122223333:policy/BudgetDenyAll","Roles":["BillingAlertDenyRole"]}}' \
  --execution-role-arn arn:aws:iam::111122223333:role/BudgetActionRole --approval-model AUTOMATIC

# EC2 stop action at 120% (ApprovalModel=MANUAL — destructive)
aws budgets put-budget-action --account-id 111122223333 --budget-name monthly-ec2-budget \
  --notification-type ACTUAL --action-type RUN_SSM_DOCUMENTS \
  --action-threshold ActionThresholdValue=120,ActionThresholdType=PERCENTAGE \
  --definition '{"SsmActionDefinition":{"ActionSubType":"STOP_EC2_INSTANCES","Region":"us-east-1","InstanceIds":["i-0abc12345"]}}' \
  --execution-role-arn arn:aws:iam::111122223333:role/BudgetActionRole --approval-model MANUAL
```

### Cost Explorer anomaly view

Cost Explorer surfaces anomalies in the console under "Cost Anomaly
Detection". The same data is available via `aws ce get-anomalies`. CE
is the visualization; CAD is the engine. Use `get-anomalies`
programmatically and surface in your own dashboard or Slack via
Lambda.

### CUR analysis automation

```bash
aws cur describe-report-definitions --output json  # verify CUR configured
```

**Top-spenders Athena query (schedule daily via EventBridge):**

```sql
SELECT lineitem_product_servicename AS service, resource_id,
       SUM(lineitem_unblendedcost) AS spend
FROM "cur"."cur_table"
WHERE year = '2026' AND month = '08'
  AND lineitem_lineitemtype IN ('Usage', 'DiscountedUsage')
GROUP BY 1, 2
HAVING SUM(lineitem_unblendedcost) > 100
ORDER BY spend DESC LIMIT 20;
```

```bash
aws events put-rule --name cur-daily-top-spenders \
  --schedule-expression "cron(0 12 * * ? *)" --state ENABLED
aws events put-targets --rule cur-daily-top-spenders \
  --targets '{"Id":"1","Arn":"arn:aws:lambda:us-east-1:111122223333:function:cur-top-spenders"}'
```

### Amazon Q cost-optimization recommendations

```bash
# Cost Optimization Hub (Org-level)
aws cost-optimization-hub get-recommendations \
  --filter '{"implementAfterTimestamp": 0}' --max-results 50 --output json
# Lambda (scheduled) polls, dedupes by recommendationId, posts to Slack
```

## Response patterns

### 1. Notify (Slack / Teams / email / PagerDuty)

```python
import json, urllib.request, os
def lambda_handler(event, context):
    webhook = os.environ['SLACK_WEBHOOK_URL']  # from Parameter Store
    record = json.loads(event['Records'][0]['Sns']['Message'])
    impact = record.get('Impact', {}).get('TotalImpact', 'unknown')
    service = record.get('Impact', {}).get('Services', [{}])[0].get('ServiceName', 'unknown')
    msg = {'text': (
        f":moneybag: *Cost Anomaly*\nImpact: ${impact}\n"
        f"Service: {service}\nAnomaly ID: {record.get('AnomalyId','unknown')}\n"
        f"Account: {record.get('AccountId','unknown')}")}
    urllib.request.urlopen(urllib.request.Request(
        webhook, json.dumps(msg).encode(), {'Content-Type': 'application/json'}))
```

### 2. Tag suspect resources

```python
import boto3, json, os
tag_api = boto3.client('resourcegroupstaggingapi')
def lambda_handler(event, context):
    record = json.loads(event['Records'][0]['Sns']['Message'])
    anomaly_id = record['AnomalyId']
    resources = json.loads(os.environ['SUSPECT_RESOURCES'])  # populated by Step Functions CUR query
    tag_api.tag_resources(ResourceARNList=resources,
                          Tags={'CostAnomaly': anomaly_id, 'Investigate': 'true'})
```

### 3. Budgets native actions

Budgets actions run in the Budgets service — no EventBridge or Lambda
for the action itself. Use `APPLY_IAM_POLICY` for soft containment
(deny new resource creation) and `RUN_SSM_DOCUMENTS` with
`STOP_EC2_INSTANCES` for hard containment.

### 4. CUR top-spenders drill-down

```python
import boto3
athena = boto3.client('athena')
def lambda_handler(event, context):
    query = '''SELECT lineitem_product_servicename, resource_id,
           SUM(lineitem_unblendedcost) AS spend
    FROM "cur"."cur_table"
    WHERE year='{y}' AND month='{m}'
    GROUP BY 1, 2 HAVING SUM(lineitem_unblendedcost) > 100
    ORDER BY spend DESC LIMIT 20'''.format(y='2026', m='08')
    return {'QueryExecutionId': athena.start_query_execution(
        QueryString=query, QueryExecutionContext={'Database': 'cur'},
        ResultConfiguration={'OutputLocation': 's3://cur-athena-results-us-east-1/'}
    )['QueryExecutionId']}
```

### 5. Full-playbook (Step Functions)

```json
{
  "StartAt": "CheckKillSwitch",
  "States": {
    "CheckKillSwitch": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ssm:get-parameter",
      "Parameters": {"Name": "/cost/kill-switch"},
      "Next": "KillChoice"
    },
    "KillChoice": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.Parameter.Value", "StringEquals": "disabled", "Next": "Abort"}],
      "Default": "NotifySlack"
    },
    "Abort": {"Type": "Succeed"},
    "NotifySlack": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:cost-notify-slack",
      "Next": "TagResources"
    },
    "TagResources": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:cost-tag-resources",
      "Next": "WaitForApproval"
    },
    "WaitForApproval": {
      "Comment": "Human callback via SQS task token",
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Parameters": {
        "QueueUrl": "https://sqs.<region>.amazonaws.com/<account>/cost-approval",
        "MessageBody": {"anomalyId.$": "$.anomalyId", "impact.$": "$.impact", "taskToken.$": "$$.Task.Token"}
      },
      "Next": "ActionOrClose"
    },
    "ActionOrClose": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.decision", "StringEquals": "act", "Next": "RunBudgetAction"}],
      "Default": "CloseIncident"
    },
    "RunBudgetAction": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:cost-budget-action",
      "Next": "CloseIncident"
    },
    "CloseIncident": {"Type": "Succeed"}
  }
}
```

## Step Functions orchestration

For full-playbook cost response (multi-phase, approval-gated), use
Step Functions. The state machine above orchestrates the canonical
pattern: kill-switch check -> notify -> tag -> wait for approval ->
optional action -> close.

| Pattern | Use when | Trade-off |
|---|---|---|
| `Wait` state with fixed duration | One-shot timer ("wait 1h, then auto-stop") | Stays "Running"; clutters dashboard |
| `Task` with `waitForTaskToken` | Human callback via SQS/CLI | Pauses cleanly; resumes on callback |

Always prefer task-token callback for human approval gates.

## Guardrails (MANDATORY)

Every cost-anomaly automation MUST include:

1. **A kill-switch checked BEFORE any action.** Parameter Store
   (`/cost/kill-switch`), Lambda guard, or EventBridge rule disable.
2. **Dry-run mode for the first deployment.** Set the workflow to
   notify-only for 1-2 weeks; promote to actions after.
3. **An approval gate before any resource-stopping action.** Use Step
   Functions `Task` with `waitForTaskToken` and an SQS queue.
4. **Scoped IAM roles.** `ce:GetAnomalies` (read), `sns:Publish` on
   the topic, `resourcegroupstaggingapi:TagResources` on specific
   ARNs — NOT `*:*` on `*`.
5. **Idempotency.** Handle multiple triggers for the same anomaly.
   Use `AnomalyId` as the dedupe key (DynamoDB or Parameter Store).
6. **No destructive actions without explicit approval.** Notification,
   tagging, IAM deny (reversible) are allowed without approval. EC2
   stop/terminate, resource deletion require an approval gate.

```bash
# Kill-switch pattern
aws ssm put-parameter --name /cost/kill-switch --value "enabled" --type String
aws ssm put-parameter --name /cost/kill-switch --value "disabled" \
  --type String --overwrite  # one-command disable
```

## Output format — worked examples

### Worked example — AUTOMATED full-playbook

```text
DETECTION_SOURCE: cad
RESPONSE_SCOPE: full-playbook
VERDICT: AUTOMATED
WORKFLOW:
  Detection: ec2-spend-monitor (arn:aws:ce::111122223333:anomalymonitor/abc-123)
  Anomaly subscription: prod-cost-anomaly-sub (threshold USD 100, daily)
  SNS topic: arn:aws:sns:us-east-1:111122223333:cost-anomaly-alerts
  Lambda: cost-notify-slack, cost-tag-resources, cost-budget-action
  Step Functions: arn:aws:states:us-east-1:111122223333:stateMachine:cost-full-playbook
  Budgets action: monthly-ec2-budget (IAM deny 100%, EC2 stop 120%)
  Kill-switch: Parameter Store /cost/kill-switch
GUARDRAILS:
  - [PASS] Dry-run 2026-07-15 to 2026-07-29 (14 days, notify-only)
  - [PASS] Approval gate via SQS task token before EC2 stop
  - [PASS] Lambda role scoped to ce:GetAnomalies, sns:Publish,
          resourcegroupstaggingapi:TagResources, budgets:ExecuteBudgetAction
  - [PASS] Idempotency: DynamoDB cost-anomaly-dedupe keyed by AnomalyId
  - [PASS] Kill-switch checked first in state machine
AUDIT:
  - [PASS] CloudTrail org trail covers 111122223333
  - [PASS] Slack notification includes AnomalyId, Impact USD, Service
  - [PASS] Budgets action execution logged; tagged CostAnomaly=<AnomalyId>
FINDINGS:
  - [INFO] SNS subscription confirmed; CAD evaluates daily (6-24h latency)
  - [WARN] CUR/Athena top-spenders query runs on a 12h delay
REMEDIATION: aws cloudformation deploy --stack-name prod-cost-workflow \
  --template-file cost-workflow.yaml --capabilities CAPABILITY_NAMED_IAM
```

### Worked example — MANUAL_STEP_REQUIRED (missing approval gate)

```text
DETECTION_SOURCE: budgets
RESPONSE_SCOPE: budget-action
VERDICT: MANUAL_STEP_REQUIRED
WORKFLOW: (partial — blocked)
GUARDRAILS:
  - [PASS] Kill-switch: Parameter Store /cost/kill-switch
  - [FAIL] No approval gate — Budgets EC2 stop runs AUTOMATIC at 120%
  - [PASS] IAM role scoped to budgets:ExecuteBudgetAction
AUDIT:
  - [PASS] CloudTrail covers the account; Budgets action execution logged
FINDINGS:
  - [CRITICAL] No approval gate: a breach at 120% auto-stops instances with
    no human check. A billing-cycle lag (CUR delivery 8-24h) could trigger
    the stop after spend has already returned to normal.
  - [HIGH] Action lists i-0abc12345 only — horizontally scaled instances
    are NOT covered.
REMEDIATION:
  1. Move EC2 stop from 120% AUTOMATIC to 120% MANUAL:
     aws budgets put-budget-action --account-id 111122223333 \
       --budget-name monthly-ec2-budget --notification-type ACTUAL \
       --action-type RUN_SSM_DOCUMENTS --approval-model MANUAL
  2. Add a notify-only action at 100% so on-call is paged before stop.
  3. Tag EC2 with BudgetsActionMonitored=true; audit monthly.
```

## NEVER (these things)

- **NEVER deploy a budget EC2-stop action without an approval gate.**
  Budgets native `RUN_SSM_DOCUMENTS` with `STOP_EC2_INSTANCES` and
  `ApprovalModel=AUTOMATIC` stops instances the moment the threshold
  crosses — including during a billing-cycle lag when actual spend has
  already returned to normal. The stop causes an outage that costs
  more than the anomaly. Use `ApprovalModel=MANUAL` or wire the stop
  behind a Step Functions task-token approval gate.

- **NEVER grant the cost-response Lambda `ec2:*` or `iam:*` on `*`.**
  Scope to `ce:GetAnomalies`, `resourcegroupstaggingapi:TagResources`
  on specific ARNs, `budgets:ExecuteBudgetAction` on specific budget
  ARNs. A Lambda that can stop any EC2 instance or attach any IAM
  policy is a privilege-escalation target.

- **NEVER assume SNS notifications will be delivered.** SNS requires
  endpoint confirmation. An unconfirmed subscription silently drops
  messages. Always send a test message after creating the topic.

- **NEVER hardcode Slack/Teams webhook URLs in Lambda code.** Store
  in Parameter Store (free, encrypted by default) or Secrets Manager
  (paid, KMS-encrypted, rotation support). A hardcoded URL leaked via
  CloudTrail `GetFunctionConfiguration` lets anyone post to your
  Slack channel.

- **NEVER skip the dry-run window.** A workflow deployed straight to
  live without a 1-2 week dry-run (notify-only) period will misfire
  on the first real anomaly — wrong Slack channel, malformed
  notification, idempotency miss, or scoped-IAM gap.

- NEVER terminate EC2 instances from cost automation. Stopping is
  reversible; terminating destroys the resource and its EBS volumes.
  Terminate decisions require human judgment and are out of scope.

- NEVER rely on Budgets for real-time detection. Budgets evaluates
  every 8-12 hours; CAD evaluates daily/weekly. For sub-hour
  detection, use CloudWatch billing alarms (4h poll) or CUR Athena.

- NEVER attach an IAM deny-all policy to a role the Lambda or Step
  Functions execution role assumes. The deny-all cascades and blocks
  the workflow itself. Apply deny-all only to user-serving roles.

- NEVER use `ApprovalModel=AUTOMATIC` for Budgets actions with
  `RUN_SSM_DOCUMENTS`. Use `MANUAL` for EC2/RDS stop. Reserve
  `AUTOMATIC` for `APPLY_IAM_POLICY` (reversible) and
  `SNS_NOTIFICATION`.

- NEVER forget to dedupe Amazon Q / Cost Optimization Hub
  recommendations by `recommendationId`. A daily Lambda poll without
  dedupe reposts the same recommendation daily, creating Slack noise
  that trains the team to ignore the channel.

## Expert heuristic — the 60-second triage

When handed a cost-response design request, run this 60-second triage
before drafting the workflow:

1. **Identify the detection source.** CAD (anomaly ML), Budgets
   (threshold), CUR/Athena (top-spenders), or Q (recommendations).
2. **Identify the response severity.** Notify-only (reversible, no
   approval needed) vs resource-affecting (approval gate required).
3. **Identify the latency expectation.** CAD = 6-24h. Budgets = 8-12h.
   CUR/Athena = schedule-dependent. Set expectations explicitly.
4. **Identify the kill-switch.** Parameter Store, EventBridge disable,
   or Lambda guard. No kill-switch = MANUAL_STEP_REQUIRED.
5. **Identify the dry-run plan.** Ship with a 1-2 week dry-run
   (notify-only) before going live with actions.

If any of the five is missing or unclear, emit MANUAL_STEP_REQUIRED.

## Pre-flight safety checks (run before any deploy)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`cloudformation deploy`, `events put-rule`, `budgets
  put-budget-action`, `lambda create-function`), emit and await
  operator approval.
- **Dry-run first.** Deploy with `response_scope=notify` for 1-2 weeks
  before promoting to `budget-action` or `full-playbook`.
- **Validate the kill-switch.** Set `/cost/kill-switch` to "disabled"
  and verify a test anomaly does NOT trigger the action.
- **Verify Slack/Teams webhook.** Send a test message before relying
  on it. Capture existing Budgets configuration before deploying new
  actions.
- **Bulk operation safety limit.** Slice multi-account deploys into
  batches of at most 3 accounts; emit per-account CONFIRM per batch.

## Edge-case handling

- **Anomaly for a deleted resource.** CAD may surface an anomaly for a
  resource terminated between detection and response. The Lambda must
  handle `InvalidInstanceID.NotFound` gracefully — log and move on.
- **Cross-account cost rollup.** A payer sees aggregated spend; member
  anomalies may be hidden. Deploy per-member CAD monitors.
- **Planned spend spike (marketing launch, load test).** Disable the
  workflow before the event; re-enable after.
- **CUR schema change.** AWS occasionally adds columns. `SELECT *`
  survives; explicit-column queries break. Test after CUR updates.
- **Budgets action stale instance list.** If instances rotate
  (autoscaling), the action silently does nothing. Audit monthly.

## Recent AWS features (2024-2026)

- **CAD with ML impact evaluation (2024-2025):** CAD uses ML to
  evaluate dollar impact per anomaly (`Impact.TotalImpact`). Filter on
  this for severity; do not rely on legacy `AnomalyScore`.
- **Budgets advanced actions (2024-2025):** `RUN_SSM_DOCUMENTS` now
  supports SSM documents beyond `AWS-StopEC2Instance` — custom
  documents for RDS stop, ECS task scale-in, Lambda throttle.
- **AWS Cost Optimization Hub (2024-2025):** Aggregates
  recommendations across services (EC2 rightsize, RDS rightsize, SP
  commitment, S3 lifecycle). Use `get-recommendations --filter` for
  service-scoped recs. Dedupe by `recommendationId`.
- **Amazon Q cost optimization (2024-2025):** Q Business with the
  cost-optimization plugin answers natural-language spend questions.
  Layer Q insights on top of CAD alerts for richer notifications.
- **CUR 2.0 (2024-2025):** CUR supports columnar (Parquet) delivery
  with 5-10x faster Athena queries. Migrate from CSV to Parquet.
- **Budgets reset at calendar month (2025):** `TimeUnit=MONTHLY`
  budgets now reset strictly on the 1st of the calendar month.

## Domain

AWS CloudOps / FinOps — cost anomaly response automation.

## AWS documentation

- **AWS Cost Anomaly Detection** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-anomaly-detection.html
- **AWS Budgets** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- **AWS Budgets actions** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html
- **Cost and Usage Report** — https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html
- **Cost Optimization Hub** — https://docs.aws.amazon.com/cost-optimization-hub/latest/userguide/what-is-cost-optimization-hub.html
- **Amazon Q Business** — https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/what-is.html
- **AWS Cost Explorer** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- **Athena CUR queries** — https://docs.aws.amazon.com/cur/latest/userguide/cur-athena.html
- **AWS FinOps Blog** — https://aws.amazon.com/blogs/cost-management/
