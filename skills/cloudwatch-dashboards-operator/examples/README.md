# End-to-end usage scenario: cloudwatch-dashboards-operator

A walkthrough showing the skill planning an RDS monitoring dashboard
creation with 8 widgets, all pre-checks passing, and the operator
confirming at the CONFIRM gate. Contrasted with the REVIEW_REQUIRED
case where a cross-account OAM dashboard needs stakeholder confirmation.

## Input (user prompt)

> Create a dashboard called `prod-rds-overview` for our production RDS
> instance `prod-orders-db`. I need CPU, memory, connections, storage,
> query throughput, replica lag, an alarm widget for `rds-cpu-high`,
> and error logs. Use metric math for connection utilization.

```json
{
  "Operation": "create-dashboard",
  "DashboardName": "prod-rds-overview",
  "Service": "RDS",
  "Widgets": 8,
  "NamespaceCheck": {
    "Namespace": "AWS/RDS",
    "MetricsFound": 42
  },
  "DimensionCheck": {
    "DBInstanceIdentifier": "prod-orders-db",
    "Exists": true,
    "Status": "available"
  },
  "AlarmCheck": {
    "AlarmName": "rds-cpu-high",
    "Exists": true
  },
  "DashboardExistence": {
    "AlreadyExists": false
  }
}
```

## Skill output

```text
OPERATION: create-dashboard
VERDICT: OPERATION_COMPLETED
TARGET: prod-rds-overview (widgets: 8)
PRE_CHECKS:
  - [PASS] Dashboard name "prod-rds-overview" does not already exist
  - [PASS] Namespace AWS/RDS has published data (42 metrics found)
  - [PASS] DBInstanceIdentifier dimension value matches live RDS instance
  - [PASS] Alarm rds-cpu-high exists (for alarm widget)
  - [PASS] Dashboard body size: 12 KB (< 256 KB limit)
STEPS:
  1. CONFIRM: About to create dashboard "prod-rds-overview" with 8
     widgets in account 111111111111 region us-east-1. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name prod-rds-overview \
       --dashboard-body file://dashboards/prod-rds-overview.json
  3. aws cloudwatch get-dashboard \
       --dashboard-name prod-rds-overview \
       --query 'DashboardName'
POST_VERIFY:
  - [PASS] get-dashboard returns "prod-rds-overview"
  - [PASS] Dashboard body matches input (8 widgets)
  - [PASS] Namespace AWS/RDS has data (widgets will render)
NOTES:
  - Dashboard includes metric math for connection utilization:
    DatabaseConnections / maxConnections * 100
  - Alarm widget shows rds-cpu-high (threshold 80% for 5 min)
  - Set auto-refresh to 5 minutes in the console (cost-optimized)
  - Store the dashboard JSON in Git for version-controlled IaC
```

## Contrast — REVIEW_REQUIRED case (cross-account OAM)

If the operator requested a cross-account dashboard via OAM, the
pre-check gate would surface review items:

```text
OPERATION: enable-cross-account
VERDICT: REVIEW_REQUIRED
TARGET: cross-account-rds-overview (monitoring: 111111111111,
        sources: 222222222222, 333333333333)
PRE_CHECKS:
  - [PASS] OAM sink "org-monitoring-sink" exists, Status: ACTIVE
  - [PASS] Source account 222222222222 linked (LINKED, MetricLink: true)
  - [PASS] Source account 333333333333 linked (LINKED, MetricLink: true)
  - [REVIEW] Enabling cross-account dashboard exposes metrics from
    accounts 222222222222 and 333333333333 in the monitoring account.
    Confirm all stakeholders authorized cross-account visibility.
  - [REVIEW] Dashboard includes Metrics Insights query aggregating
    across all linked accounts. Verify the GROUP BY @Account clause
    matches the monitoring scope.
STEPS:
  1. CONFIRM: About to create cross-account dashboard with OAM filter
     for accounts 222222222222 and 333333333333. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name cross-account-rds-overview \
       --dashboard-body file://cross-account-rds-overview.json
POST_VERIFY:
  - (pending operator confirmation and execution)
NOTES:
  - OAM link propagates metrics, logs, and traces from source accounts.
  - The @Account variable lets users filter by source account.
  - Default is "*" (all linked accounts).
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the put-dashboard command directly. The skill runs pre-checks
   (namespace data availability, dimension match, alarm existence,
   dashboard name conflict, body size limit) before executing.

2. **PutDashboard overwrites the entire body.** A generic assistant
   omits this critical behavior. The skill captures the current body
   for diff/rollback before any update.

3. **Metric math for derived calculations.** A generic assistant uses
   raw metric values only. The skill constructs metric math expressions
   (error rate, connection utilization) within the widget itself.

4. **Anomaly detection training data requirement.** A generic assistant
   adds the band without checking data history. The skill verifies
   minimum 15 minutes of training data and recommends optimal 2+ weeks.

5. **OAM vs cross-account IAM roles.** A generic assistant may suggest
   legacy cross-account role assumption. The skill uses OAM shared
   observability, which scales to hundreds of accounts.

6. **Metrics Insights cost awareness.** A generic assistant omits the
   per-query cost. The skill surfaces the $0.005/1K queries cost and
   recommends LIMIT clauses.

7. **Custom widget code execution surface.** A generic assistant
   deploys Lambda widgets without review. The skill flags the code
   execution risk and requires operator confirmation.

8. **Git-based version control for dashboards.** A generic assistant
   makes console edits. The skill promotes storing dashboard JSON in
   Git and deploying via CI/CD for consistency and rollback.

## Slash-command invocation

```
/aws:operate-cloudwatch-dashboards
```

Or via the orchestrator:

```
/aws:pipeline
You: "create an RDS dashboard for prod-orders-db"
```

The orchestrator emits
`[Phase: Operate | Skills routed: cloudwatch-dashboards-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create RDS dashboard for prod-orders-db"
# [Phase: Operate | Skills routed: cloudwatch-dashboards-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the dashboard is created:

```bash
# Verify the dashboard was created
aws cloudwatch get-dashboard \
  --dashboard-name prod-rds-overview \
  --profile default \
  --query 'DashboardName'

# Store the JSON body in Git
aws cloudwatch get-dashboard \
  --dashboard-name prod-rds-overview \
  --profile default \
  --query 'DashboardBody' \
  --output text | jq . > dashboards/prod-rds-overview.json

git add dashboards/prod-rds-overview.json
git commit -m "Add prod-rds-overview CloudWatch dashboard"

# Set up an alarm referenced in the dashboard (if not already present)
aws cloudwatch put-metric-alarm \
  --alarm-name rds-cpu-high \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=prod-orders-db \
  --threshold 80 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 300 \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:ops-alerts \
  --profile default
```
