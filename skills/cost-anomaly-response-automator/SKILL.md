---
name: cost-anomaly-response-automator
description: 'Designs automated AWS cost-anomaly detection and response workflows across AWS Cost Anomaly Detection (CAD) monitors (service, linked account, daily/weekly/monthly cadence), anomaly subscriptions (SNS), automated response patterns (EventBridge to Lambda: notify Slack or Teams, tag suspect resources, trigger a Budgets action), AWS Budgets cost-budget auto-actions (IAM policy attach, EC2 stop), Cost Explorer anomaly views, and CUR (Cost and Usage Report) analysis automation (Athena top-spenders queries). Layers in the latest: CAD with ML impact evaluation, Amazon Q cost-optimization recommendations, and Budgets advanced actions. Enforces guardrails: dry-run first, human-approval gate for any resource-stopping action, scoped IAM, idempotency, full CloudTrail audit. Emits AUTOMATED with response plan or MANUAL_STEP_REQUIRED with the specific gap. Use when wiring Cost Anomaly Detection or Budgets to a notification or remediation pipeline.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws ce create-anomaly-monitor, create-anomaly- subscription, get-anomalies; aws budgets create-budget, put-budget-action; aws cur describe-report-definitions; aws athena start-query-execution; aws sns create-topic / subscribe; aws events put-rule / put-targets; aws lambda create-function; aws resourcegroupstaggingapi tag-resources; aws...
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
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing an automated cost-anomaly response for AWS, wiring Cost Anomaly Detection or AWS Budgets to a notification (Slack, Teams, email) or remediation (tag suspect resources, attach an IAM deny policy, stop EC2), building the CUR Athena top-spenders query that feeds the response pipeline, layering Amazon Q cost-optimization recommendations onto anomaly alerts, or hardening an existing spend-response workflow with dry-run, approval gate, and audit.
  when_not_to_use: Manual cost triage — this skill designs automation; use a human-driven cost review for one-off investigations., RI/SP purchasing strategy — commitment decisions are strategic; use a Savings Plan negotiation skill, not a real-time response pipeline., Billing accuracy disputes — use AWS Support; this skill automates response, not charge correction., Showback/chargeback reporting — use CUR + Athena + QuickSight; this skill is for anomaly response, not periodic reporting.
  activation_triggers: automate cost anomaly response, Cost Anomaly Detection to Slack, Budgets action on cost overrun, SNS alert on spend anomaly, EventBridge Lambda cost remediation, stop EC2 on budget breach, IAM deny policy budget action, CUR Athena top spenders, Amazon Q cost optimization, cost budget auto-action, tag resources on anomaly, anomaly subscription SNS
  invocation_schema: "{output: 'Deterministic block: DETECTION_SOURCE / RESPONSE_SCOPE / VERDICT / WORKFLOW\n    / GUARDRAILS / AUDIT / FINDINGS / REMEDIATION. VERDICT is AUTOMATED when complete\n    with dry-run, scoped IAM, approval gate before resource-stopping actions, and\n    CloudTrail-auditable record; MANUAL_STEP_REQUIRED when a guardrail or coverage\n    gate fails.', properties: {detection_source: {description: The detection source\n        that triggers the workflow., enum: [cad, budgets, ce-anomaly, cur, q-recommendations],\n      type: enum}, existing_workflow: {description: 'Existing EventBridge rule + Lambda\n        or Step Functions definition. When provided, runs the guardrail + audit gate.',\n      type: object}, response_scope: {description: Which response phases to automate.,\n      enum: [notify, tag, budget-action, full-playbook, cur-analysis], type: enum},\n    severity_threshold: {description: USD impact (CAD) or % of budget (Budgets). Default\n        100 USD / 80%., type: number}}, required: [detection_source, response_scope],\n  type: object}"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Cost Anomaly Detection, CAD, AWS Budgets, cost budget, budget action, anomaly subscription, SNS alert, Cost Explorer, Cost and Usage Report, CUR, Athena top spenders, Amazon Q cost optimization, EventBridge, Lambda remediation, Slack notification, Teams notification, FinOps, cost governance, EC2 stop budget action, IAM policy budget action, spend automation
  tags: finops, cost-anomaly, budgets, automation, cost-explorer, cur, eventbridge, lambda
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

Live-account pre-flight commands (CAD enabled, CUR exists, SNS topic, Lambda role scope, Budgets enabled): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full catalog (CAD daily/weekly lag, TotalImpact semantics, Budgets 8-12h evaluation, calendar-month reset, single-threshold actions, IAM-policy vs EC2-stop targeting, CUR 8-24h latency, Glue partitions, SNS confirmation, webhook storage, EventBridge gaps, Q scoping, COH dedupe, monitor types): [references/advanced-patterns.md](references/advanced-patterns.md).

## Detection sources

### AWS Cost Anomaly Detection (CAD)

Monitor and subscription CLI (list monitors, SERVICE and LINKED_ACCOUNT monitors, SNS-wired anomaly subscription, get-anomalies): [references/cad-budgets-action-catalog.md](references/cad-budgets-action-catalog.md).

### AWS Budgets

Budget and action CLI (create-budget, 80% SNS notify, 100% IAM deny AUTOMATIC, 120% EC2 stop MANUAL): [references/cad-budgets-action-catalog.md](references/cad-budgets-action-catalog.md).

### Cost Explorer anomaly view

Cost Explorer surfaces anomalies in the console under "Cost Anomaly
Detection". The same data is available via `aws ce get-anomalies`. CE
is the visualization; CAD is the engine. Use `get-anomalies`
programmatically and surface in your own dashboard or Slack via
Lambda.

### CUR analysis automation

CUR verify + top-spenders Athena SQL + EventBridge daily schedule CLI: [references/cad-budgets-action-catalog.md](references/cad-budgets-action-catalog.md).

### Amazon Q cost-optimization recommendations

Cost Optimization Hub get-recommendations CLI + scheduled Lambda poll/dedupe pattern: [references/cad-budgets-action-catalog.md](references/cad-budgets-action-catalog.md).

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

Full state-machine JSON (kill-switch check -> notify -> tag -> SQS task-token approval -> optional Budgets action -> close): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Full MANUAL_STEP_REQUIRED example (Budgets EC2 stop AUTOMATIC at 120%, no approval gate): [references/worked-examples.md](references/worked-examples.md).

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

Edge-case catalog (deleted resource, cross-account rollup, planned spike, CUR schema change, stale instance list): [references/advanced-patterns.md](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

What changed in 24 months (CAD ML impact, Budgets SSM documents, Cost Optimization Hub, Amazon Q, CUR 2.0 Parquet, calendar-month reset): [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Worked examples](references/worked-examples.md) - MANUAL_STEP_REQUIRED worked example: Budgets EC2 stop at 120% with no approval gate
- [Diagnostic commands](references/diagnostic-commands.md) - live-account pre-flight commands (CAD monitors, CUR, SNS, Lambda role, Budgets)
- [Advanced patterns](references/advanced-patterns.md) - Step 0 non-obvious cost behaviors, full-playbook Step Functions state machine, edge-case handling, recent AWS features
- [CAD/Budgets/Athena action catalog](references/cad-budgets-action-catalog.md) - detection-source CLI (CAD monitors/subscriptions, Budgets + native actions, CUR top-spenders query, Cost Optimization Hub polling)

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
