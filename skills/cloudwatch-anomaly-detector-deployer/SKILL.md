---
name: cloudwatch-anomaly-detector-deployer
description: >-
  Deploys Amazon CloudWatch Anomaly Detection models on AWS metrics with
  production defaults: anomaly detector creation
  (put-metric-anomaly-detector), metric math band visualization
  (ANOMALY_DETECTION_BAND), configuration (stat, period, assessment
  period), std dev multiplier tuning (default 3, lower = more
  sensitive), alert on band breach (upper or lower), recovery to normal
  state, cross-account anomaly detection, composite alarm integration,
  custom metrics vs built-in (CPU, network) support, and limitation
  detection (not all metrics support anomaly detection). Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when creating
  a CloudWatch anomaly detection model, configuring anomaly bands,
  tuning anomaly sensitivity, setting anomaly alarms, or visualizing
  anomaly detection bands. Triggers create anomaly detection model,
  cloudwatch anomaly detection, anomaly band breach alarm, tune anomaly
  sensitivity, anomaly detector std dev, anomaly detection custom
  metric, cross-account anomaly detection.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with cloudwatch and
  cloudwatch:PutMetricAnomalyDetector permissions. Works with
  Terraform aws_cloudwatch_anomaly_detector and aws_cloudwatch_metric_alarm
  resources and CloudFormation AWS::CloudWatch::AnomalyDetector templates.
keywords:
  - aws
  - cloudwatch
  - anomaly detection
  - anomaly detector
  - metric math
  - anomaly band
  - cloudops
  - deploy
  - std dev
  - sensitivity
  - composite alarm
  - custom metrics
  - cross-account
tags:
  - aws
  - cloudwatch
  - anomaly-detection
  - cloudops
  - deploy
  - monitoring
  - metric-math
  - alarms
  - sensitivity
  - cross-account
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - cloudwatch
    - anomaly-detection
    - cloudops
    - deploy
    - monitoring
    - metric-math
    - alarms
    - sensitivity
    - cross-account
  dependencies:
    - aws-orchestrator
  keywords:
    - create anomaly detection model
    - cloudwatch anomaly detection
    - anomaly band breach alarm
    - tune anomaly sensitivity
    - anomaly detector std dev
    - anomaly detection custom metric
    - cross-account anomaly detection
  when_to_use: >-
    Invoke when the user wants to create a CloudWatch Anomaly Detection
    model on a metric, visualize the anomaly detection band, configure an
    alarm on band breach, tune the anomaly sensitivity via standard
    deviation multiplier, deploy cross-account anomaly detection, or
    integrate anomaly detectors with composite alarms. Do NOT invoke for
    static-threshold CloudWatch alarms without anomaly detection, metric
    streaming (Kinesis), or Logs Insights anomaly detection.
---

# CloudWatch Anomaly Detection Deployer

An AWS CloudOps agent skill that deploys Amazon CloudWatch Anomaly
Detection models with correct defaults. The skill walks the operator
through anomaly detector creation, metric math band visualization,
configuration (stat, period, assessment period), sensitivity tuning
(std dev multiplier), alarm-on-breach setup, recovery-to-normal
behavior, cross-account anomaly detection, composite alarm integration,
custom vs built-in metric support, and the critical limitation that not
all metrics support anomaly detection. It captures all configuration
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create anomaly detection model, CloudWatch anomaly detection, anomaly
band breach alarm, tune anomaly sensitivity, anomaly detector std dev,
anomaly detection custom metric, cross-account anomaly detection.

## STRICT output contract

When this skill is invoked with a CloudWatch Anomaly Detection
provisioning request (create an anomaly detector, configure an anomaly
band, set up a band-breach alarm, tune sensitivity, visualize bands, or
a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `ANOMALY_DETECTION:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based evals
and downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Anomaly detection model (ML baseline) | Core model concept |
| Step 2 — Metric compatibility check | Limitation: not all metrics supported |
| Step 3 — Configuration (stat, period, dimensions) | Detector parameters |
| Step 4 — Sensitivity tuning (std dev multiplier) | Default 3, lower = more sensitive |
| Step 5 — Band visualization (metric math) | ANOMALY_DETECTION_BAND |
| Step 6 — Alarm on band breach | Upper/lower breach alarms |
| Step 7 — Assessment period and training data | 2-week minimum |
| Step 8 — Recovery to normal state | Auto-recovery behavior |
| Step 9 — Cross-account anomaly detection | Cross-account metrics |
| Step 10 — Composite alarm integration | Combining anomaly + threshold |
| Step 11 — Custom metrics vs built-in | Metric type differences |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/sensitivity-and-tuning.md | Std dev multiplier detail |
| references/alarms-and-composite.md | Alarm + composite detail |

## Mindset

**One-line takeaway:** CloudWatch Anomaly Detection is a machine-
learning model that learns the normal expected value of a metric over
time and produces an expected-value band. When the actual metric value
falls outside the band (upper or lower), it is flagged as anomalous.
The model needs at least 15 data points (roughly 2 weeks at 5-minute
resolution) to establish a reliable baseline, and the band width is
controlled by the standard deviation multiplier (default 3; lower =
more sensitive, higher = less sensitive).

Three misconceptions dominate anomaly detection misdesign at provisioning
time:

- **"Anomaly detection works on any metric."** It does NOT. Not all
  CloudWatch metrics support anomaly detection. The model needs
  sufficient historical data (at least ~2 weeks) and the metric must
  produce regular data points. Metrics with sparse or irregular data
  (e.g., error counts that are usually zero) produce poor baselines.
  Always verify metric compatibility before deploying.

- **"A lower std dev is always better for catching anomalies."** It
  depends. The default std dev multiplier is 3 (meaning the band is
  roughly 3 standard deviations from the expected value). Lowering it
  to 1 or 2 makes the detector MORE sensitive (catches smaller
  deviations) but also increases FALSE POSITIVES. Raising it to 4 or 5
  makes it LESS sensitive (fewer false positives but may miss real
  anomalies). The right value depends on the metric's natural
  variability and the operational tolerance for false alerts.

- **"Anomaly detection replaces threshold alarms."** It complements
  them, not replaces them. Anomaly detection excels at metrics with
  variable but predictable patterns (e.g., request rates, CPU
  utilization that follows diurnal patterns). Static thresholds are
  still better for hard limits (e.g., error count > 0, disk usage >
  90%). Use composite alarms to combine both approaches.

## Configuration dependency graph (novel heuristic)

Anomaly detection configurations are NOT independent. The detector
needs historical data before it can produce a band. The alarm needs an
ACTIVE detector before it can evaluate. The std dev multiplier affects
both the band width and the alarm sensitivity. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Anomaly detector | metric exists with >= 15 historical data points; metric supports anomaly detection | detector returns `LEARNING` state until enough data; band not usable until `TRAINED` | the anomaly band |
| Band visualization | detector state `TRAINED`; metric math query with ANOMALY_DETECTION_BAND | band not visible in console until model is trained (can take 15 min after creation) | visual inspection of expected vs actual |
| Band-breach alarm | detector state `TRAINED`; alarm uses metric math expression comparing actual to band | alarm does not fire during LEARNING state; fires only when band is available | alerting on anomalies |
| Std dev multiplier | detector exists; configured at detector creation or via update | changing std dev takes effect after model re-trains (not immediate); lower = more sensitive | sensitivity control |
| Assessment period | alarm exists; controls how many consecutive data points must be anomalous | too few points = flappy alarm; too many = slow detection | alarm evaluation window |
| Composite alarm | one or more child alarms exist (anomaly + threshold) | composite evaluates AND/OR of children; child state changes propagate | combined alerting |
| Cross-account | cross-account sharing enabled (sharing policies or RAM); metric visible in monitoring account | detector in monitoring account sees shared metrics; latency in cross-account data | cross-account anomaly detection |

**The training-data row is the one a baseline model misses.** Creating
the detector without enough historical data results in a `LEARNING`
state where no band is produced. The alarm appears to be configured
correctly but never fires because the band does not exist. The
procedure below forces an explicit check on historical data depth.

**Cross-dependency gotchas:**
- The detector MUST reach `TRAINED` state before the band is usable
  (requires >= 15 data points at the configured period).
- Std dev multiplier changes take up to 15 minutes (model re-trains).
- Cross-account detection requires metric sharing (resource policy or
  RAM). A detector on a non-shared metric sees no data.
- Composite alarms evaluate AND/OR of children; a child in
  `INSUFFICIENT_DATA` may propagate to the composite.

## Expert heuristic: the two-week baseline requirement

A baseline model says "create the detector and attach an alarm." The
correct heuristic recognizes that the ML model needs historical data to
learn the expected pattern, and without it, the band does not exist.

```text
Metric data timeline:
  Past ──────────────────────────────────── Present ──── Future
  │←──── historical data (>= 15 points) ────→│
  │                                          │
  │  Detector created here ─────────────────→│  LEARNING → TRAINED
  │                                          │
  │  Band available here ───────────────────→│  Alarm can fire
  │                                          │

If < 15 historical data points exist:
  Detector stays in LEARNING indefinitely
  Band never produced
  Alarm never fires (INSUFFICIENT_DATA)
```

**Key implication:** always verify the metric has at least 2 weeks of
historical data at the target period (5 min, 1 min, etc.) before
creating the detector. If the metric is new, wait 2 weeks before
deploying anomaly detection, or use a shorter-period metric that
accumulates 15 points faster.

## Expert heuristic: std dev multiplier tuning

The standard deviation multiplier controls the band width and thus the
sensitivity of anomaly detection.

```text
Std dev multiplier guide:
  ├── 1.0  → Very sensitive (catches small deviations, many false positives)
  │        Use for: critical metrics where any deviation matters
  ├── 2.0  → Sensitive (good starting point for volatile metrics)
  │        Use for: error rates, latency percentiles with high variance
  ├── 3.0  → DEFAULT (balanced, the AWS-recommended starting point)
  │        Use for: CPU utilization, request count, network traffic
  ├── 4.0  → Less sensitive (fewer false positives, may miss small anomalies)
  │        Use for: metrics with known periodic spikes (batch jobs)
  └── 5.0  → Very insensitive (only catches major anomalies)
             Use for: metrics where only severe deviations matter

Rule of thumb: start at 3, observe for 1 week, tune down if missing
real anomalies, tune up if too many false positives.
```

**Key implication:** the std dev multiplier is the primary tuning knob
after deployment. It is not set-and-forget; plan for a tuning cycle
after initial deployment.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Metric exists in CloudWatch | Detector requires a live metric namespace/name | `aws cloudwatch get-metric-statistics` returns data |
| >= 15 historical data points at target period | ML model needs ~2 weeks of baseline data | `aws cloudwatch get-metric-statistics` with 15-day window |
| Metric supports anomaly detection | Not all metrics support it (sparse, irregular metrics fail) | Verify metric produces regular data points; check AWS docs for excluded metric types |
| Namespace, metric name, dimensions identified | Detector configuration requires these | Confirm from CloudWatch console or API |
| Stat configured (Sum, Average, etc.) | Detector evaluates one stat per configuration | Choose the stat that reflects the metric's behavior |
| Period configured (60, 300, etc.) | Determines resolution of the anomaly band | Match the metric's reporting period |
| SNS topic ARN (for alarm notifications) | Band-breach alarm needs an SNS topic for notifications | `aws sns list-topics` |
| IAM permissions | Need cloudwatch:PutMetricAnomalyDetector, cloudwatch:PutMetricAlarm | Verify IAM policy |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Anomaly detection model (ML baseline)

CloudWatch Anomaly Detection applies a machine-learning model to a
CloudWatch metric. The model learns the metric's normal expected value
based on historical data and produces two output values: the expected
upper bound and the expected lower bound. Together, these form the
anomaly detection band.

| Concept | Description |
|---|---|
| Model type | Random cut forest (RCF) based ML model |
| Training data | Historical metric data (minimum 15 data points at target period) |
| Output | Expected value, upper band, lower band |
| Band width | Controlled by std dev multiplier (default 3) |
| State transitions | LEARNING → TRAINED (once enough data is processed) |
| Re-training | Continuous; model adapts to recent data patterns |

**The detector API:**

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300 \
  --configuration '{"StandardDeviation": 3}'
```

The detector enters `LEARNING` state immediately. Once it has processed
enough historical data (typically within 15 minutes of creation if
sufficient data exists), it transitions to `TRAINED` state and begins
producing the anomaly band.

## Step 2 — Metric compatibility check

**This is the most commonly skipped step and the #1 cause of "my
anomaly detector doesn't work" tickets.**

Not all CloudWatch metrics support anomaly detection. The model needs
metrics that produce regular, frequent data points with enough history.
The following metric characteristics indicate POOR compatibility:

| Metric characteristic | Why it fails | Recommendation |
|---|---|---|
| Sparse data (mostly zero, occasional spikes) | Model cannot learn a baseline from mostly-zero data | Use static threshold > 0 |
| Irregular intervals (data only when events occur) | No pattern to learn | Use static threshold or Logs Insights |
| Less than 15 data points at target period | Insufficient training data | Wait for more data; use shorter period |
| Constant value (no variability) | Model trains but band is trivially narrow; every change is anomalous | Use static threshold for delta detection |
| Counter metrics (monotonically increasing) | Model learns the rate of increase, not the absolute value | Use a rate/derivative metric instead |

**Compatible metrics (good candidates):**
- `AWS/EC2 CPUUtilization` — regular, frequent, diurnal patterns
- `AWS/ApplicationELB RequestCount` — traffic patterns
- `AWS/RDS DatabaseConnections` — usage patterns
- Custom metrics that report regularly (e.g., request latency, queue
  depth, active sessions)
- `AWS/NetworkELB ProcessedBytes` — network throughput patterns

**Verify metric compatibility:**

```bash
# Check if the metric has sufficient data points
aws cloudwatch get-metric-statistics \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --statistics Average \
  --period 300 \
  --start-time $(date -u -v-15d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Datapoints | length(@)' --output text
# Expected: >= 15 (ideally thousands for 2 weeks at 5-min period)
```

If the result is less than 15, the metric does not have enough data for
a reliable baseline. Output `VERDICT: PREREQUISITES_MISSING`.

## Step 3 — Configuration (stat, period, dimensions)

The anomaly detector configuration defines which metric, which
statistic, what period, and what dimensions to monitor.

| Parameter | Description | Common values |
|---|---|---|
| Namespace | CloudWatch metric namespace | `AWS/EC2`, `AWS/RDS`, `MyApp` (custom) |
| MetricName | The metric to monitor | `CPUUtilization`, `RequestCount`, `Latency` |
| Dimensions | Metric dimensions (specific instance, LB, etc.) | `InstanceId=i-xxx`, `LoadBalancer=app/xxx` |
| Stat | Aggregation method | `Average`, `Sum`, `Maximum`, `p99` (percentile) |
| Period | Resolution in seconds | `60` (1 min), `300` (5 min), `900` (15 min) |

**Stat selection guide:**

```text
Metric type → Recommended stat:
  ├── Gauge metrics (CPU, memory, connections)
  │     → Average (smooths out momentary spikes)
  ├── Count metrics (requests, errors, bytes)
  │     → Sum (total per period)
  ├── Latency metrics (response time)
  │     → p99 or p99.9 (tail latency is what matters)
  └── Utilization metrics (disk, memory)
        → Average or Maximum
```

**Period selection guide:**

```text
Use case → Recommended period:
  ├── Real-time anomaly detection (sub-minute)
  │     → 60 seconds (1 min)
  │     Requires metric reporting at 1-min resolution
  ├── Standard anomaly detection
  │     → 300 seconds (5 min) — DEFAULT
  │     Good balance of resolution and noise reduction
  └── Long-term trend anomaly detection
        → 900 seconds (15 min) or 3600 (1 hr)
        For batch or hourly patterns
```

**Create the detector with configuration:**

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300 \
  --configuration '{"StandardDeviation": 3}'
```

## Step 4 — Sensitivity tuning (std dev multiplier)

The standard deviation multiplier (`StandardDeviation` in the
configuration JSON) is the primary tuning knob for anomaly detection
sensitivity. It controls how wide the expected-value band is.

| Std dev multiplier | Sensitivity | Band width | False positive rate | Use case |
|---|---|---|---|---|
| 1 | Very high | Narrow (1 sigma) | High | Critical metrics, any deviation matters |
| 2 | High | Medium (2 sigma) | Moderate | Error rates, volatile latency |
| 3 (DEFAULT) | Balanced | Standard (3 sigma) | Low | CPU, network, request count |
| 4 | Low | Wide (4 sigma) | Very low | Metrics with periodic spikes |
| 5 | Very low | Very wide (5 sigma) | Minimal | Only severe anomalies matter |

**Tuning procedure:**

1. Deploy with default (3).
2. Observe for at least 1 week.
3. If too many false positives: increase to 4.
4. If missing real anomalies: decrease to 2.
5. Re-observe for another week. Iterate.

**Update std dev multiplier (post-deployment tuning):**

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300 \
  --configuration '{"StandardDeviation": 2}'
```

**Note:** Changing the std dev triggers a model re-train. The new band
appears within 15 minutes. The alarm continues to use the old band
until the model re-trains.

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

## Step 6 — Alarm on band breach

The primary use case for anomaly detection is alerting when the metric
value falls outside the expected band. This is done with a CloudWatch
alarm using metric math.

**Alarm expression — breach above the upper band:**

```text
m1 > ANOMALY_DETECTION_BAND(m1)
```

**Alarm expression — breach below the lower band:**

```text
m1 < ANOMALY_DETECTION_BAND(m1)
```

**Create an alarm on band breach:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "cpu-anomaly-breach-i-abc123" \
  --alarm-description "CPU utilization anomaly breach for i-abc1234567890" \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data "breaching" \
  --metrics '[
    { "Id": "m1", "MetricStat": { "Metric": { "Namespace": "AWS/EC2", "MetricName": "CPUUtilization", "Dimensions": [{"Name":"InstanceId","Value":"i-abc1234567890"}] }, "Period": 300, "Stat": "Average" } },
    { "Id": "e1", "Expression": "ANOMALY_DETECTION_BAND(m1)", "Label": "Band" },
    { "Id": "e2", "Expression": "IF(m1 > e1, 1, 0)", "Label": "BreachAbove" }
  ]' \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts"
```

**Breach direction:**

| Breach type | Expression | Use case |
|---|---|---|
| Upper band breach | `m1 > ANOMALY_DETECTION_BAND(m1)` | CPU spikes, latency increases, error rate jumps |
| Lower band breach | `m1 < ANOMALY_DETECTION_BAND(m1)` | Traffic drops (possible outage), connection drops |
| Either band breach | `ABS(m1 - ANOMALY_DETECTION_BAND(m1)) > 0` | Any deviation from expected |

**Critical:** the alarm uses `evaluation-periods` to require consecutive
anomalous data points. Set to at least 2-3 to avoid flapping on
momentary spikes.

## Step 7 — Assessment period and training data

The assessment period (controlled by `evaluation-periods` on the alarm)
determines how many consecutive anomalous data points must occur before
the alarm fires.

| Assessment periods | Behavior | Trade-off |
|---|---|---|
| 1 | Fires on a single anomalous point | Very fast detection; high false positive rate |
| 2-3 (DEFAULT) | Requires 2-3 consecutive anomalous points | Balanced; good starting point |
| 5+ | Requires sustained anomaly over many periods | Low false positives; slower detection |

**Training data depth check (PREREQUISITE):**

```bash
# Count data points in the last 15 days at 5-min period
DATAPOINTS=$(aws cloudwatch get-metric-statistics \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --statistics Average \
  --period 300 \
  --start-time $(date -u -v-15d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Datapoints | length(@)' --output text)

echo "Historical data points: $DATAPOINTS"
# If < 15 → PREREQUISITES_MISSING (insufficient training data)
# If >= 15 → proceed with detector creation
```

**The 2-week rule:** the ML model needs approximately 2 weeks of data
to learn the metric's pattern (especially diurnal/weekly cycles). With
less data, the model may not capture weekend vs weekday differences,
time-of-day patterns, etc. If the metric is new, wait 2 weeks before
deploying anomaly detection.

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

## Step 11 — Custom metrics vs built-in

Anomaly detection works on BOTH built-in AWS metrics and custom metrics.
The configuration is identical; only the namespace and metric name
differ. Built-in AWS metrics (`AWS/EC2`, `AWS/RDS`, `AWS/ApplicationELB`)
are well-tested. Custom metrics work if they report regularly at 1-min
or 5-min resolution. High-resolution custom metrics (1-second) also
work but accumulate training data faster. Container Insights and Lambda
Insights metrics are supported — check for sparse data on low-traffic
functions.

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Cross-account observability GA (2023-2024):** Anomaly detectors
  and alarms in a central monitoring account evaluating metrics from
  multiple member accounts.
- **High-resolution metric support (2023-2024):** 1-second resolution
  custom metrics with anomaly detection.
- **Composite alarm enhancements (2023-2024):** Extended rule syntax
  with NOT, nested AND/OR, INSUFFICIENT_DATA state references.
- **Logs Insights anomaly detection (2024-2025):** Anomaly detection
  for log-based metrics.
- **Contributor Insights integration (2025-2026):** Automatically
  surfaces top contributors when an anomaly is detected.

## NEVER do these things

1. **NEVER create an anomaly detector without verifying >= 15
   historical data points.** The ML model needs sufficient training
   data. With less than 15 data points at the target period, the
   detector stays in LEARNING state indefinitely and the band is never
   produced. This is the #1 cause of "my anomaly alarm never fires."

2. **NEVER assume anomaly detection works on all metrics.** Sparse
   metrics (mostly zero with occasional spikes), irregular metrics,
   and constant-value metrics produce poor baselines. Always verify
   metric compatibility before deploying.

3. **NEVER set evaluation-periods to 1 for production alarms.** A
   single anomalous data point triggers the alarm, causing excessive
   false positives. Use at least 2-3 consecutive periods for
   production alerting.

4. **NEVER forget the SNS topic for alarm actions.** Without an
   `--alarm-actions` SNS topic ARN, the alarm changes state but nobody
   is notified. The alarm fires silently.

5. **NEVER assume the std dev multiplier takes effect immediately.**
   Changing the multiplier triggers a model re-train, which takes up
   to 15 minutes. Plan for the delay when tuning.

6. **NEVER use anomaly detection for metrics with known regular spikes
   without tuning the std dev up.** Metrics like batch-processing CPU
   (spikes every hour on the hour) will generate false positives at
   the default std dev of 3. Increase to 4 or 5 to accommodate known
   patterns.

7. **NEVER create cross-account anomaly detectors without verifying
   the sharing policy.** The monitoring account needs a resource
   policy on the source account allowing GetMetricData. Without it,
   the detector sees no data and stays in LEARNING.

8. **NEVER use a composite alarm with a single child alarm.** A
   composite alarm with one child provides no benefit over the child
   alarm alone. Use composite alarms only when combining 2+ alarms
   with AND/OR logic.

9. **NEVER deploy anomaly detection without a tuning plan.** The std
   dev multiplier default of 3 is a starting point, not a final value.
   Plan for at least one tuning cycle after a week of observation.

10. **NEVER use anomaly detection alone for critical alerting.**
    Always pair anomaly detection with a static-threshold backstop
    alarm via composite alarm. Anomaly detection can miss edge cases
    (e.g., gradual drift that stays within the expanding band).

## Output format

```text
ANOMALY_DETECTION: <namespace>/<metric-name> [dimensions] (<detector-state>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Metric: <namespace>/<metric-name> [<dimensions>]
  [✓|✗] Historical data: <count> data points at <period>s (need >= 15)
  [✓|✗] Metric compatibility: PASS (regular data) | FAIL (sparse/irregular)
  [✓|✗] Stat: <Average|Sum|Maximum|p99>
  [✓|✗] Period: <60|300|900> seconds
  [✓|✗] Std dev multiplier: <value> (default 3; lower = more sensitive)
  [✓|✗] Detector state: LEARNING | TRAINED
  [✓|✗] Band breach alarm: <alarm-name> (upper|lower|both, evaluation-periods=<n>)
  [✓|✗] SNS notification: <sns-topic-arn>
  [✓|✗] Recovery to OK: enabled (ok-actions configured) | not configured
  [✓|✗] Cross-account: monitoring account <account-id>, source account <account-id> | single-account
  [✓|✗] Composite alarm: <composite-alarm-name> (rule) | none
  [✓|✗] Metric type: built-in (<namespace>) | custom (<namespace>)
VERIFICATION_COMMANDS:
  aws cloudwatch describe-anomaly-detectors --namespace <namespace> --region <region>
  aws cloudwatch describe-alarms --alarm-names <alarm-name> --region <region>
  aws cloudwatch get-metric-statistics --namespace <namespace> --metric-name <metric-name> --statistics <stat> --period <period> --start-time <15d-ago> --end-time <now> --region <region>
```

### Worked example — CPU anomaly detection with band-breach alarm

```text
ANOMALY_DETECTION: AWS/EC2/CPUUtilization [InstanceId=i-abc1234567890] (TRAINED)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Metric: AWS/EC2/CPUUtilization [InstanceId=i-abc1234567890]
  [✓] Historical data: 4320 data points at 300s (need >= 15) — 15 days of 5-min data
  [✓] Metric compatibility: PASS (regular data, diurnal pattern)
  [✓] Stat: Average
  [✓] Period: 300 seconds (5 min)
  [✓] Std dev multiplier: 3 (default — balanced)
  [✓] Detector state: TRAINED
  [✓] Band breach alarm: cpu-anomaly-breach-i-abc123 (upper, evaluation-periods=3)
  [✓] SNS notification: arn:aws:sns:us-east-1:123456789012:anomaly-alerts
  [✓] Recovery to OK: enabled (ok-actions configured)
  [✓] Cross-account: single-account (123456789012)
  [✓] Composite alarm: none (standalone anomaly alarm)
  [✓] Metric type: built-in (AWS/EC2)
VERIFICATION_COMMANDS:
  aws cloudwatch describe-anomaly-detectors --namespace AWS/EC2 --region us-east-1
  aws cloudwatch describe-alarms --alarm-names cpu-anomaly-breach-i-abc123 --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --statistics Average --period 300 --start-time 2026-07-28T00:00:00Z --end-time 2026-08-12T00:00:00Z --region us-east-1
```

## Error handling

### Detector stuck in LEARNING state
- The metric does not have enough historical data points. Verify with
  `get-metric-statistics` that at least 15 data points exist at the
  configured period. If the metric is new, wait for more data to
  accumulate. Also check that the namespace, metric name, and
  dimensions match the actual metric exactly.

### Alarm in INSUFFICIENT_DATA
- The detector has not reached TRAINED state, or the metric is not
  producing data. Check the detector state with
  `describe-anomaly-detectors`. If TRAINED, check the alarm's metric
  math expression for errors. Verify the SNS topic exists.

### Too many false positive alarms
- The std dev multiplier is too low for the metric's natural
  variability. Increase the multiplier (3 → 4) and wait for the model
  to re-train (up to 15 minutes). Also consider increasing
  evaluation-periods (3 → 5) for more sustained anomaly detection.

### Anomaly alarm never fires
- Possible causes: (1) detector in LEARNING state (not enough data),
  (2) std dev multiplier too high (band too wide), (3) alarm metric
  math expression is wrong, (4) SNS topic not configured. Check each
  in order.

### Cross-account detector sees no data
- The source account has not enabled sharing, or the monitoring
  account does not have the correct data source link. Verify the
  resource policy in the source account and the link in the monitoring
  account.

## Domain

AWS CloudOps / Amazon CloudWatch Anomaly Detection & ML-Based Metric
Monitoring.

## AWS documentation

- **CloudWatch Anomaly Detection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html
- **Create an anomaly detector** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection_Create.html
- **Anomaly detection alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection_Alarm.html
- **Metric math** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html
- **Composite alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html
- **Cross-account observability** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Cross-Account-Setup.html
- **put-metric-anomaly-detector API** — https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/put-metric-anomaly-detector.html
- **CloudWatch pricing** — https://aws.amazon.com/cloudwatch/pricing/
