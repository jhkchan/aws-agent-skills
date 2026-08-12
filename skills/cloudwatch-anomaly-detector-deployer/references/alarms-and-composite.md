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
