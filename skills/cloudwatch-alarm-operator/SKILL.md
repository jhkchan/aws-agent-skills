---
name: cloudwatch-alarm-operator
description: >-
  Operates CloudWatch alarm lifecycles safely — creates static-threshold,
  metric-math, anomaly-detection, and composite alarms; tunes threshold /
  period / DatapointsToAlarm / TreatMissingData; wires alarm actions
  (SNS, Auto Scaling, EC2 recover/stop/reboot, Lambda via SNS, Systems
  Manager via SNS); reduces alarm fatigue via composite rollups and
  anomaly bands; and diagnoses alarms stuck in INSUFFICIENT_DATA or
  failing to fire. Runs deterministic pre-checks (metric namespace,
  dimensions, statistic, SNS topic existence, actions-enabled flag),
  emits the exact put-metric-alarm / put-composite-alarm CLI behind a
  CONFIRM gate, and verifies state transitions post-apply. Emits a
  verdict (READY | BLOCKED | COMPLETED) per operation. Use when creating
  CPU/memory/disk/error-rate/latency/SQS-depth/Lambda-throttle alarms,
  building composite alarms to reduce alarm fatigue, converting static
  thresholds to anomaly detection, diagnosing alarms stuck in
  INSUFFICIENT_DATA, or tuning alarm sensitivity.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws cloudwatch put-metric-alarm, put-composite-alarm,
  describe-alarms, describe-alarm-history, get-metric-statistics,
  put-anomaly-detector, enable-alarm-actions, disable-alarm-actions
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CloudWatch
  - alarms
  - put-metric-alarm
  - put-composite-alarm
  - anomaly detection
  - metric math
  - alarm actions
  - SNS
  - Auto Scaling
  - EC2 recover
  - alarm fatigue
  - composite alarms
  - INSUFFICIENT_DATA
  - TreatMissingData
  - threshold tuning
  - DatapointsToAlarm
  - EvaluationPeriods
  - request-error-rate
  - CPUUtilization
  - Lambda throttles
  - SQS queue depth
tags: [cloudwatch, monitoring, alarms, observability, operate, anomaly-detection, composite-alarms]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Creating or tuning CloudWatch alarms (CPU, memory, disk, error rate,
    latency, SQS depth, Lambda errors/throttles), wiring alarm actions
    (SNS, Auto Scaling, EC2 recover, Lambda, SSM), building composite
    alarms to reduce alarm fatigue, converting static thresholds to
    anomaly detection, diagnosing alarms stuck in INSUFFICIENT_DATA or
    not firing, or auditing alarm state transitions.
  activation_triggers:
    - "create CloudWatch alarm"
    - "tune CloudWatch alarm"
    - "alarm stuck in INSUFFICIENT_DATA"
    - "alarm not triggering"
    - "composite alarm"
    - "reduce alarm fatigue"
    - "anomaly detection alarm"
    - "metric math alarm"
    - "request error rate alarm"
    - "CPU threshold alarm"
    - "memory alarm CloudWatch agent"
    - "Lambda throttle alarm"
    - "SQS queue depth alarm"
    - "EC2 recover alarm action"
    - "alarm actions SNS"
  invocation_schema: >-
    Input: either (a) an alarm operation intent (create, tune, diagnose,
    composite-rollup) with target namespace/metric/dimensions/threshold,
    OR (b) an alarm name for live-account tuning or diagnosis. Output:
    deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block
    per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.
---

# CloudWatch Alarm Operator

## What this skill does

Executes CloudWatch alarm lifecycle operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI (does the
namespace exist? are dimensions correct? does the SNS topic exist? is
ActionsEnabled on?), emits the exact `put-metric-alarm` /
`put-composite-alarm` sequence behind a CONFIRM gate, and verifies
state transitions after apply. Every alarm operation surfaces the
TreatMissingData choice (the most common silent blind spot) and the
M-of-N detection lag.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority order + common alarm patterns | Before any operation |
| **§ Mindset** | Why pre-checks matter, the M-of-N lag, INSUFFICIENT_DATA trap | Understanding the safety model |
| **§ Pre-flight** | Alarm/metric metadata gate — namespace, dimensions, statistic | Before executing any CLI |
| **§ Process** | Per-operation planning: create, tune, composite, anomaly, diagnose | When choosing which operation |
| **§ Common patterns** | CPU/memory/disk/error-rate/latency/SQS/Lambda boilerplate | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that cause silent alarm failures | Review before risky operations |
| **§ Pre-flight safety** | Additional checks before any remediation CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (missing metric namespace, wrong dimensions, SNS topic missing, ActionsEnabled false on existing alarm, period mismatch) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Alarm applied and post-verification passed (state transition confirmed, action wiring verified, describe-alarms matches expected config) | Emit describe-alarms summary, state, action wiring |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Metric namespace + dimensions** — the namespace exists, the metric
   is publishing, and dimensions match the metric's native structure.
2. **Period / resolution alignment** — Period >= metric's native publishing
   interval (60s detailed, 300s basic).
3. **DatapointsToAlarm / EvaluationPeriods sanity** — DatapointsToAlarm <=
   EvaluationPeriods (otherwise permanently non-functional).
4. **Threshold / ComparisonOperator feasibility** — the threshold must be
   achievable for the metric's range.
5. **Action targets** — every ARN in AlarmActions / OKActions /
   InsufficientDataActions exists, is in the same region, and is under
   the 5-ARN-per-category cap.
6. **TreatMissingData intent** — explicit choice (not the default
   "missing") for the metric's missing-data semantics.
7. **Composite Rule integrity** — for composite alarms, every child
   alarm referenced in Rule exists; Rule <= 512 chars.

**Detection lag baselines (2026):**

- Static-threshold alarm (Period=60, DatapointsToAlarm=1): ~60-120s.
- Static-threshold alarm (Period=300, DatapointsToAlarm=2 of 3): ~10-15 min.
- Composite alarm: evaluates every 60s (fixed) on top of child latency.
- Anomaly detection: ~15 min warm-up before bands are valid.

## Mindset

**One-line takeaway:** an alarm has one job — detect a condition and
notify someone (or trigger auto-remediation). When any link breaks, the
alarm becomes a false sense of security. Driven by three CloudWatch
realities:

- **M-of-N introduces multi-period lag.** `DatapointsToAlarm=3,
  EvaluationPeriods=5, Period=300` cannot fire until 3 breaching windows
  complete — at least 15 minutes from the first breach. Operators
  expecting 1-minute latency are surprised. For critical alarms
  (availability, security), prefer `DatapointsToAlarm=1,
  EvaluationPeriods=1` and accept more noise.
- **INSUFFICIENT_DATA is silent.** The default TreatMissingData is
  "missing" — the alarm enters INSUFFICIENT_DATA when no datapoints
  arrive and triggers `InsufficientDataActions` (almost always empty),
  NOT `AlarmActions`. The alarm goes dark without anyone noticing.
- **PutMetricAlarm overwrites atomically.** Alarm names are unique
  within account+region, but `put-metric-alarm` does NOT error on
  duplicate names — it replaces the entire configuration with no
  version history and no rollback path. The only audit trail is
  CloudTrail.

## Pre-flight: alarm/metric metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-alarms` returns at most 100 per page
(`--max-records 100`). Use `--starting-token` (AWS CLI v2 pagination
syntax) to drain to completion. `get-metric-statistics` returns up to
1440 datapoints per call; for long windows, partition by day.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudwatch describe-alarms --alarm-names <name>` — confirm the
   alarm exists (or doesn't, for create ops). Capture `ActionsEnabled`,
   `StateValue`, `AlarmActions`, `OKActions`, `InsufficientDataActions`,
   `TreatMissingData`.
2. `aws cloudwatch get-metric-statistics --namespace <ns> --metric-name
   <mn> --dimensions <dims> --start-time <iso> --end-time <iso> --period
   <p> --statistics <stat>` — confirm the metric is publishing and
   observe the typical range.
3. `aws cloudwatch describe-anomaly-detectors --namespace <ns>` — for
   anomaly-detection conversions, verify whether a detector already
   exists on the metric.
4. `aws sns get-topic-attributes --topic-arn <arn>` — verify each
   action target exists.
5. `aws cloudwatch describe-alarm-history --alarm-name <name>
   --history-type StateHistory --start-date <iso> --end-date <iso>` —
   surface recent state transitions; a flapping alarm (>5 transitions
   per hour) needs threshold recalibration.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Alarm/metric configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws cloudwatch describe-alarms --alarm-names
<name> --output json and re-plan.`

| Attribute | Effect on operation |
|---|---|
| `ActionsEnabled: false` on existing alarm | Tune/update still applies but notifications remain suppressed. Surface as a finding: re-enable via `enable-alarm-actions`. |
| `StateValue: INSUFFICIENT_DATA` (existing alarm) | Active blind spot. Tune operation must set `TreatMissingData` explicitly. |
| `StateValue: ALARM` (existing alarm, stuck >24h) | Threshold too low or OK action missing. Surface as a finding. |
| `TreatMissingData` unset (existing alarm) | Defaults to "missing" — alarm goes to INSUFFICIENT_DATA on gaps. Tune must set explicit value. |
| `DatapointsToAlarm > EvaluationPeriods` (existing alarm) | Permanently non-functional. Tune must fix. |
| Period < metric native publishing interval | Most windows empty. Tune must align Period. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious CloudWatch alarm behaviors

These behaviors are easy to misjudge without operational CloudWatch
experience. Each changes a plan if ignored:

- **TreatMissingData defaults to "missing" — NOT "notBreaching".** If
  unset, the alarm enters INSUFFICIENT_DATA when no datapoints arrive.
  This is the single most common alarm blind spot: operators assume
  missing data means "no problem" but the alarm actually goes dark.

- **INSUFFICIENT_DATA triggers InsufficientDataActions, NOT
  AlarmActions.** If InsufficientDataActions is empty (the common
  case), the transition is silent. This is why an alarm that enters
  INSUFFICIENT_DATA is a monitoring black hole.

- **DatapointsToAlarm must be <= EvaluationPeriods.** This is the M-of-N
  pattern: `DatapointsToAlarm=2, EvaluationPeriods=5` means the alarm
  fires when 2 of the last 5 windows are breaching. If DatapointsToAlarm
  exceeds EvaluationPeriods, the condition can **never** be satisfied.
  CloudWatch accepts this config without validation error.

- **ActionsEnabled: false is a global kill switch.** Even if
  AlarmActions lists five SNS topics, a Lambda function, and three
  AutoScaling policies, setting ActionsEnabled to false suppresses ALL
  of them. Often set during testing and forgotten.

- **PutMetricAlarm silently overwrites existing alarms.** No version
  history, no diff, no rollback. A deployment that recreates an alarm
  with different settings has no audit trail in the alarm config itself.
  Only CloudTrail `PutMetricAlarm` events reveal the change.

- **Composite alarm Rule expression is limited to 512 characters** and
  can reference up to 100 other alarms. A Rule near the 512-char limit
  is fragile — a minor logic change can exceed the limit and fail
  silently on update.

- **AnomalyDetection requires ~15 minutes of metric history** before
  producing valid bands. A newly created anomaly detector on a metric
  with no history returns empty bands — the alarm will not fire until
  enough data accumulates. Do NOT classify a new anomaly-detection
  alarm as broken during this warm-up window.

- **MetricMath FILL() can mask missing data.** `FILL(m1, 0)` replaces
  missing datapoints with 0 — prevents INSUFFICIENT_DATA but can cause
  false negatives (error-count metric filled with 0 looks healthy when
  the metric simply stopped reporting). Pair FILL() with a secondary
  "heartbeat" alarm that detects the metric going missing.

- **Alarm actions are capped at 5 per category.** AlarmActions,
  OKActions, InsufficientDataActions each accept a maximum of 5 ARNs.
  The 6th is silently rejected.

- **Period must be >= the metric's native resolution.** A metric
  published every 5 minutes evaluated with Period=60 produces mostly
  empty windows. AWS services natively publish at 1 minute (detailed)
  or 5 minutes (basic monitoring).

- **High-resolution alarms (10s or 30s Period) cost more.** Standard
  alarms evaluate at 60-second resolution at no extra charge.
  High-resolution alarms incur a higher per-alarm monthly cost. Reserve
  for critical metrics (payment fraud, security anomalies).

- **Composite alarms evaluate every 60 seconds, fixed.** Regardless of
  any child alarm Period. The composite resolves `ALARM(name)` /
  `OK(name)` references to each child's current StateValue, then
  applies boolean operators.

- **Composite short-circuit hazard.** `ALARM(child-a) AND
  ALARM(child-b)` requires BOTH children to be in ALARM simultaneously.
  If child-a fires and clears before child-b fires, the composite never
  enters ALARM. Use OR for escalation; use AND carefully with time-
  window awareness via child EvaluationPeriods.

- **Alarm actions ordering and deduplication.** Actions execute in the
  order listed but are NOT deduplicated. The same SNS topic in both a
  child alarm and the composite alarm delivers two notifications for
  the same event. Design composite actions as escalation (different
  SNS topic, different on-call tier).

- **PutMetricAlarm for an ANOMALY_DETECTION_BAND expression.** The
  `Metrics` array member uses `Expression: ANOMALY_DETECTION_BAND(m1,
  stdev)` and the alarm `ComparisonOperator` becomes
  `GreaterThanUpperThreshold` / `LessThanLowerThreshold` against the
  band edges, not against a static Threshold.

- **Cross-account/cross-region metric alarms use the AccountId field
  inside the Metrics array member**, not the Dimensions array. An
  alarm with the wrong AccountId silently monitors the wrong account.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
BLOCKED with the failed checks enumerated in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. The namespace and metric name are spelled correctly (case-sensitive).
2. The dimensions match the metric's native structure (wrong dimensions
   = no datapoints = INSUFFICIENT_DATA).
3. The metric is currently publishing (`get-metric-statistics` returns
   non-empty datapoints within the last 2 periods).
4. The IAM role for the operator holds `cloudwatch:PutMetricAlarm` /
   `PutCompositeAlarm` / `EnableAlarmActions` as appropriate.

**For create/tune metric alarm (`put-metric-alarm`):**
5. `Period` >= metric native publishing interval (300 for basic, 60 for
   detailed).
6. `DatapointsToAlarm <= EvaluationPeriods`.
7. `Threshold` is achievable for the metric's observed range (use
   `get-metric-statistics` to sample).
8. `Statistic` matches the metric's semantics (use `Sum` for counts,
   `Average` for utilization, `SampleCount` for volume).
9. Every `AlarmActions` / `OKActions` / `InsufficientDataActions` ARN
   exists (sns:get-topic-attributes, lambda:get-function, autoscaling
   describe-policies) and is in the same region.
10. <= 5 ARNs per action category.
11. `TreatMissingData` is set explicitly (not left as default "missing").

**For composite alarm (`put-composite-alarm`):**
5. Every `ALARM(name)` / `OK(name)` reference in Rule resolves to an
   existing alarm in the account+region.
6. Rule length <= 512 characters.
7. <= 100 distinct alarm references in Rule.
8. AlarmActions for the composite includes at least one ESCALATION
   target (different SNS topic than child alarms) — otherwise the
   composite adds no notification value.

**For anomaly detection conversion:**
5. The metric has >= 15 minutes of history (warm-up requirement). If
   not, the plan notes the warm-up window and schedules a re-check.
6. An existing anomaly detector on the same metric/dimensions is
   surfaced (don't duplicate detectors).
7. Standard deviation is 2 (moderate) or 3 (conservative) by default;
   stdev <= 1 is flagged as over-sensitive.

**For diagnose operations (alarm stuck / not firing):**
5. `describe-alarms` for the alarm name returns a valid config.
6. `describe-alarm-history --history-type StateHistory` for the last
   72 hours is fetched to surface transition patterns.
7. `get-metric-statistics` over the same window confirms whether the
   metric actually breached the configured threshold (rule out
   "operator thinks it should fire but the metric never crossed").

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the alarm
  specification.
- The expected detection lag (Period * DatapointsToAlarm seconds for
  the first ALARM transition).
- The expected side-effects (SNS notification delivered, AutoScaling
  policy executed, EC2 recover triggered, Lambda invoked).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`put-metric-alarm`, `put-composite-alarm`, `delete-alarms`,
  `disable-alarm-actions`, `enable-alarm-actions`), emit:
  `CONFIRM: About to <operation> on alarm <name> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.
- Snapshot the current alarm config before modification:
  `aws cloudwatch describe-alarms --alarm-names <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`. PutMetricAlarm overwrites with
  no version history.
- Execute the CLI.
- For composite alarms, validate the Rule expression by reading the
  alarm back via `describe-alarms` after apply (CloudWatch accepts
  invalid Rule syntax at PutMetricAlarm time but evaluates only at the
  next cycle).

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must
pass for `COMPLETED`.

1. `describe-alarms --alarm-names <name>` returns the expected
   configuration (threshold, period, TreatMissingData, actions).
2. For a new alarm: `StateValue` is `INSUFFICIENT_DATA` initially (no
   data yet evaluated) or `OK` after the first evaluation cycle. It is
   NOT `ALARM` unless the metric is already breaching.
3. For a tune on an existing alarm: the new threshold / period /
   TreatMissingData is reflected in `describe-alarms`.
4. For action wiring: `ActionsEnabled: true` and the action ARNs are
   populated. Verify the SNS topic has subscriptions
   (`sns list-subscriptions-by-topic`).
5. Trigger a synthetic test (optional): publish a test datapoint via
   `aws cloudwatch put-metric-data` that breaches the threshold, wait
   for the evaluation cycle, verify the alarm transitions to ALARM and
   the SNS notification is delivered. Clean up the test datapoint.
6. For composite alarms: trigger one child alarm via synthetic datapoint
   and verify the composite Rule evaluates correctly.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## Common alarm patterns (boilerplate)

### CPU utilization threshold (EC2, 80% for 5 min)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-cpu-high-prod-web-1" \
  --alarm-description "CPU > 80% for 5 min on prod-web-1. Runbook: https://runbooks.example.com/high-cpu" \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --datapoints-to-alarm 1 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical \
  --ok-actions arn:aws:sns:us-east-1:111111111111:on-call-info \
  --unit Percent
```

### Memory threshold (requires CloudWatch agent)

Memory metrics are NOT published by default — the CloudWatch agent
must be installed on the EC2 instance. Namespace is `CWAgent`.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-memory-high-prod-web-1" \
  --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 Name=ImageId,Value=ami-0abcdef1234567890 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

Note: the CWAgent dimensions include `ImageId`, `InstanceId`, and
sometimes `objecttype`. Verify the exact dimensions via
`get-metric-statistics` first — a wrong dimension set produces no
datapoints.

### Disk space utilization

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-disk-high-prod-web-1-root" \
  --namespace CWAgent \
  --metric-name disk_used_percent \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 Name=path,Value=/ Name=fstype,Value=xfs \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --datapoints-to-alarm 1 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-warning
```

### Request error rate (metric math: errors / requests)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "alb-5xx-error-rate-prod" \
  --alarm-description "ALB 5xx rate > 1% for 5 min. Runbook: https://runbooks.example.com/5xx" \
  --namespace AWS/ApplicationELB \
  --metric-name 5xx \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 5 \
  --datapoints-to-alarm 3 \
  --threshold 0.01 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

For a true ratio (errors / total), use metric math with the `--metrics`
flag instead:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "alb-error-ratio-prod" \
  --namespace AWS/ApplicationELB \
  --alarm-description "ALB 5xx / total > 1%. Runbook: https://runbooks.example.com/5xx" \
  --metrics \
    "m1,HTTPCode_ELB_5XX_Count,Sum,60,LoadBalancer,app/prod-alb/1234567890" \
    "m2,RequestCount,Sum,60,LoadBalancer,app/prod-alb/1234567890" \
    "e1,EXPRESSION(m1/m2),60" \
  --comparison-operator GreaterThanThreshold \
  --threshold 0.01 \
  --evaluation-periods 3 \
  --datapoints-to-alarm 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

### Latency (ALB TargetResponseTime, anomaly detection)

```bash
# 1. Create the anomaly detector first
aws cloudwatch put-anomaly-detector \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --stat Average \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
  --configuration '{"MetricMathConfig":{"AnomalyDetectorConfiguration":{"Expression":"e1","Period":60,"Stat":"Average"}}}' \
  --profile default

# 2. Wait 15 min for the band to populate

# 3. Create the alarm against the band
aws cloudwatch put-metric-alarm \
  --alarm-name "alb-latency-anomaly-prod" \
  --namespace AWS/ApplicationELB \
  --metrics \
    "m1,TargetResponseTime,Average,60,LoadBalancer,app/prod-alb/1234567890" \
    "ad1,ANOMALY_DETECTION_BAND(m1,2),60" \
  --comparison-operator GreaterThanUpperThreshold \
  --evaluation-periods 3 \
  --datapoints-to-alarm 2 \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

Note: `GreaterThanUpperThreshold` triggers when the observed value
exceeds the band's upper edge. Standard deviation 2 = moderate
sensitivity; 3 = conservative.

### SQS queue depth (ApproximateNumberOfMessagesVisible)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "sqs-depth-high-prod-orders" \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --threshold 10000 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-warning
```

### Lambda errors and throttles

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-errors-high-prod-checkout" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=prod-checkout \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 5 \
  --datapoints-to-alarm 3 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical

aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-throttles-high-prod-checkout" \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=prod-checkout \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --datapoints-to-alarm 1 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

### Composite alarm (reduce alarm fatigue)

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "prod-checkout-critical-rollup" \
  --alarm-description "Composite: any 2 of {5xx, latency, lambda errors} firing. Escalation tier." \
  --actions-enabled \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-escalation \
  --alarm-rule "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)" \
  --treat-missing-data notBreaching
```

### EC2 recover (auto-remediation)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-status-check-recover-prod-web-1" \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed_System \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data ignore \
  --alarm-actions arn:aws:automate:us-east-1:ec2:recover
```

The `arn:aws:automate:<region>:ec2:recover` action triggers an in-place
recovery (the instance is migrated to healthy hardware, retains its
private IP, public IP, and EBS volumes).

## Diagnostic flows

### Alarm stuck in INSUFFICIENT_DATA

1. `describe-alarms --alarm-names <name>` — capture Namespace,
   MetricName, Dimensions, Period.
2. `get-metric-statistics --namespace <ns> --metric-name <mn>
   --dimensions <dims> --start-time <now-1h> --end-time <now> --period
   <period> --statistics <stat>`.
3. If no datapoints: the metric is not publishing. Likely causes:
   - Wrong namespace (case-sensitive — `AWS/EC2` not `aws/ec2`).
   - Wrong dimension name or value (case-sensitive).
   - The resource (instance, function, queue) is stopped/terminated.
   - The CWAgent is not running or is configured with a different
     dimension set (verify via the agent's config file).
4. If datapoints exist but alarm is still INSUFFICIENT_DATA: Period
   misalignment (Period < native resolution) or EvaluationPeriods
   window hasn't accumulated enough datapoints yet.
5. Remediation: fix the namespace/dimensions, or set
   `--treat-missing-data breaching` so the alarm fires when the metric
   goes missing (rather than going dark).

### Alarm not triggering despite apparent breach

1. `describe-alarms --alarm-names <name>` — capture Threshold,
   ComparisonOperator, Statistic, Period, EvaluationPeriods,
   DatapointsToAlarm.
2. `get-metric-statistics` over the same window and Period — verify the
   statistic value actually crossed the threshold.
3. Common mismatches:
   - Operator expects `Sum` but alarm uses `Average` (or vice versa).
   - Operator is looking at a 1-min graph but the alarm uses Period=300
     (the 5-min average masks 1-min spikes).
   - `DatapointsToAlarm=3, EvaluationPeriods=5` — the breach hasn't
     persisted long enough to satisfy M-of-N.
   - `ActionsEnabled: false` — the alarm transitions to ALARM state but
     suppresses notifications (easy to verify in `describe-alarms`
     `StateValue` — if it's `ALARM` but no one was paged, this is it).
4. Remediation: align the alarm Statistic/Period with the operator's
   mental model; reduce DatapointsToAlarm for faster (noisier) response.

### Alarm stuck in ALARM (no OK action configured)

1. The metric has returned to normal but the alarm stays in ALARM state.
2. Check: OKActions is empty — clearing notifications are not delivered,
   but the StateValue should still transition to OK. If StateValue is
   still ALARM, the metric has not actually returned to normal — verify
   via `get-metric-statistics`.
3. If StateValue is OK but no notification fired: OKActions is empty.
   Add an OK action if clearing notifications are desired.
4. If the underlying issue is resolved but the metric is slow to clear
   (e.g., a queue depth draining slowly), consider an
   `INSUFFICIENT_DATA → OK` transition via TreatMissingData.

## Output format (per operation)

```text
OPERATION: <create | tune | composite | anomaly | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <alarm-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <OK | ALARM | INSUFFICIENT_DATA after apply>
NOTES: <TreatMissingData choice rationale, detection lag, action wiring caveats>
```

### Worked example — create CPU alarm (READY)

```text
OPERATION: create
VERDICT: READY
TARGET: ec2-cpu-high-prod-web-1
PRE_CHECKS:
  - [PASS] Namespace AWS/EC2, MetricName CPUUtilization valid
  - [PASS] Dimensions InstanceId=i-0123456789abcdef0 returns datapoints
    (Average ~45% over last 1h)
  - [PASS] Period 300 >= metric native 60s (detailed monitoring)
  - [PASS] DatapointsToAlarm 1 <= EvaluationPeriods 1
  - [PASS] Threshold 80 achievable (current Average ~45%, max ~72%)
  - [PASS] Statistic Average matches utilization semantics
  - [PASS] AlarmActions SNS arn:aws:sns:us-east-1:111111111111:on-call-critical
    exists and has subscriptions
  - [PASS] 1 ARN <= 5 cap per category
  - [PASS] TreatMissingData notBreaching explicit (CPU gap = instance
    likely stopped = not a CPU problem)
STEPS:
  1. CONFIRM: About to put-metric-alarm ec2-cpu-high-prod-web-1 in
     account 111111111111 region us-east-1. This will CREATE a new
     alarm that fires SNS on-call-critical when CPU > 80% for 5 min.
     Estimated detection lag: ~5-10 min from first breach. Proceed?
     (yes/no)
  2. aws cloudwatch put-metric-alarm --alarm-name ec2-cpu-high-prod-web-1 \
       --namespace AWS/EC2 --metric-name CPUUtilization \
       --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
       --statistic Average --period 300 --evaluation-periods 1 \
       --threshold 80 --comparison-operator GreaterThanThreshold \
       --treat-missing-data notBreaching \
       --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical \
       --ok-actions arn:aws:sns:us-east-1:111111111111:on-call-info
POST_VERIFY:
  - (pending execution)
  - describe-alarms returns the alarm with StateValue INSUFFICIENT_DATA
    (initial) transitioning to OK after the first evaluation cycle
STATE: (pending — will be INSUFFICIENT_DATA for the first ~5 min)
NOTES:
  - Detection lag: Period(300) * DatapointsToAlarm(1) = 5 min from
    first breach to ALARM transition.
  - TreatMissingData notBreaching: if the instance stops and CPU
    metrics stop, the alarm stays in OK (correct — stopped instance
    is not a CPU problem).
  - The alarm has no InsufficientDataActions — if you want to be
    alerted when the metric goes missing entirely, add an
    InsufficientDataActions SNS target.
```

### Worked example — diagnose stuck alarm (BLOCKED)

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

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
OPERATION: <create | tune | composite | anomaly | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <alarm-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on alarm <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <OK | ALARM | INSUFFICIENT_DATA | pending>
NOTES: <TreatMissingData rationale — must state breaching|notBreaching|ignore and why; detection lag; action wiring caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY`, `BLOCKED`, or
  `COMPLETED` (not `ready`, `blocked`, `completed`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]` or
  `[FAIL]` and a specific reason for each failure. An empty PRE_CHECKS block
  is non-compliant.
- NEVER emit TreatMissingData as "missing" (the default) — always choose
  `breaching`, `notBreaching`, or `ignore` and state the rationale in NOTES.
  "missing" is a silent-blind-spot anti-pattern, not a valid choice.
- NEVER list a CLI command with placeholder flags (e.g., `--dimensions
  <dims>`) in a READY plan — every flag must be populated with actual values
  from the input data.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation (create, tune, composite, anomaly).
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`.
- NEVER diagnose an INSUFFICIENT_DATA alarm without quoting the
  `get-metric-statistics` result that proves whether the metric is
  publishing — the evidence must include the datapoint count or range.

### Perfect example output

```text
OPERATION: create
VERDICT: READY
TARGET: ec2-cpu-high-prod-web-1
PRE_CHECKS:
  - [PASS] Namespace AWS/EC2, MetricName CPUUtilization valid
  - [PASS] Dimensions InstanceId=i-0123456789abcdef0 returns datapoints (Average ~45% over last 1h)
  - [PASS] Period 300 >= metric native 60s (detailed monitoring)
  - [PASS] DatapointsToAlarm 1 <= EvaluationPeriods 1
  - [PASS] Threshold 80 achievable (current Average ~45%, max ~72%)
  - [PASS] AlarmActions SNS arn:aws:sns:us-east-1:111111111111:on-call-critical exists and has subscriptions
  - [PASS] 1 ARN <= 5 cap per category
  - [PASS] TreatMissingData notBreaching explicit (CPU gap = instance likely stopped = not a CPU problem)
STEPS:
  1. CONFIRM: About to put-metric-alarm ec2-cpu-high-prod-web-1 in account 111111111111 region us-east-1. This will CREATE a new alarm that fires SNS on-call-critical when CPU > 80% for 5 min. Estimated detection lag: ~5 min. Proceed? (yes/no)
  2. aws cloudwatch put-metric-alarm --alarm-name ec2-cpu-high-prod-web-1 --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=i-0123456789abcdef0 --statistic Average --period 300 --evaluation-periods 1 --datapoints-to-alarm 1 --threshold 80 --comparison-operator GreaterThanThreshold --treat-missing-data notBreaching --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical --ok-actions arn:aws:sns:us-east-1:111111111111:on-call-info
POST_VERIFY:
  - (pending execution)
  - describe-alarms returns the alarm with StateValue INSUFFICIENT_DATA (initial) transitioning to OK after first evaluation cycle
STATE: pending — will be INSUFFICIENT_DATA for the first ~5 min
NOTES:
  - Detection lag: Period(300) x DatapointsToAlarm(1) = 5 min from first breach to ALARM transition.
  - TreatMissingData notBreaching: if the instance stops and CPU metrics stop, the alarm stays in OK (correct — stopped instance is not a CPU problem).
```

## Anti-Patterns — NEVER do these things

- NEVER leave TreatMissingData as the default "missing" for production
  alarms. The default behavior is INSUFFICIENT_DATA on gaps, which
  triggers InsufficientDataActions (almost always empty) instead of
  AlarmActions. The alarm goes dark silently. Set explicit
  `--treat-missing-data breaching|notBreaching|ignore` based on metric
  semantics.

- NEVER set DatapointsToAlarm > EvaluationPeriods. The condition is
  mathematically impossible to satisfy — the alarm is permanently
  non-functional regardless of metric data. CloudWatch accepts this
  config without validation error.

- NEVER confuse AlarmActions with InsufficientDataActions. An alarm
  entering INSUFFICIENT_DATA fires ONLY InsufficientDataActions. If
  that list is empty, the transition is silent. For availability
  metrics, configure BOTH AlarmActions (breach) and
  InsufficientDataActions (missing data alert).

- NEVER assume `ActionsEnabled: true` on an existing alarm. Always
  check — a flag set to false during testing and forgotten suppresses
  ALL actions (SNS, Lambda, AutoScaling, EC2 recover). The alarm
  transitions to ALARM state but nobody is notified.

- NEVER create a static-threshold alarm on a high-variance metric
  (traffic, latency, error rate) without first sampling the metric
  range via `get-metric-statistics`. A threshold picked without data
  either floods on-call with false positives or misses real anomalies.
  Prefer anomaly detection for high-variance metrics.

- NEVER recommend anomaly detection for binary metrics
  (StatusCheckFailed), countdown metrics (certificate expiry), or
  metrics with well-understood capacity limits (disk utilization).
  Anomaly detection adds value for metrics with seasonality, trend
  drift, or unpredictable variance only.

- NEVER create a composite alarm with empty AlarmActions and assume it
  "rolls up" child notifications. Composite alarms do NOT auto-aggregate
  child alarm actions — each alarm notifies independently. The composite
  should have at least one escalation action distinct from child alarm
  actions.

- NEVER PutMetricAlarm without a CONFIRM gate. PutMetricAlarm silently
  overwrites the existing alarm config with no version history, no diff,
  and no rollback. Always snapshot via `describe-alarms --output json`
  first.

- NEVER add more than 5 ARNs to a single action category. The 6th ARN
  is silently dropped. For fan-out, use one SNS topic with multiple
  subscriptions instead.

- NEVER trust a freshly-created anomaly-detection alarm to fire
  immediately. AnomalyDetection requires ~15 minutes of metric history
  before producing valid bands. During warm-up, the alarm evaluates
  against empty bands and may behave unpredictably.

- NEVER use Period < metric native publishing interval. A 5-minute
  metric evaluated with Period=60 produces 4 empty windows out of 5,
  causing frequent INSUFFICIENT_DATA.

- NEVER use MetricMath `FILL(m1, 0)` on error/failure metrics without a
  secondary heartbeat alarm. FILL(0) prevents INSUFFICIENT_DATA but
  masks sensor failures (the metric stops reporting and looks healthy
  at 0).

- NEVER auto-execute a state-changing CloudWatch CLI without the
  CONFIRM gate. PutMetricAlarm, PutCompositeAlarm, DeleteAlarms,
  DisableAlarmActions, and EnableAlarmActions all have side effects
  (overwrite configs, suppress notifications, delete alarm history).
  Always emit CONFIRM and wait.

- NEVER delete an alarm to "stop noise" without first understanding why
  it is firing. DeleteAlarms is irreversible. The correct first step is
  `disable-alarm-actions` (reversible) while investigating.

- NEVER create a high-resolution alarm (Period=10 or 30) for low-
  urgency metrics. High-resolution alarms incur a higher per-alarm
  monthly cost. Reserve for critical metrics where 60s latency is
  unacceptable (payment fraud, security anomalies).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-metric-alarm`, `put-composite-alarm`, `delete-alarms`,
  `disable-alarm-actions`, `enable-alarm-actions`), the operator MUST
  emit: `CONFIRM: About to <action> on alarm <name> in account <account>
  region <region>. This affects <consequence>. Proceed? (yes/no)`. Do
  NOT execute the CLI command until the operator confirms.

- **PutMetricAlarm overwrites the entire alarm configuration.** Always
  snapshot before modification:
  `aws cloudwatch describe-alarms --alarm-names <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`.

- When adding actions, verify the SNS topic / Lambda function /
  AutoScaling policy ARN exists and is in the same region. A non-
  existent ARN in AlarmActions causes the action to fail silently at
  fire time.

- When changing TreatMissingData on an existing alarm, consider the
  impact on currently-breaching alarms. Changing from "missing" to
  "notBreaching" while the alarm is in INSUFFICIENT_DATA will
  immediately transition it to OK — potentially clearing an important
  state.

- For composite alarm Rule changes, validate the expression syntax
  before applying. CloudWatch accepts the Rule at PutMetricAlarm time
  but evaluates it only at the next evaluation cycle — a syntax error
  produces no immediate error.

- When converting a static-threshold alarm to anomaly detection,
  schedule the operation in two steps: (1) create the anomaly detector
  and wait 15 min for warm-up, (2) update the alarm to use the band.
  Doing both in one step risks a window where the alarm has no valid
  threshold.

- Prefer additive changes (add an InsufficientDataActions target, add
  an OK action) over destructive changes (delete an alarm, remove an
  action) — additive changes are reversible and do not risk breaking
  existing on-call workflows.

## Recent AWS features (2024-2026)

- **CloudWatch Metric Explorer (2024-2025):** cross-account, cross-
  region metric exploration without pre-configuring alarms. Use to
  find the right metric / dimension set before creating an alarm.
- **Contributor Insights (2024-2025):** top-N contributors to a metric
  (e.g., top source IPs driving 5xx errors). Pair with alarms on
  abnormal contributor patterns.
- **CloudWatch Application Signals (2024-2025):** auto-discovered SLOs
  and Service Level Objectives from CloudWatch Agent on EC2/ECS/EKS.
  Alarms can be created on SLO burn rate instead of raw metrics —
  operationally cleaner for service-level monitoring.
- **OpenTelemetry native metrics (2024):** CloudWatch ingests OTel-
  format metrics natively. Alarms on OTel metrics may have different
  namespace and dimension structures — verify mappings.
- **Composite alarm improvements (2024):** more complex boolean
  expressions and cross-region references. Cascading composite
  dependencies can create blind spots if a component is deleted —
  surface as a finding.
- **CloudWatch metric streams (2024-2025):** stream metrics to S3 /
  third-party (Datadog, New Relic) in real-time. Complementary to
  alarms — useful for long-term retention and third-party alerting.
- **Built-in anomaly detection on AWS services (2025):** some AWS
  service consoles (RDS Performance Insights, Application Signals)
  ship with pre-built anomaly detection — reduces the need to
  hand-tune stdev.

## Domain

AWS CloudOps / CloudWatch Alarm Lifecycle & Observability Operations.

## Expert heuristic: INSUFFICIENT_DATA vs ALARM

INSUFFICIENT_DATA does NOT mean "the value is zero" or "the metric is
healthy." It means **the metric is not being reported at all** — the
alarm has no data to evaluate. Operators routinely misread
INSUFFICIENT_DATA as "everything is fine" when it actually means
"monitoring is broken."

**Diagnostic decision tree:**

```
INSUFFICIENT_DATA
   ├─ Is the metric published at all?
   │    ├─ NO → Sensor failure (most common)
   │    │         • EC2: is the instance running? is the CloudWatch agent installed?
   │    │         • Lambda: is the function being invoked?
   │    │         • Custom metric: is the PUT-metric-data call succeeding?
   │    │         • RDS: is the instance in AVAILABLE state (not stopped)?
   │    │
   │    └─ YES → Check alarm config
   │              • Namespace case-sensitive? (AWS/EC2 vs aws/ec2)
   │              • Dimension name/value case-sensitive?
   │              • Period < native publishing interval?
   │              • EvaluationPeriods window has not accumulated enough data yet?
```

**Per-service INSUFFICIENT_DATA root causes:**

| Service / metric | What to check when INSUFFICIENT_DATA appears |
|---|---|
| `AWS/EC2 CPUUtilization` | Instance running? Detailed monitoring enabled (60s) vs basic (300s)? Period matches? |
| `CWAgent mem_used_percent` | CloudWatch agent running on the instance? `ImageId` and `ObjectType` dimensions match agent config? |
| `AWS/Lambda Errors/Throttles` | Function being invoked at all? Function name spelled correctly? |
| `AWS/SQS ApproximateNumberOfMessagesVisible` | Queue name correct? Queue in the same region? |
| `AWS/ApplicationELB HTTPCode_ELB_5XX_Count` | ALB exists? `LoadBalancer` dimension value matches current ALB ARN (not a deleted one)? |
| Custom namespace | `put-metric-data` calls succeeding (check CloudTrail)? Namespace spelled correctly (case-sensitive)? |

**Fix — set TreatMissingData based on metric semantics:**
- `breaching` — for availability / heartbeat metrics where missing
  data IS the alert (e.g., a "metric stopped reporting" alarm).
- `notBreaching` — for utilization metrics where missing data means
  the resource is gone (e.g., CPU on a stopped instance).
- `ignore` — for metrics where missing data is expected periodically
  (e.g., queue depth outside business hours).

ALWAYS pair the TreatMissingData choice with an
`InsufficientDataActions` SNS target so the monitoring black hole
itself triggers an alert.

## Edge case: alarm stuck in ALARM after the metric stops reporting

When a metric was breaching and then STOPS reporting entirely (sensor
failure, instance terminated, agent crashed mid-incident), the alarm's
behavior depends on TreatMissingData — and the wrong choice leaves the
alarm in ALARM state indefinitely:

| TreatMissingData | Behavior when metric stops mid-breach |
|---|---|
| `missing` (default) | Transitions to INSUFFICIENT_DATA after the next evaluation cycle — `InsufficientDataActions` fires (usually empty = silent) |
| `breaching` | Stays in ALARM forever — the missing data is treated as continuing to breach |
| `notBreaching` | Transitions to OK after the next cycle — `OKActions` fires (if configured) |
| `ignore` | Stays in ALARM forever — the alarm holds its last evaluated state |

**The "stuck in ALARM forever" trap:** with `TreatMissingData: breaching`
(common for security / availability alarms), an alarm that fired
legitimately and then lost its metric source stays in ALARM even after
the underlying issue is resolved and the resource is terminated.
On-call receives no "all clear" because:
1. The metric is gone, so no OK datapoint can ever clear the breach.
2. `OKActions` only fires on a real OK transition, not on alarm
   deletion.

**Diagnostic:**
1. `describe-alarms --alarm-names <name>` — confirm `StateValue: ALARM`
   and `StateUpdatedTimestamp` is old (>24h).
2. `get-metric-statistics` over the last hour — if empty, the metric
   stopped.
3. Check the resource: is the EC2 instance terminated? Is the Lambda
   function deleted? Is the ALB gone?

**Fix:**
- If the resource is gone: `delete-alarms` — the alarm is monitoring
  nothing.
- If the resource exists but the agent/sensor is broken: fix the
  sensor, the alarm will self-clear on the next OK datapoint.
- To force-clear without waiting: snapshot the config, then
  `set-alarm-state --state-value OK --state-reason "manual override
  after sensor recovery"` (use sparingly — this bypasses CloudWatch's
  evaluation).
- Prevent recurrence: add a secondary "alarm stuck in ALARM > 24h"
  composite alarm that fires when `StateUpdatedTimestamp` is too old.

## AWS documentation

- **Amazon CloudWatch User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- **CloudWatch Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- **Using Composite Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html
- **Anomaly Detection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html
- **Metric Math** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html
- **CloudWatch API Reference** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/
- **AWS CLI CloudWatch reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/
- **CloudWatch Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html
