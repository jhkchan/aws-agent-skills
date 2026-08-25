# Alarms and Composite Integration — CloudWatch Anomaly Detection Deployer

Deep reference on band-breach alarm configuration, metric math
expressions for anomaly detection alarms, composite alarm patterns
combining anomaly + static thresholds, recovery-to-normal behavior,
and cross-account alarm setup. Loaded on demand by the skill — kept
out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Band-breach alarm architecture

### How the alarm evaluates

A band-breach alarm uses metric math to compare the actual metric
value to the anomaly detection band. The evaluation cycle is:

```text
Every period (e.g., 300s):
  1. Fetch the actual metric value (m1)
  2. Fetch the anomaly band via ANOMALY_DETECTION_BAND(m1)
  3. Compare: is m1 above the upper band? Below the lower band?
  4. If breach: increment breach counter
  5. If breach counter >= evaluation-periods: transition to ALARM
  6. If no breach: reset breach counter; if was ALARM, transition to OK
```

### Upper band breach alarm

The most common pattern — alert when the metric exceeds the upper band
(e.g., CPU spike, latency increase).

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "cpu-anomaly-upper-breach" \
  --alarm-description "CPU above anomaly band for i-abc123" \
  --evaluation-periods 3 \
  --datapoints-to-alarm 3 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data "breaching" \
  --metrics '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization","Dimensions":[{"Name":"InstanceId","Value":"i-abc1234567890"}]},"Period":300,"Stat":"Average"}},
    {"Id":"e1","Expression":"ANOMALY_DETECTION_BAND(m1)","Label":"Band"},
    {"Id":"e2","Expression":"IF(m1 > e1, 1, 0)","Label":"BreachAbove","ReturnData":true}
  ]' \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --region us-east-1
```

### Lower band breach alarm

Alert when the metric drops below the lower band (e.g., traffic drop,
connection drop).

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "traffic-anomaly-lower-breach" \
  --alarm-description "Request count below anomaly band" \
  --evaluation-periods 3 \
  --datapoints-to-alarm 3 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data "breaching" \
  --metrics '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"RequestCount","Dimensions":[{"Name":"LoadBalancer","Value":"app/prod-alb/1234567890"}]},"Period":300,"Stat":"Sum"}},
    {"Id":"e1","Expression":"ANOMALY_DETECTION_BAND(m1)","Label":"Band"},
    {"Id":"e2","Expression":"IF(m1 < e1, 1, 0)","Label":"BreachBelow","ReturnData":true}
  ]' \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:outage-alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:outage-alerts" \
  --region us-east-1
```

### Either band breach (upper OR lower)

Alert on any deviation from the expected band.

```bash
# Use ABS to detect breach in either direction
"Expression": "IF(ABS(m1 - e1) > 0, 1, 0)"
```

Note: the `ANOMALY_DETECTION_BAND` function returns two values (upper
and lower). The comparison `m1 > e1` checks against the upper bound,
`m1 < e1` checks against the lower bound. To check either, use two
expressions and combine.

## Recovery to normal state

### Automatic recovery

When the metric returns inside the band, the alarm transitions back to
OK after the same number of evaluation periods required for the breach.

```text
Timeline example (evaluation-periods = 3):
  T1: metric inside band → OK
  T2: metric above band → breach counter = 1 → still OK
  T3: metric above band → breach counter = 2 → still OK
  T4: metric above band → breach counter = 3 → ALARM (SNS notification)
  T5: metric above band → breach counter = 4 → ALARM (no re-notification)
  T6: metric inside band → breach counter reset → recovery counter = 1 → still ALARM
  T7: metric inside band → recovery counter = 2 → still ALARM
  T8: metric inside band → recovery counter = 3 → OK (SNS OK notification if ok-actions set)
```

### OK actions for recovery notification

Set `--ok-actions` to receive an SNS notification when the alarm
recovers:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "cpu-anomaly-breach" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  ...
```

### Treat missing data

The `--treat-missing-data` parameter controls behavior when the metric
is not reporting:

| Value | Behavior | Use case |
|---|---|---|
| `breaching` | Missing data counts as anomalous | Default — better safe than sorry |
| `notBreaching` | Missing data counts as normal | When metric gaps are expected (e.g., no traffic at night) |
| `ignore` | Missing data is not counted | Maintain current alarm state |
| `missing` | Alarm goes to INSUFFICIENT_DATA | Strict — requires data to evaluate |

## Composite alarm patterns

### Pattern 1: Anomaly AND threshold (reduce false positives)

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "cpu-critical-composite" \
  --alarm-rule \
    "ALARM(\"cpu-anomaly-breach-i-abc123\") AND ALARM(\"cpu-high-threshold-i-abc123\")" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:critical-alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:critical-alerts" \
  --region us-east-1
```

This fires only when CPU is BOTH anomalous AND above 80%. Eliminates
false positives from expected high-usage periods.

### Pattern 2: Anomaly OR threshold (broad coverage)

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "latency-coverage-composite" \
  --alarm-rule \
    "ALARM(\"latency-anomaly-breach\") OR ALARM(\"latency-absolute-threshold\")" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:latency-alerts" \
  --region us-east-1
```

This fires on EITHER anomaly detection OR absolute threshold. Good for
layered coverage.

### Pattern 3: Anomaly with maintenance window suppression

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "cpu-anomaly-with-suppression" \
  --alarm-rule \
    "ALARM(\"cpu-anomaly-breach\") AND NOT ALARM(\"maintenance-mode-active\")" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --region us-east-1
```

This suppresses anomaly alarms during planned maintenance windows.

### Pattern 4: Multi-metric anomaly (any metric anomalous)

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "multi-metric-anomaly" \
  --alarm-rule \
    "ALARM(\"cpu-anomaly\") OR ALARM(\"memory-anomaly\") OR ALARM(\"disk-anomaly\")" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:infra-alerts" \
  --region us-east-1
```

## Cross-account alarm setup

### Architecture

```text
Source Account (222222222222)          Monitoring Account (111111111111)
  ┌─────────────────────┐                ┌───────────────────────────┐
  │  RDS Database       │                │  Anomaly Detector         │
  │  Connections metric │──sharing──────→│  (on source metric)       │
  │                     │   policy       │                           │
  │  Resource Policy    │                │  Band-Breach Alarm        │
  │  (allows monitoring │                │  (in monitoring account)  │
  │   account to read)  │                │                           │
  └─────────────────────┘                │  SNS Topic                │
                                          │  (in monitoring account)  │
                                          └───────────────────────────┘
```

### Step 1: Source account — enable sharing

```bash
# In the source account (222222222222)
aws cloudwatch put-resource-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "AWS": "arn:aws:iam::111111111111:root" },
        "Action": [
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --region us-east-1
```

### Step 2: Monitoring account — create link

```bash
# In the monitoring account (111111111111)
aws logs create-link \
  --link-name "source-account-metrics" \
  --resource-arn "arn:aws:logs:us-east-1:222222222222:log-group:*" \
  --filter 'logGroupNamePrefix("aws/cloudwatch/")'
```

### Step 3: Monitoring account — create detector and alarm

```bash
# In the monitoring account — create the anomaly detector
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/RDS" \
  --metric-name "DatabaseConnections" \
  --dimensions Name=DBInstanceIdentifier,Value=prod-db-001 \
  --stat "Average" \
  --period 300 \
  --configuration '{"StandardDeviation": 3}' \
  --region us-east-1

# Create the band-breach alarm in the monitoring account
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-anomaly-breach-prod-db-001" \
  --evaluation-periods 3 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --metrics '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/RDS","MetricName":"DatabaseConnections","Dimensions":[{"Name":"DBInstanceIdentifier","Value":"prod-db-001"}]},"Period":300,"Stat":"Average"}},
    {"Id":"e1","Expression":"ANOMALY_DETECTION_BAND(m1)"},
    {"Id":"e2","Expression":"IF(m1 > e1, 1, 0)","ReturnData":true}
  ]' \
  --alarm-actions "arn:aws:sns:us-east-1:111111111111:central-alerts" \
  --region us-east-1
```

## Terraform examples

### Anomaly detector + alarm

```hcl
resource "aws_cloudwatch_anomaly_detector" "cpu" {
  namespace   = "AWS/EC2"
  metric_name = "CPUUtilization"

  dimensions = {
    InstanceId = "i-abc1234567890"
  }

  stat   = "Average"
  period = 300

  configuration {
    excluded_time_ranges {}
    metric_timezone = "UTC"
  }
}

# The std dev multiplier is set via the configuration block
# In Terraform provider >= 5.0:
resource "aws_cloudwatch_anomaly_detector" "cpu" {
  namespace   = "AWS/EC2"
  metric_name = "CPUUtilization"

  dimensions = {
    InstanceId = "i-abc1234567890"
  }

  stat   = "Average"
  period = 300

  configuration {
    standard_deviation = 3
  }
}
```

### Composite alarm

```hcl
resource "aws_cloudwatch_composite_alarm" "cpu_critical" {
  alarm_name = "cpu-critical-composite"
  alarm_description = "CPU anomaly AND high threshold"

  alarm_rule = "ALARM(\"${aws_cloudwatch_metric_alarm.cpu_anomaly.alarm_name}\") AND ALARM(\"${aws_cloudwatch_metric_alarm.cpu_threshold.alarm_name}\")"

  alarm_actions = [aws_sns_topic.critical_alerts.arn]
  ok_actions    = [aws_sns_topic.critical_alerts.arn]
}
```

## Common alarm pitfalls

1. **Forgetting to set alarm-actions.** The alarm changes state but
   nobody is notified. Always include the SNS topic ARN.

2. **Setting evaluation-periods too low.** A single anomalous point
   triggers the alarm. Use at least 2-3 for production.

3. **Not setting ok-actions.** Without ok-actions, the recovery to
   normal state is silent. Set ok-actions for alarm lifecycle
   visibility.

4. **Using the wrong comparison operator.** The metric math expression
   uses an IF to produce 0 or 1; the alarm threshold should be 0 with
   GreaterThanThreshold. Using a different threshold/operator requires
   adjusting the expression.

5. **Not handling missing data.** Decide on `--treat-missing-data`
   explicitly. The default (`missing`) may cause INSUFFICIENT_DATA
   during expected gaps.

---

## Step 5 — Band visualization (metric math)

The anomaly detection band is visualized in the CloudWatch console
using metric math with the `ANOMALY_DETECTION_BAND` function. This
function returns the upper and lower band values for a given anomaly
detector.

**Metric math expression for band visualization:**

```text
ANOMALY_DETECTION_BAND(m1)
```

Where `m1` is the metric being monitored.

**CLI — create a metric math dashboard via put-dashboard:**

```bash
# The ANOMALY_DETECTION_BAND function produces upper/lower band values.
# In the console, this renders as a shaded band around the metric line.
aws cloudwatch put-dashboard \
  --dashboard-name "AnomalyDetection-CPU" \
  --dashboard-body '{"widgets":[{"type":"metric","x":0,"y":0,"width":12,"height":6,"properties":{"metrics":[["AWS/EC2","CPUUtilization","InstanceId","i-abc1234567890"],[{"expression":"ANOMALY_DETECTION_BAND(m1)","label":"Anomaly Band","id":"e1"}]],"view":"timeSeries","period":300,"stat":"Average"}}]}'
```

The `ANOMALY_DETECTION_BAND` function references the metric `m1`
(the first metric in the array) and produces the expected band.

---

## Step 8 — Recovery to normal state

When the metric value returns inside the anomaly band, the alarm
transitions back to `OK` automatically. This is the recovery-to-normal
behavior.

```text
Alarm state transitions:
  OK → ANOMALY (metric outside band for evaluation_periods)
  ANOMALY → OK (metric back inside band for evaluation_periods)
  OK → INSUFFICIENT_DATA (not enough data to evaluate, e.g., during LEARNING)
```

**Recovery behavior configuration:**

- `--evaluation-periods` controls how many consecutive in-band points
  are needed to recover to OK (same parameter as breach detection).
- The alarm evaluates BOTH breach and recovery using the same
  evaluation periods count. There is no separate recovery-period
  parameter.
- For asymmetric behavior (quick to alert, slow to recover), use
  different alarms or a composite alarm with state logic.

**OK action (notification on recovery):**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "cpu-anomaly-breach-i-abc123" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  ... # other parameters same as Step 6
```

Setting `--ok-actions` sends an SNS notification when the alarm
recovers to OK, providing closure on the anomaly event.

---

## Step 9 — Cross-account anomaly detection

CloudWatch supports cross-account anomaly detection, where a monitoring
(central) account creates anomaly detectors on metrics from member
accounts. This requires CloudWatch cross-account observability sharing.

**Prerequisites for cross-account:**
1. The member account must enable sharing (cloudwatch:PutResourcePolicy).
2. The monitoring account must have a data source link to the member
   account.
3. The anomaly detector is created in the monitoring account,
   referencing the member account's metric.

**Member account — enable sharing:**

```bash
aws cloudwatch put-resource-policy \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::111111111111:root"},"Action":["cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics"],"Resource":"*"}]}'
```

**Monitoring account — create detector and link:**

```bash
# Create data source link to member account
aws logs create-link --link-name "member-account-link" \
  --resource-arn "arn:aws:logs:us-east-1:222222222222:log-group:*" \
  --filter 'logGroupNamePrefix("aws/cloudwatch/")'

# Create detector (metric resolved from linked member account)
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" --period 300 \
  --configuration '{"StandardDeviation": 3}'
```

**Note:** cross-account observability uses the "source account" and
"monitoring account" model. The detector and alarm live in the
monitoring account. The metric data is read from the source account via
the sharing policy.

---

## Step 10 — Composite alarm integration

Composite alarms combine multiple alarms (anomaly + static threshold)
using AND/OR logic. This is useful for reducing false positives by
requiring multiple conditions to be true simultaneously.

**Example: anomaly breach AND high absolute threshold:**

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "cpu-composite-anomaly-and-threshold" \
  --alarm-rule "(ALARM(cpu-anomaly-breach-i-abc123) AND ALARM(cpu-high-threshold-i-abc123))" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:critical-alerts"
```

**Composite alarm logic patterns:**

| Pattern | Rule expression | Use case |
|---|---|---|
| Anomaly AND threshold | `ALARM(anomaly) AND ALARM(threshold)` | Reduce false positives; require both anomaly and high value |
| Anomaly OR threshold | `ALARM(anomaly) OR ALARM(threshold)` | Broad coverage; alert on either condition |
| Anomaly AND NOT maintenance | `ALARM(anomaly) AND NOT ALARM(maintenance-mode)` | Suppress anomalies during planned maintenance |
| Either of two metrics anomalous | `ALARM(cpu-anomaly) OR ALARM(memory-anomaly)` | Alert if either resource is anomalous |

**Key implication:** composite alarms let you combine anomaly detection
with static thresholds for a layered alerting strategy. This is the
recommended approach for production — use anomaly detection as the
primary signal and static thresholds as backstop coverage.
