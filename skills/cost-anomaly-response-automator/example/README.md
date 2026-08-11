# Example usage: cost-anomaly-response-automator

A walkthrough showing the skill designing a CAD-to-Slack full-playbook
cost anomaly response with notify, tag, approval gate, and budget
action. The skill emits an AUTOMATED verdict.

## Input (user prompt)

> Design an automated cost anomaly response for our production AWS
> account. When CAD detects an anomaly above USD 100 on the EC2 spend
> monitor, I want to: notify the FinOps Slack channel, tag the
> suspect resources, wait for human approval, then optionally run the
> budget EC2 stop action. Include a kill-switch and full audit.

## Skill output

```text
DETECTION_SOURCE: cad
RESPONSE_SCOPE: full-playbook
VERDICT: AUTOMATED
WORKFLOW:
  Detection: ec2-spend-monitor (arn:aws:ce::111122223333:anomalymonitor/abc-123)
  Anomaly subscription: prod-cost-anomaly-sub (threshold USD 100, daily)
  SNS topic: arn:aws:sns:us-east-1:111122223333:cost-anomaly-alerts
  EventBridge rule: n/a (CAD -> SNS -> Lambda)
  Lambda functions: cost-notify-slack, cost-tag-resources, cost-budget-action
  Step Functions: arn:aws:states:us-east-1:111122223333:stateMachine:cost-full-playbook
  Budgets action: monthly-ec2-budget (IAM deny at 100%, EC2 stop at 120%)
  Kill-switch: Parameter Store /cost/kill-switch
GUARDRAILS:
  - [PASS] Dry-run completed 2026-07-15 to 2026-07-29 (14 days, notify-only)
  - [PASS] Approval gate via SQS task token before EC2 stop
  - [PASS] Lambda role scoped to ce:GetAnomalies, sns:Publish,
          resourcegroupstaggingapi:TagResources, budgets:ExecuteBudgetAction
  - [PASS] Idempotency: DynamoDB table cost-anomaly-dedupe keyed by AnomalyId
  - [PASS] Kill-switch checked first in state machine
AUDIT:
  - [PASS] CloudTrail org trail covers account 111122223333
  - [PASS] Slack notification includes AnomalyId, Impact USD, Service
  - [PASS] Budgets action execution logged in CloudTrail
  - [PASS] Tagged resources carry CostAnomaly=<AnomalyId> tag
FINDINGS:
  - [INFO] SNS subscription confirmed by Slack-forwarding Lambda
  - [INFO] CAD evaluates daily; expect 6-24h latency on anomaly detection
  - [WARN] CUR/Athena top-spenders query runs on a 12h delay (CUR delivery)
REMEDIATION: Deploy via:
  aws cloudformation deploy --stack-name prod-cost-workflow \
    --template-file cost-workflow.yaml --capabilities CAPABILITY_NAMED_IAM
```

## What the skill caught that a generic assistant misses

1. **CAD evaluates daily, not real-time.** A generic assistant lets
   the operator believe the response is near-real-time. The skill sets
   the 6-24h latency expectation explicitly in FINDINGS.

2. **Approval gate via SQS task token.** A generic assistant uses a
   fixed `Wait` state or skips the gate entirely. The skill uses the
   `sqs:sendMessage.waitForTaskToken` pattern for clean human callback
   — pausing cleanly and resuming on approval.

3. **Idempotency via AnomalyId.** A generic assistant omits the
   dedupe check; a finding storm triggers duplicate actions. The skill
   keys the DynamoDB dedupe table on AnomalyId.

4. **Kill-switch checked FIRST in the state machine.** A generic
   assistant buries the kill-switch inside a Lambda — if the Lambda
   fails on the check, the workflow proceeds. The skill puts the check
   as a Step Functions `Task` + `Choice` state before any action.

5. **Scoped IAM for the Lambda.** A generic assistant grants
   `ec2:*` or `iam:*` on `*`. The skill scopes the Lambda role to
   `ce:GetAnomalies`, `sns:Publish` on the specific topic, and
   `resourcegroupstaggingapi:TagResources` on specific ARNs.

6. **CUR delivery lag surfaced.** A generic assistant deploys the
   Athena top-spenders query without flagging the 8-24h CUR delivery
   lag. The skill notes the query runs on stale data and recommends
   scheduling for 12:00 UTC or later.

## Slash-command invocation

```
/aws:automate-cost-anomaly-response
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate EC2 spend anomaly response with Slack notify, tag, and approval gate"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the workflow, validate the posture:

```bash
# Verify CAD monitor exists and is active
aws ce get-anomaly-monitors --query 'AnomalyMonitors[?MonitorName==`ec2-spend-monitor`]'

# Verify the anomaly subscription is wired to SNS
aws ce get-anomaly-subscriptions \
  --query 'AnomalySubscriptions[?Name==`prod-cost-anomaly-sub`].Subscribers'

# Verify the Step Functions state machine exists and is active
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111122223333:stateMachine:cost-full-playbook \
  --query 'status'

# Verify the kill-switch parameter is set
aws ssm get-parameter --name /cost/kill-switch

# Verify the Slack webhook is stored in Parameter Store
aws ssm get-parameter --name /cost/slack-webhook --with-decryption

# Verify the Budgets action approval model is MANUAL (not AUTOMATIC)
aws budgets describe-budget-action \
  --account-id 111122223333 --budget-name monthly-ec2-budget \
  --action-id <action-id> --query 'Action.ApprovalModel'

# Send a test anomaly to verify the pipeline fires end-to-end
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111122223333:cost-anomaly-alerts \
  --message '{"AnomalyId":"test-001","Impact":{"TotalImpact":500},"AccountId":"111122223333"}'

# Verify the Step Functions execution started
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:111122223333:stateMachine:cost-full-playbook \
  --max-results 1

# Test the kill-switch: disable and verify no action
aws ssm put-parameter --name /cost/kill-switch --value "disabled" \
  --type String --overwrite
# Send another test event — workflow should succeed without action
aws ssm put-parameter --name /cost/kill-switch --value "enabled" \
  --type String --overwrite  # re-enable
```
