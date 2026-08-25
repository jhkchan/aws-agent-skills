# CAD Monitors, Budgets Actions, and Athena CUR Patterns — Reference

This reference catalogues the concrete AWS CLI shapes for Cost
Anomaly Detection monitors, anomaly subscriptions, AWS Budgets native
actions, and the Athena CUR query patterns used by the
cost-anomaly-response-automator skill. Each entry includes parameters,
IAM requirements, and known failure modes.

## Cost Anomaly Detection (CAD) monitor types

| MonitorType | Use case | Key parameter |
|---|---|---|
| `SERVICE` | Monitor spend for one AWS service (e.g., EC2, S3) | `MonitorSpecification` Dimensions Key=SERVICE |
| `LINKED_ACCOUNT` | Monitor spend for one member account | `MonitorSpecification` Dimensions Key=LINKED_ACCOUNT |
| `DIMENSION` | Monitor by a Cost Explorer dimension (SERVICE default) | `MonitorDimension` |
| `CUSTOM` | Monitor a CloudWatch metric expression | `MonitorSpecification` Expression |

**Cadence:** CAD evaluates monitors on a daily or weekly cadence
(set on the anomaly subscription, not the monitor). Daily is the
default. There is no real-time or hourly cadence.

**IAM permissions for the operator:**
- `ce:CreateAnomalyMonitor`, `ce:GetAnomalyMonitors`,
  `ce:UpdateAnomalyMonitor`, `ce:DeleteAnomalyMonitor`
- `ce:CreateAnomalySubscription`, `ce:GetAnomalySubscriptions`
- `ce:GetAnomalies` (read anomalies)

**Failure modes:**
- Monitor created but no subscription wired — anomalies are detected
  but never delivered. Always pair monitor creation with a
  subscription.
- Subscription SNS topic deleted — anomalies silently dropped. Monitor
  the topic's existence via Config.
- `MonitorSpecification` JSON malformed — `create-anomaly-monitor`
  fails with a generic ValidationException. Validate JSON before
  passing.

## CAD anomaly subscription

**Threshold semantics:** `Threshold` is in USD (the dollar deviation
from baseline that triggers the alert). A threshold of 100 fires on
anomalies with `Impact.TotalImpact >= 100`.

**Frequency:** `DAILY` (default) or `WEEKLY` or `IMMEDIATE`. IMMEDIATE
fires as soon as an anomaly is detected (still subject to CAD's daily
evaluation).

**Subscriber types:** `SNS` (topic ARN), `EMAIL` (address).

```bash
aws ce create-anomaly-subscription --anomaly-subscription '{
  "Name": "prod-cost-anomaly-sub",
  "Threshold": 100.0,
  "Frequency": "DAILY",
  "MonitorArnList": ["arn:aws:ce::111122223333:anomalymonitor/abc-123"],
  "Subscribers": [{"Address": "arn:aws:sns:us-east-1:111122223333:cost-anomaly-alerts", "Type": "SNS"}]
}'
```

## AWS Budgets native actions

### APPLY_IAM_POLICY

Attaches an existing IAM policy (typically deny-all) to specified IAM
roles, users, or groups when the budget threshold is crossed.

**Parameters:**
- `PolicyArn` (required) — the IAM policy to attach.
- `Roles` / `Users` / `Groups` (at least one) — the principals to
  attach to.

**IAM permissions on the execution role:**
- `iam:AttachRolePolicy`, `iam:AttachUserPolicy`,
  `iam:AttachGroupPolicy`
- `iam:ListAttachedRolePolicies` (for status check)

**Reversibility:** Reversible — detach the policy to undo. Safe for
`ApprovalModel=AUTOMATIC`.

### RUN_SSM_DOCUMENTS

Runs an SSM Automation document (typically `AWS-StopEC2Instance`)
when the budget threshold is crossed.

**Parameters:**
- `ActionSubType` — `STOP_EC2_INSTANCES` or `START_EC2_INSTANCES`.
- `Region` (required) — region of the instances.
- `InstanceIds` (required) — list of instance IDs.

**IAM permissions on the execution role:**
- `ssm:StartAutomationExecution`
- `ec2:StopInstances` / `ec2:StartInstances` on the listed instances
- `iam:PassRole` on the SSM automation role

**Reversibility:** Stopping is reversible (start the instance);
however, stopping causes an outage. Use `ApprovalModel=MANUAL`.

**Failure mode:** If `InstanceIds` lists terminated or non-existent
instances, the action silently does nothing. Audit the list monthly.

### SNS_NOTIFICATION

Publishes to an SNS topic when the threshold is crossed.

**Parameters:**
- `Notification` (required) — the SNS topic ARN.

**IAM permissions:**
- `sns:Publish` on the topic ARN.

**Reversibility:** Fully reversible (no state change). Safe for
`ApprovalModel=AUTOMATIC`.

## Athena CUR query patterns

### Top-spenders by service and resource

```sql
SELECT lineitem_product_servicename AS service,
       lineitem_usageaccount_id AS account,
       resource_id AS resource,
       SUM(lineitem_unblendedcost) AS spend
FROM "cur"."cur_table"
WHERE year = '2026' AND month = '08'
  AND lineitem_lineitemtype IN ('Usage', 'DiscountedUsage')
GROUP BY 1, 2, 3
HAVING SUM(lineitem_unblendedcost) > 100
ORDER BY spend DESC LIMIT 20;
```

### Spend delta vs previous period

```sql
WITH this_period AS (
  SELECT lineitem_product_servicename AS service,
         SUM(lineitem_unblendedcost) AS spend
  FROM "cur"."cur_table"
  WHERE year='2026' AND month='08'
  GROUP BY 1
),
prev_period AS (
  SELECT lineitem_product_servicename AS service,
         SUM(lineitem_unblendedcost) AS spend
  FROM "cur"."cur_table"
  WHERE year='2026' AND month='07'
  GROUP BY 1
)
SELECT t.service, t.spend AS this_month, p.spend AS last_month,
       (t.spend - p.spend) AS delta,
       ROUND((t.spend - p.spend) * 100.0 / NULLIF(p.spend, 0), 1) AS pct_change
FROM this_period t JOIN prev_period p ON t.service = p.service
WHERE ABS(t.spend - p.spend) > 50
ORDER BY ABS(t.spend - p.spend) DESC;
```

### Untagged resources (cost-allocation gap)

```sql
SELECT lineitem_product_servicename AS service,
       resource_id, SUM(lineitem_unblendedcost) AS spend
FROM "cur"."cur_table"
WHERE year='2026' AND month='08'
  AND resource_id NOT LIKE 'aws:%'
  AND product_resourceid = ''
GROUP BY 1, 2 HAVING SUM(lineitem_unblendedcost) > 50
ORDER BY spend DESC LIMIT 50;
```

**Athena requirements:**
- The CUR table MUST be partitioned by `year` and `month`. Run
  `MSHC REPAIR TABLE cur_table` after creating a new CUR.
- The Glue Data Catalog database (`cur`) must exist and contain the
  table. Use the AWS-provided CloudFormation template for CUR Athena
  integration.
- Query results land in the configured S3 output location. Set a
  lifecycle policy to expire results after 30 days.

**Performance:** Parquet CUR (CUR 2.0) queries 5-10x faster than CSV
CUR. Migrate if still on CSV.

## Cost Optimization Hub

**API:**

```bash
aws cost-optimization-hub get-recommendations \
  --filter '{"implementAfterTimestamp": 0}' \
  --max-results 50 --output json

aws cost-optimization-hub get-recommendation \
  --recommendation-id <id> --output json
```

**Recommendation types:** `RIGHTSIZING`, `SCHEDULE`, `STOP`, `SP_PURCHASE`.

**Deduplication:** Each recommendation has a stable
`recommendationId`. A Lambda polling daily must track the last-seen
ID in DynamoDB or Parameter Store to avoid re-posting.

**Enrollment:** Cost Optimization Hub must be enabled in the payer
account. Member account recommendations roll up to the payer.

## Detection source CLI — AWS Cost Anomaly Detection (CAD)

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

## Detection source CLI — AWS Budgets

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

## Detection source CLI — CUR analysis automation

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

## Detection source CLI — Amazon Q / Cost Optimization Hub recommendations

```bash
# Cost Optimization Hub (Org-level)
aws cost-optimization-hub get-recommendations \
  --filter '{"implementAfterTimestamp": 0}' --max-results 50 --output json
# Lambda (scheduled) polls, dedupes by recommendationId, posts to Slack
```
