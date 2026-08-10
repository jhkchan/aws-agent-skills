# End-to-end usage scenario: cloudwatch-dashboard-deployer

A walkthrough showing the skill creating an EC2 operational dashboard,
a metric-math error-rate dashboard, and a cross-account dashboard that
is blocked by a missing sharing role. Each path includes pre-checks,
CONFIRM gate, and post-verification — and is contrasted with the
PREREQUISITES_MISSING case where pre-checks catch a problem.

## Input (user prompt)

> Create a production operational dashboard "prod-ec2-ops" with CPU,
> Memory, and Network widgets using the INSTANCE_ID variable. Then
> build a metric-math error rate dashboard for the ALB. Then set up
> a cross-account dashboard — but the staging account doesn't have
> the sharing role yet.

```json
{
  "Operation": "create",
  "Dashboard name": "prod-ec2-ops",
  "Region": "us-east-1",
  "Account": "111111111111",
  "Widgets": [
    {"type": "metric", "namespace": "AWS/EC2", "metric": "CPUUtilization", "dimensions": "InstanceId=${INSTANCE_ID}", "statistic": "Average", "period": 300, "position": "x=0,y=0,w=12,h=6"},
    {"type": "metric", "namespace": "CWAgent", "metric": "mem_used_percent", "dimensions": "InstanceId=${INSTANCE_ID}", "statistic": "Average", "period": 300, "position": "x=12,y=0,w=12,h=6"},
    {"type": "metric", "namespace": "AWS/EC2", "metrics": ["NetworkIn","NetworkOut"], "dimensions": "InstanceId=${INSTANCE_ID}", "statistic": "Sum", "period": 300, "position": "x=0,y=6,w=24,h=3"}
  ],
  "DashboardVariable": "INSTANCE_ID",
  "MetricChecks": {
    "AWS/EC2.CPUUtilization": {"datapoints": 60, "Average": 45.2},
    "CWAgent.mem_used_percent": {"datapoints": 60, "Average": 62.4},
    "AWS/EC2.NetworkIn": {"datapoints": 60, "Sum": 1048576}
  }
}
```

## Skill output — create operational dashboard

```text
DASHBOARD: prod-ec2-ops
VERDICT: READY_TO_DEPLOY
TARGET: prod-ec2-ops
PRE_CHECKS:
  - [PASS] DashboardBody valid JSON, 3 widgets, 0 overlaps
  - [PASS] Widget 1: AWS/EC2 CPUUtilization InstanceId=${INSTANCE_ID}
    returns 60 datapoints (Average ~45%, Maximum 72%)
  - [PASS] Widget 2: CWAgent mem_used_percent InstanceId=${INSTANCE_ID}
    returns 60 datapoints (Average ~62%)
  - [PASS] Widget 3: metric math NetworkIn/1048576 valid
  - [PASS] Period 300 >= metric native 60s (detailed monitoring)
  - [PASS] Statistic Average matches utilization semantics (widgets 1-2)
  - [PASS] Dashboard variable INSTANCE_ID maps to valid dimension on
    AWS/EC2 and CWAgent
  - [PASS] 3 widgets <= 100 cap
  - [PASS] IAM principal holds cloudwatch:PutDashboard
STEPS:
  1. CONFIRM: About to put-dashboard prod-ec2-ops in account
     111111111111 region us-east-1. This will CREATE a new dashboard
     with 3 metric widgets (CPU, Memory, Network). Proceed? (yes/no)
  2. aws cloudwatch put-dashboard --dashboard-name prod-ec2-ops \
       --dashboard-body '{"widgets":[...]}'
POST_VERIFY:
  - (pending execution)
  - get-dashboard returns 3 widgets with correct positions
  - Each metric widget renders non-empty within the dashboard time range
WIDGETS: 3 (3 metric, 0 log, 0 alarm, 0 text)
SHARING: single-account
NOTES:
  - Dashboard variable INSTANCE_ID enables dynamic instance selection
    from the dashboard dropdown — no need for one dashboard per instance.
  - CWAgent widget requires CloudWatch agent installed on target
    instances. If memory chart renders empty, verify agent status via
    `aws ssm describe-instance-information` and check the agent config.
  - No auto-refresh configured — set to 5m for operational use via
    the console.
```

## Skill output — metric math dashboard

```text
DASHBOARD: prod-alb-error-rate
VERDICT: READY_TO_DEPLOY
TARGET: prod-alb-error-rate
PRE_CHECKS:
  - [PASS] DashboardBody valid JSON, 1 widget, 0 overlaps
  - [PASS] m1 (HTTPCode_ELB_5XX_Count) returns 60 datapoints (Sum ~12/min)
  - [PASS] m2 (RequestCount) returns 60 datapoints (Sum ~5000/min)
  - [PASS] Expression e1: m1/m2*100 — valid math syntax, m-IDs reference
    defined metrics
  - [PASS] Period 60 >= ALB native 60s
  - [PASS] Statistic Sum matches count semantics
  - [PASS] 1 widget <= 100 cap
STEPS:
  1. CONFIRM: About to put-dashboard prod-alb-error-rate in account
     111111111111 region us-east-1. This will CREATE a new dashboard
     with 1 metric-math widget (ALB 5xx error rate %). Proceed? (yes/no)
  2. aws cloudwatch put-dashboard --dashboard-name prod-alb-error-rate \
       --dashboard-body '{"widgets":[{"type":"metric","x":0,"y":0,"width":24,"height":6,"properties":{"metrics":[["AWS/ApplicationELB","HTTPCode_ELB_5XX_Count","LoadBalancer","app/prod-alb/1234567890",{"id":"m1"}],["AWS/ApplicationELB","RequestCount","LoadBalancer","app/prod-alb/1234567890",{"id":"m2"}],[{"expression":"m1/m2*100","label":"Error Rate %","id":"e1"}]],"period":60,"stat":"Sum","title":"ALB 5xx Error Rate (%)","view":"timeSeries"}}]}'
POST_VERIFY:
  - (pending execution)
  - get-dashboard returns 1 widget with metric math expression
  - Error rate chart renders non-empty (expected ~0.24% based on m1/m2)
WIDGETS: 1 (1 metric, 0 log, 0 alarm, 0 text)
SHARING: single-account
NOTES:
  - Expression e1: m1/m2*100 computes error rate as percentage. m1 is
    5xx count, m2 is total request count. Division yields rate, *100
    converts to percentage.
  - The yAxis range is not set — consider adding yAxis: {left: {min: 0,
    max: 10}} to keep the chart readable when error rate is low.
  - Period 60 gives 1-minute granularity. For executive dashboards,
    increase to 3600 for hourly aggregation.
```

## Skill output — cross-account dashboard (PREREQUISITES_MISSING)

```text
DASHBOARD: cross-account-ec2-ops
VERDICT: PREREQUISITES_MISSING
TARGET: cross-account-ec2-ops
PRE_CHECKS:
  - [PASS] DashboardBody valid JSON, 2 widgets, 0 overlaps
  - [PASS] Widget 1: dev account 222222222222 CPUUtilization returns
    60 datapoints (sharing role exists, metrics visible)
  - [FAIL] Widget 2: staging account 333333333333 CPUUtilization
    returns 0 datapoints — CloudWatch-CrossAccountSharingRole does
    NOT exist in staging account 333333333333. Metrics from this
    account are not visible to the monitoring account. The widget
    will render empty.
  - [PASS] Dashboard structure is valid
STEPS: (none — pre-checks failed; resolve sharing role first)
POST_VERIFY: (none)
WIDGETS: 2 planned (2 metric, 0 log, 0 alarm, 0 text)
SHARING: cross-account:2-source-accounts (BLOCKED — 1 of 2 missing role)
NOTES:
  - Root cause: CloudWatch-CrossAccountSharingRole is missing in the
    staging account (333333333333). The dev account (222222222222)
    has the role and its metrics are visible.
  - Remediation: create the sharing role in the staging account:
    aws iam create-role --role-name CloudWatch-CrossAccountSharingRole \
      --assume-role-policy-document '{
        "Version":"2012-10-17",
        "Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::111111111111:root"},"Action":"sts:AssumeRole"}]
      }'
    aws iam attach-role-policy --role-name CloudWatch-CrossAccountSharingRole \
      --policy-arn arn:aws:iam::aws:policy/service-role/CloudWatch-CrossAccountSharingRolePolicy
  - After creating the role, re-verify:
    aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
      --metric-name CPUUtilization \
      --dimensions Name=InstanceId,Value=i-0abcdef1234567890 \
      --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
      --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Average
    Datapoints should appear within 5 minutes of role creation.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the put-dashboard command directly. The skill runs 9+
   deterministic pre-checks and confirms each metric is publishing,
   log groups exist, sharing roles are configured, and the dashboard
   JSON structure is valid.

2. **PutDashboard overwrite trap.** A generic assistant adds widgets
   without fetching the existing dashboard body. The skill snapshots
   via `get-dashboard --output json` first because PutDashboard
   replaces the entire DashboardBody with no version history.

3. **Dashboard variables.** A generic assistant hardcodes instance IDs.
   The skill uses $INSTANCE_ID so one dashboard serves the entire fleet
   and adapts to instance replacements.

4. **Cross-account sharing role verification.** A generic assistant
   creates the cross-account dashboard and assumes it will work. The
   skill verifies the sharing role exists in EACH source account and
   blocks deployment if any role is missing — preventing empty widgets
   that silently erode operator trust.

5. **Metric math ID convention.** A generic assistant omits the `id`
   field in metric options and the expression references fail silently.
   The skill enforces the m1/m2/e1 convention and validates expression
   syntax before deployment.

6. **CWAgent namespace awareness.** A generic assistant uses AWS/EC2
   for memory metrics. The skill knows OS-level metrics (memory, disk,
   swap) are in the CWAgent namespace and requires the CloudWatch agent
   to be installed — surfacing this as a NOTES caveat.

7. **Empty widget diagnostic.** A generic assistant deploys and walks
   away. The skill includes a post-verification step and a diagnostic
   decision tree for empty widgets (namespace case-sensitivity,
   dimension matching, cross-account AccountId correctness).

8. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — PutDashboard silently overwrites the entire
   dashboard with no diff or rollback.

## Slash-command invocation

```
/aws:deploy-cloudwatch-dashboard
```

Or via the orchestrator:

```
/aws:pipeline
You: "create an operational dashboard for my EC2 fleet"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: cloudwatch-dashboard-deployer]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create a cloudwatch dashboard"
# [Phase: Deploy | Skills routed: cloudwatch-dashboard-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the dashboard is created:

```bash
# Verify the dashboard exists and has the expected widgets
aws cloudwatch get-dashboard --dashboard-name prod-ec2-ops \
  --profile default \
  --query 'DashboardArn'

# Count widgets in the deployed dashboard
aws cloudwatch get-dashboard --dashboard-name prod-ec2-ops \
  --profile default \
  --query 'DashboardBody' --output text | jq '.widgets | length'

# Verify a specific metric is rendering
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average \
  --profile default
```
