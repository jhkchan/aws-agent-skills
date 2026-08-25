# Advanced patterns - Cost Anomaly Response Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

## Full-playbook Step Functions state machine (Response pattern 5)

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
