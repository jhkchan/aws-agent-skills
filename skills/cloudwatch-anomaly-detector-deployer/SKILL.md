---
name: cloudwatch-anomaly-detector-deployer
description: 'Deploys Amazon CloudWatch Anomaly Detection models on AWS metrics with production defaults: anomaly detector creation (put-metric-anomaly-detector), metric math band visualization (ANOMALY_DETECTION_BAND), configuration (stat, period, assessment period), std dev multiplier tuning (default 3, lower = more sensitive), alert on band breach (upper or lower), recovery to normal state, cross-account anomaly detection, composite alarm integration, custom metrics vs built-in (CPU, network) support, and limitation detection (not all metrics support anomaly detection). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a CloudWatch anomaly detection model, configuring anomaly bands, tuning anomaly sensitivity, setting anomaly alarms, or visualizing anomaly detection bands. Triggers create anomaly detection model, cloudwatch anomaly detection, anomaly band breach alarm, tune anomaly sensitivity, anomaly detector std dev, anomaly detection custom metric, cross-account anomaly detection.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloudwatch and cloudwatch:PutMetricAnomalyDetector permissions. Works with Terraform aws_cloudwatch_anomaly_detector and aws_cloudwatch_metric_alarm resources and CloudFormation AWS::CloudWatch::AnomalyDetector templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudwatch, anomaly-detection, cloudops, deploy, monitoring, metric-math, alarms, sensitivity, cross-account
  dependencies: aws-orchestrator
  keywords: aws, cloudwatch, anomaly detection, anomaly detector, metric math, anomaly band, cloudops, deploy, std dev, sensitivity, composite alarm, custom metrics, cross-account
  when_to_use: Invoke when the user wants to create a CloudWatch Anomaly Detection model on a metric, visualize the anomaly detection band, configure an alarm on band breach, tune the anomaly sensitivity via standard deviation multiplier, deploy cross-account anomaly detection, or integrate anomaly detectors with composite alarms. Do NOT invoke for static-threshold CloudWatch alarms without anomaly detection, metric streaming (Kinesis), or Logs Insights anomaly detection.
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
| references/advanced-patterns.md | Compatibility + features detail |
| references/error-handling.md | Failure modes + remedies |

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

**This is the most commonly skipped step and the #1 cause of tickets.** Full compatibility table and verification command: [advanced-patterns.md](references/advanced-patterns.md). Sparse, irregular, constant-value, and counter metrics are poor candidates; if fewer than 15 data points exist at the target period, output `VERDICT: PREREQUISITES_MISSING`.

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

Full tuning guide: [sensitivity-and-tuning.md](references/sensitivity-and-tuning.md). Default `StandardDeviation` 3 (balanced); lower = more sensitive but more false positives, higher = less sensitive. Changes take up to 15 minutes (model re-trains).

## Step 5 — Band visualization (metric math)

Full procedure: [alarms-and-composite.md](references/alarms-and-composite.md). The `ANOMALY_DETECTION_BAND(m1)` metric-math expression renders the expected band in dashboards.

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

Full guide: [sensitivity-and-tuning.md](references/sensitivity-and-tuning.md). `evaluation-periods` 2-3 (default) balances detection speed vs false positives; verify ~2 weeks of historical data before creating the detector.

## Step 8 — Recovery to normal state

Full behavior: [alarms-and-composite.md](references/alarms-and-composite.md). The alarm returns to OK automatically after the same number of in-band evaluation periods; set `--ok-actions` for recovery notifications.

## Step 9 — Cross-account anomaly detection

Full setup: [alarms-and-composite.md](references/alarms-and-composite.md). The source account enables sharing (`put-resource-policy`); the monitoring account creates the link and hosts the detector + alarm.

## Step 10 — Composite alarm integration

Full patterns: [alarms-and-composite.md](references/alarms-and-composite.md). Combine anomaly + static-threshold alarms with AND/OR rules for layered alerting.

## Step 11 — Custom metrics vs built-in

Details: [advanced-patterns.md](references/advanced-patterns.md). Both built-in and custom metrics work with identical configuration; custom metrics must report regularly — check for sparse data on low-traffic functions.

## Step 12 — Recent features

Details: [advanced-patterns.md](references/advanced-patterns.md). Cross-account observability GA, high-resolution metric support, composite alarm enhancements, Logs Insights anomaly detection, Contributor Insights integration.

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

## References (load on demand)

- [Sensitivity and tuning](references/sensitivity-and-tuning.md) — std dev multiplier math, tuning workflow, assessment periods (Steps 4 and 7 in detail)
- [Alarms and composite integration](references/alarms-and-composite.md) — band-breach alarms, recovery to normal, cross-account setup, composite patterns, band visualization (Steps 5, 8, 9, and 10 in detail)
- [Advanced patterns](references/advanced-patterns.md) — metric compatibility edge cases, the two-week baseline, custom vs built-in metrics, recent features (Steps 2, 11, and 12 in detail)
- [Error handling](references/error-handling.md) — failure modes and remedies
- [End-to-end walkthrough](examples/README.md) — full worked example from invocation to verification

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
