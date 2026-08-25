# Worked Examples (load on demand) — CloudWatch Dashboards Operator

Secondary worked examples moved verbatim from SKILL.md; the primary example (create RDS monitoring dashboard) remains inline in SKILL.md. Loaded on demand.

---

## Worked example — cross-account via OAM (REVIEW_REQUIRED) (moved from SKILL.md)

```text
OPERATION: enable-cross-account
VERDICT: REVIEW_REQUIRED
TARGET: cross-account-rds-overview (monitoring account: 111111111111,
        source accounts: 222222222222, 333333333333)
PRE_CHECKS:
  - [PASS] OAM sink "org-monitoring-sink" exists in account 111111111111
  - [PASS] Source account 222222222222 linked (LinkStatus: LINKED)
  - [PASS] Source account 333333333333 linked (LinkStatus: LINKED)
  - [PASS] Dashboard body uses @Account variable for cross-account filter
  - [REVIEW] Enabling cross-account dashboard exposes metrics from
    accounts 222222222222 and 333333333333 in the monitoring account.
    Confirm that all stakeholders have authorized cross-account visibility.
  - [REVIEW] OAM link propagates CloudWatch metrics, Logs, and traces
    from source accounts. Verify the link configuration specifies
    MetricLink: true and the source accounts' metrics will appear with
    the @Account dimension.
  - [REVIEW] Dashboard includes Metrics Insights query that aggregates
    across all linked accounts:
    SELECT avg(CPUUtilization) FROM AWS/RDS GROUP BY @Account,
    DBInstanceIdentifier ORDER BY avg() DESC LIMIT 20
STEPS:
  1. CONFIRM: About to create cross-account dashboard
     "cross-account-rds-overview" with OAM filter for accounts
     222222222222 and 333333333333 in account 111111111111 region
     us-east-1. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name cross-account-rds-overview \
       --dashboard-body file://cross-account-rds-overview.json
  3. aws cloudwatch get-dashboard \
       --dashboard-name cross-account-rds-overview \
       --query 'DashboardName'
POST_VERIFY:
  - (pending operator confirmation and execution)
NOTES:
  - OAM sink must have AttachesToSourceAccountProperties matching the
    source account IDs. Verify with:
    aws oam get-sink --identifier org-monitoring-sink
  - Source accounts must have the OAM link with MetricLink: true:
    aws oam get-link --identifier <link-id> --region <source-region>
  - The @Account variable dropdown in the dashboard lets users filter
    by source account. Default is "*" (all accounts).
```

---

## Worked example — add anomaly detection (moved from SKILL.md)

```text
OPERATION: add-anomaly-detection
VERDICT: OPERATION_COMPLETED
TARGET: prod-lambda-errors (widget: anomaly band on Errors metric)
PRE_CHECKS:
  - [PASS] Namespace AWS/Lambda has published data
  - [PASS] Metric Errors has 14 days of history (optimal for training)
  - [PASS] Dashboard "prod-lambda-overview" exists (update operation)
  - [PASS] Current dashboard body captured for diff
STEPS:
  1. CONFIRM: About to add anomaly detection band (stdev: 2) on the
     Lambda Errors metric to dashboard "prod-lambda-overview" in
     account 111111111111 region us-east-1. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name prod-lambda-overview \
       --dashboard-body file://prod-lambda-overview-with-anomaly.json
  3. aws cloudwatch get-dashboard \
       --dashboard-name prod-lambda-overview \
       --query 'DashboardBody' --output text | jq '.widgets | length'
POST_VERIFY:
  - [PASS] Dashboard body updated (widget count: 6 → 7)
  - [PASS] Anomaly detection band widget present in body
  - [PASS] Band renders with expected range (training data sufficient)
NOTES:
  - Anomaly detection model uses the ANOMALY_DETECTION_BAND math function:
    ANOMALY_DETECTION_BAND(m1, 2) where m1 = Errors metric
  - stdev: 2 means the band covers 2 standard deviations from expected.
    Anomalies are values outside the band. Tune stdev to adjust
    sensitivity:
    - stdev 1: tight (more anomalies flagged, more false positives)
    - stdev 3: loose (fewer anomalies, may miss subtle deviations)
  - Set up an alarm on the anomaly detection band:
    aws cloudwatch put-metric-alarm \
      --alarm-name lambda-error-anomaly \
      --namespace AWS/Lambda \
      --metric-name AnomalyDetectionBand \
      --statistic Sum \
      --period 300 --evaluation-periods 2 \
      --threshold 0 --comparison-operator LessThanLowerOrGreaterThanUpperBand \
      --metrics '[{"Id":"m1","Label":"Errors","MetricStat":{"Metric":{"Namespace":"AWS/Lambda","MetricName":"Errors","Dimensions":[{"Name":"FunctionName","Value":"prod-api-handler"}]},"Period":300,"Stat":"Sum"}},{"Id":"ad1","Label":"Expected","Expression":"ANOMALY_DETECTION_BAND(m1,2)","ReturnData":true}]'
```

---

## Worked example — Metrics Insights dashboard (moved from SKILL.md)

```text
OPERATION: create-dashboard
VERDICT: OPERATION_COMPLETED
TARGET: top10-ec2-by-cpu (widgets: 3, Metrics Insights: 1)
PRE_CHECKS:
  - [PASS] Dashboard name "top10-ec2-by-cpu" does not already exist
  - [PASS] Namespace AWS/EC2 has published data
  - [PASS] Metrics Insights query syntax validated
  - [PASS] Dashboard body size: 4 KB (< 256 KB limit)
STEPS:
  1. CONFIRM: About to create dashboard "top10-ec2-by-cpu" with
     Metrics Insights query for top 10 EC2 instances by CPU utilization
     in account 111111111111 region us-east-1. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name top10-ec2-by-cpu \
       --dashboard-body file://top10-ec2-by-cpu.json
  3. aws cloudwatch get-dashboard \
       --dashboard-name top10-ec2-by-cpu \
       --query 'DashboardName'
POST_VERIFY:
  - [PASS] get-dashboard returns "top10-ec2-by-cpu"
  - [PASS] Metrics Insights widget renders top-10 table
  - [PASS] Query: SELECT avg(CPUUtilization) FROM AWS/EC2 WHERE
    AutoScalingGroupName LIKE 'prod-%' GROUP BY InstanceId ORDER BY
    avg() DESC LIMIT 10
NOTES:
  - Metrics Insights cost: $0.005 per 1,000 queries. At 5-minute
    auto-refresh, that is ~288 queries/day = ~$0.0014/day per widget.
  - The GROUP BY clause aggregates by InstanceId. Add more dimensions
    (e.g., InstanceType) for deeper analysis.
  - ORDER BY avg() DESC LIMIT 10 returns the top 10 by average CPU.
    Use MAX for peak utilization ranking.
```

---

## Worked example — dashboard IaC via Git (moved from SKILL.md)

```text
OPERATION: update-dashboard
VERDICT: OPERATION_COMPLETED
TARGET: prod-rds-overview (widgets: 8 → 10, diff: +2 widgets)
PRE_CHECKS:
  - [PASS] Dashboard "prod-rds-overview" exists
  - [PASS] Current body captured: /tmp/prod-rds-overview-pre-1234567890.json
  - [PASS] Proposed body validated (valid JSON, 10 widgets)
  - [PASS] Diff: 2 new widgets added (replica-lag-metric-math, alarm-secondary)
  - [PASS] No existing widgets removed (additive update)
STEPS:
  1. CONFIRM: About to update dashboard "prod-rds-overview" from 8 to
     10 widgets (additive: replica lag metric math + secondary alarm)
     in account 111111111111 region us-east-1. This OVERWRITES the
     entire dashboard body. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name prod-rds-overview \
       --dashboard-body file://dashboards/prod-rds-overview.json
  3. aws cloudwatch get-dashboard \
       --dashboard-name prod-rds-overview \
       --query 'DashboardBody' --output text | jq '.widgets | length'
POST_VERIFY:
  - [PASS] Widget count: 10 (was 8, +2 new widgets)
  - [PASS] New widgets render with data
  - [PASS] Existing widgets preserved (verified via diff)
NOTES:
  - The dashboard JSON is stored in dashboards/prod-rds-overview.json.
    The Git diff shows exactly which widgets changed:
    git diff HEAD~1 -- dashboards/prod-rds-overview.json
  - CI/CD pipeline deploys on merge to main:
    aws cloudwatch put-dashboard \
      --dashboard-name prod-rds-overview \
      --dashboard-body file://dashboards/prod-rds-overview.json
  - For environment-specific dashboards, use parameterized JSON:
    envsubst < dashboards/rds-overview.template.json > /tmp/rds-overview.json
    aws cloudwatch put-dashboard \
      --dashboard-name ${ENV}-rds-overview \
      --dashboard-body file:///tmp/rds-overview.json
```
