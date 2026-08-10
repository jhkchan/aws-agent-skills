# CloudWatch Alarm Patterns and Diagnosis Reference

Load this reference when planning or executing any CloudWatch alarm
operation. The procedures below are the canonical sequences for each
alarm archetype, with pre-checks, command sequence, post-verification,
and rollback notes.

## Decision tree — which alarm archetype

| Scenario | Use | Why |
|---|---|---|
| Utilization with known ceiling (CPU, disk, memory) | **Static threshold** | Well-understood capacity limits — static % works |
| Binary/status (StatusCheckFailed, backup failures) | **Static threshold (> 0)** | Any breach is bad — no need for anomaly detection |
| Countdown (cert expiry) | **Static threshold (< N)** | Monotonic countdown — static works |
| High-variance metric (latency, traffic, error rate) | **Anomaly detection** | Adapts to seasonality, avoids flood-or-miss |
| Ratio of two metrics (error rate = errors / requests) | **Metric math** | Combines multiple metrics into one alarm |
| Reduce alarm fatigue across N child alarms | **Composite alarm** | Boolean OR/AND rollup with escalation action |
| Auto-remediation on instance failure | **EC2 recover action** | In-place instance recovery |
| Auto-remediation on breach | **SNS → Lambda / SNS → SSM** | Trigger downstream automation |
| Capacity scaling on load | **Auto Scaling policy action** | Scale out/in tied to alarm state |

## Static threshold alarm procedure

**When to use:** utilization, binary status, countdown metrics.

**Pre-checks:**
1. Namespace + MetricName + Dimensions return datapoints via
   `get-metric-statistics` (case-sensitive).
2. Period >= metric native publishing interval.
3. DatapointsToAlarm <= EvaluationPeriods.
4. Threshold achievable per `get-metric-statistics` observed range.
5. Statistic matches metric semantics (Sum for counts, Average for
   utilization, SampleCount for volume).
6. AlarmActions / OKActions ARNs exist; <= 5 per category.
7. TreatMissingData set explicitly.

**Command sequence:**
```bash
# 1. Snapshot existing alarm (if updating)
aws cloudwatch describe-alarms --alarm-names <name> --output json \
  > /tmp/<name>-backup-$(date +%s).json

# 2. Sample the metric range (informs Threshold choice)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Maximum \
  --output table

# 3. CONFIRM gate, then put-metric-alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "<name>" \
  --alarm-description "<description with runbook link>" \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Average --period 300 \
  --evaluation-periods 1 --datapoints-to-alarm 1 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical \
  --ok-actions arn:aws:sns:us-east-1:111111111111:on-call-info

# 4. Verify
aws cloudwatch describe-alarms --alarm-names <name>
```

**Post-verification:**
- `describe-alarms` returns the expected config.
- `StateValue` transitions from INSUFFICIENT_DATA to OK after one
  evaluation cycle.
- Trigger a synthetic breach (optional) to confirm the alarm fires.

**Common failure modes:**
- `INSUFFICIENT_DATA` persists — wrong namespace, wrong dimensions, or
  the resource is stopped/terminated.
- Alarm never fires despite apparent breach — Statistic/Period mismatch
  with operator's mental model; verify via `get-metric-statistics` with
  the alarm's exact Period and Statistic.

## Anomaly detection alarm procedure

**When to use:** high-variance metrics (latency, traffic, error rate)
with seasonality or trend drift.

**Two-step procedure (REQUIRED):**

```bash
# STEP 1: Create the anomaly detector FIRST
aws cloudwatch put-anomaly-detector \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --stat Average \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890

# Wait ~15 min for the band to populate. Verify via:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
  --start-time $(date -u -d '15 min ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average

# STEP 2: Create the alarm against the band
aws cloudwatch put-metric-alarm \
  --alarm-name "alb-latency-anomaly-prod" \
  --namespace AWS/ApplicationELB \
  --metrics \
    "m1,TargetResponseTime,Average,60,LoadBalancer,app/prod-alb/1234567890" \
    "ad1,ANOMALY_DETECTION_BAND(m1,2),60" \
  --comparison-operator GreaterThanUpperThreshold \
  --evaluation-periods 3 --datapoints-to-alarm 2 \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

**Standard deviation guide:**
- stdev 1 = very tight, frequent false positives (rarely correct).
- stdev 2 = moderate, the typical default.
- stdev 3 = conservative, major incidents only.

**Common failure modes:**
- Bands empty for a new detector — wait 15 min for warm-up.
- Bands too wide (every metric looks normal) — metric has extreme
  variance; consider cleaning the data first (remove outliers) or use a
  different metric.
- Bands too tight (constant false alarms) — increase stdev.

## Composite alarm procedure

**When to use:** reduce alarm fatigue by rolling up N child alarms with
boolean logic into one escalation alarm.

**Pre-checks:**
1. Every `ALARM(name)` / `OK(name)` reference in Rule exists in the
   account+region.
2. Rule length <= 512 characters.
3. <= 100 distinct alarm references.
4. AlarmActions includes an ESCALATION target distinct from child
   alarms (otherwise the composite adds no notification value).

**Command sequence:**
```bash
aws cloudwatch put-composite-alarm \
  --actions-enabled \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-escalation \
  --alarm-name "prod-checkout-critical-rollup" \
  --alarm-description "Escalation: any of {5xx, latency, lambda errors}" \
  --alarm-rule "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)"
```

**Rule design patterns:**
- `OR` — escalation: any child triggers the composite.
- `AND` — correlated: requires multiple symptoms (use carefully — both
  children must be in ALARM simultaneously).
- `NOT ALARM(child)` — "anti-signal": composite fires when a child
  should be ALARM but isn't (e.g., backup not firing when expected).

## Diagnostic procedure — alarm stuck in INSUFFICIENT_DATA

```bash
# 1. Inspect the alarm config
aws cloudwatch describe-alarms --alarm-names <name>

# 2. Check if the metric is publishing
aws cloudwatch get-metric-statistics \
  --namespace <ns> --metric-name <mn> \
  --dimensions <dims> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period <period> --statistics <stat>

# 3. If no datapoints: fix the namespace/dimensions
# 4. If datapoints exist: check Period alignment and EvaluationPeriods

# 5. Remediation: set TreatMissingData to breaching
aws cloudwatch put-metric-alarm \
  --alarm-name <name> \
  --treat-missing-data breaching \
  [...rest of the existing config...]
```

## Alarm action wiring matrix

| Action target | ARN pattern | Use case |
|---|---|---|
| SNS topic | `arn:aws:sns:<region>:<acct>:<topic>` | Notify on-call, fan-out to email/Lambda/HTTPS |
| Auto Scaling policy | `arn:aws:autoscaling:<region>:<acct>:scalingPolicy:...` | Scale out/in on breach |
| EC2 recover | `arn:aws:automate:<region>:ec2:recover` | In-place instance recovery on System status fail |
| EC2 stop | `arn:aws:automate:<region>:ec2:stop` | Stop a runaway instance |
| EC2 reboot | `arn:aws:automate:<region>:ec2:reboot` | Reboot on System status fail (less aggressive than recover) |
| EC2 terminate | `arn:aws:automate:<region>:ec2:terminate` | Terminate (Auto Scaling group will replace) |
| Systems Manager | via SNS → SSM | Trigger SSM Automation runbook |

## TreatMissingData decision guide

| Value | Behavior | Best for |
|---|---|---|
| `breaching` | Treat missing as breach → ALARM | Availability metrics (missing = system down) |
| `notBreaching` | Treat missing as within bounds → OK | Error/count metrics (missing = zero events) |
| `ignore` | Hold current state | Transient gaps during deploys |
| `missing` (default) | Enter INSUFFICIENT_DATA | Almost never the desired behavior for production |

## M-of-N tuning guide

| Urgency | DatapointsToAlarm | EvaluationPeriods | Period | Detection lag |
|---|---|---|---|---|
| Critical (security, payment) | 1 | 1 | 60 | 1-2 min |
| High (production availability) | 1 | 2 | 60 | 2-4 min |
| Medium (warning) | 2 | 3 | 300 | 10-15 min |
| Low (capacity) | 3 | 5 | 300 | 15-25 min |

Trade-off: lower DatapointsToAlarm = faster response + more false
positives from transient spikes. Higher DatapointsToAlarm = slower
response + more confidence.

## Cost reference (2026)

- Standard alarm (Period >= 60): $0.10/alarm/month in us-east-1.
- High-resolution alarm (Period 10/30): $0.30/alarm/month.
- Composite alarm: $0.50/alarm/month.
- Anomaly detection: charged per detector, ~$0.30/detector/month.
- Metric math custom metrics: $0.30/metric/month (1000 metrics free).
- INSUFFICIENT_DATA alarms: free (no evaluations counted).

For a fleet of 500 standard alarms + 20 composite + 50 anomaly
detectors, monthly cost is ~$75 — usually negligible vs. operational
value.

## Edge case: alarm stuck in ALARM after metric stops reporting

When a metric was breaching and then STOPS reporting entirely (sensor
failure, instance terminated, agent crashed mid-incident), the alarm's
behavior depends on TreatMissingData:

| TreatMissingData | Behavior when metric stops mid-breach |
|---|---|
| `missing` (default) | Transitions to INSUFFICIENT_DATA after next cycle — `InsufficientDataActions` fires (usually empty = silent) |
| `breaching` | Stays in ALARM forever — missing data treated as continuing to breach |
| `notBreaching` | Transitions to OK after next cycle — `OKActions` fires (if configured) |
| `ignore` | Stays in ALARM forever — alarm holds its last evaluated state |

**The "stuck in ALARM forever" trap:** with `TreatMissingData: breaching`
(common for security/availability alarms), an alarm that fired legitimately
and then lost its metric source stays in ALARM even after the underlying
issue is resolved and the resource is terminated. On-call receives no "all
clear" because:
1. The metric is gone, so no OK datapoint can ever clear the breach.
2. `OKActions` only fires on a real OK transition, not on alarm deletion.

**Diagnostic steps:**
1. `describe-alarms --alarm-names <name>` — confirm `StateValue: ALARM`
   and `StateUpdatedTimestamp` is old (>24h).
2. `get-metric-statistics` over last hour — if empty, the metric stopped.
3. Check the resource: is the EC2 instance terminated? Lambda deleted?
   ALB gone?

**Fix options:**
- If the resource is gone: `delete-alarms` — the alarm monitors nothing.
- If the resource exists but agent/sensor is broken: fix the sensor; the
  alarm will self-clear on the next OK datapoint.
- To force-clear without waiting: snapshot config, then
  `set-alarm-state --state-value OK --state-reason "manual override
  after sensor recovery"` (use sparingly — bypasses CloudWatch evaluation).
- Prevent recurrence: add a secondary "alarm stuck in ALARM > 24h"
  composite alarm that fires when `StateUpdatedTimestamp` is too old.

## Worked example — diagnose stuck alarm (BLOCKED)

```text
OPERATION: diagnose
VERDICT: BLOCKED
TARGET: api-error-rate-prod
PRE_CHECKS:
  - [PASS] describe-alarms returns the alarm
  - [FAIL] Metric not publishing: get-metric-statistics on
    AWS/ApplicationELB, HTTPCode_ELB_5XX_Count, dimensions
    LoadBalancer=app/prod-alb/WRONG-NAME returns 0 datapoints over the
    last 1 hour. The LoadBalancer dimension value appears to reference
    a deleted ALB.
  - [PASS] describe-alarm-history shows the alarm entered
    INSUFFICIENT_DATA 6 days ago and has not transitioned since
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: INSUFFICIENT_DATA (stuck 6 days)
NOTES:
  - The alarm has been in INSUFFICIENT_DATA for 6 days because the
    LoadBalancer dimension references a deleted ALB. Update the
    dimension value to the current ALB ARN:
    aws cloudwatch put-metric-alarm --alarm-name api-error-rate-prod \
      --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
      [...rest of the existing config...]
  - Verify the new ALB is publishing via:
    aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
      --metric-name HTTPCode_ELB_5XX_Count \
      --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
      --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
      --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
      --period 60 --statistics Sum
  - Snapshot before update:
    aws cloudwatch describe-alarms --alarm-names api-error-rate-prod \
      --output json > /tmp/api-error-rate-prod-backup-$(date +%s).json
```
