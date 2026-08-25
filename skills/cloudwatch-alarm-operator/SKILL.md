---
name: cloudwatch-alarm-operator
description: Operates CloudWatch alarm lifecycles safely — creates static-threshold, metric-math, anomaly-detection, and composite alarms; tunes threshold / period / DatapointsToAlarm / TreatMissingData; wires alarm actions (SNS, Auto Scaling, EC2 recover/stop/reboot, Lambda via SNS, Systems Manager via SNS); reduces alarm fatigue via composite rollups and anomaly bands; and diagnoses alarms stuck in INSUFFICIENT_DATA or failing to fire. Runs deterministic pre-checks (metric namespace, dimensions, statistic, SNS topic existence, actions-enabled flag), emits the exact put-metric-alarm / put-composite-alarm CLI behind a CONFIRM gate, and verifies state transitions post-apply. Emits a verdict (READY | BLOCKED | COMPLETED) per operation. Use when creating CPU/memory/disk/error-rate/latency/SQS-depth/Lambda-throttle alarms, building composite alarms to reduce alarm fatigue, converting static thresholds to anomaly detection, diagnosing alarms stuck in INSUFFICIENT_DATA, or tuning alarm sensitivity.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws cloudwatch put-metric-alarm, put-composite-alarm, describe-alarms, describe-alarm-history, get-metric-statistics, put-anomaly-detector, enable-alarm-actions, disable-alarm-actions (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Creating or tuning CloudWatch alarms (CPU, memory, disk, error rate, latency, SQS depth, Lambda errors/throttles), wiring alarm actions (SNS, Auto Scaling, EC2 recover, Lambda, SSM), building composite alarms to reduce alarm fatigue, converting static thresholds to anomaly detection, diagnosing alarms stuck in INSUFFICIENT_DATA or not firing, or auditing alarm state transitions.
  activation_triggers: create CloudWatch alarm, tune CloudWatch alarm, alarm stuck in INSUFFICIENT_DATA, alarm not triggering, composite alarm, reduce alarm fatigue, anomaly detection alarm, metric math alarm, request error rate alarm, CPU threshold alarm, memory alarm CloudWatch agent, Lambda throttle alarm, SQS queue depth alarm, EC2 recover alarm action, alarm actions SNS
  invocation_schema: 'Input: either (a) an alarm operation intent (create, tune, diagnose, composite-rollup) with target namespace/metric/dimensions/threshold, OR (b) an alarm name for live-account tuning or diagnosis. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch, alarms, put-metric-alarm, put-composite-alarm, anomaly detection, metric math, alarm actions, SNS, Auto Scaling, EC2 recover, alarm fatigue, composite alarms, INSUFFICIENT_DATA, TreatMissingData, threshold tuning, DatapointsToAlarm, EvaluationPeriods, request-error-rate, CPUUtilization, Lambda throttles, SQS queue depth
  tags: cloudwatch, monitoring, alarms, observability, operate, anomaly-detection, composite-alarms
---

# CloudWatch Alarm Operator

## What this skill does

Executes CloudWatch alarm lifecycle operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI, emits the
exact `put-metric-alarm` / `put-composite-alarm` sequence behind a
CONFIRM gate, and verifies state transitions after apply. Every alarm
operation surfaces TreatMissingData and M-of-N detection lag.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority + detection lag | Before any operation |
| **§ Mindset** | Pre-checks, M-of-N lag, INSUFFICIENT_DATA trap | Understanding the safety model |
| **§ Pre-flight** | Alarm/metric metadata gate | Before executing any CLI |
| **§ Process** | Per-operation planning: create, tune, composite, anomaly, diagnose | When choosing which operation |
| **§ Common patterns** | CPU/memory/disk/error-rate/latency/SQS/Lambda boilerplate | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (missing metric namespace, wrong dimensions, SNS topic missing, ActionsEnabled false, period mismatch) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Alarm applied and post-verification passed (state transition confirmed, action wiring verified, describe-alarms matches expected config) | Emit describe-alarms summary, state, action wiring |

**Priority order for pre-checks (all must pass for READY):**

1. **Metric namespace + dimensions** — namespace exists, metric publishing, dimensions match native structure.
2. **Period / resolution alignment** — Period >= metric native interval (60s detailed, 300s basic).
3. **DatapointsToAlarm / EvaluationPeriods sanity** — DatapointsToAlarm <= EvaluationPeriods.
4. **Threshold / ComparisonOperator feasibility** — threshold achievable for the metric's range.
5. **Action targets** — every ARN exists, same region, <= 5 per category.
6. **TreatMissingData intent** — explicit choice (not default "missing").
7. **Composite Rule integrity** — every child alarm in Rule exists; Rule <= 512 chars.

**Detection lag baselines (2026):**
- Static threshold (Period=60, DatapointsToAlarm=1): ~60-120s.
- Static threshold (Period=300, DatapointsToAlarm=2 of 3): ~10-15 min.
- Composite: evaluates every 60s (fixed) on top of child latency.
- Anomaly detection: ~15 min warm-up before bands are valid.

## Mindset

Three CloudWatch realities drive every alarm operation:

- **M-of-N introduces multi-period lag.** `DatapointsToAlarm=3, EvaluationPeriods=5, Period=300` cannot fire until 3 breaching windows complete — at least 15 minutes from first breach. For critical alarms (availability, security), prefer `DatapointsToAlarm=1, EvaluationPeriods=1` and accept more noise.
- **INSUFFICIENT_DATA is silent.** Default TreatMissingData "missing" enters INSUFFICIENT_DATA when no datapoints arrive and triggers `InsufficientDataActions` (almost always empty), NOT `AlarmActions`. The alarm goes dark without anyone noticing.
- **PutMetricAlarm overwrites atomically.** Alarm names are unique within account+region, but `put-metric-alarm` does NOT error on duplicates — it replaces the entire config with no version history and no rollback. Only CloudTrail reveals the change.

## Pre-flight: alarm/metric metadata gate

Run before classification. `describe-alarms` returns max 100/page
(`--max-records 100`, use `--starting-token` to paginate).
`get-metric-statistics` returns max 1440 datapoints/call.

**Live-account pre-flight (skip if offline plan):**
1. `describe-alarms --alarm-names <name>` — confirm alarm exists. Capture `ActionsEnabled`, `StateValue`, action lists, `TreatMissingData`.
2. `get-metric-statistics` — confirm metric is publishing, observe typical range.
3. `describe-anomaly-detectors --namespace <ns>` — check for existing detector.
4. `sns get-topic-attributes --topic-arn <arn>` — verify each action target.
5. `describe-alarm-history --history-type StateHistory` — surface recent transitions; flapping (>5/hour) needs recalibration.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `ActionsEnabled: false` | Tune applies but notifications suppressed. Re-enable via `enable-alarm-actions`. |
| `StateValue: INSUFFICIENT_DATA` | Active blind spot. Tune must set `TreatMissingData` explicitly. |
| `StateValue: ALARM` (stuck >24h) | Threshold too low or OK action missing. Surface as finding. |
| `TreatMissingData` unset | Defaults to "missing" — alarm goes dark on gaps. |
| `DatapointsToAlarm > EvaluationPeriods` | Permanently non-functional. Tune must fix. |
| Period < metric native interval | Most windows empty. Tune must align Period. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious CloudWatch alarm behaviors

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — "Step 0: Expert knowledge" holds all 14 non-obvious behaviors (TreatMissingData default, INSUFFICIENT_DATA actions, M-of-N, ActionsEnabled kill switch, PutMetricAlarm overwrite, composite Rule limits/AND-OR, action dedup, anomaly warm-up, MetricMath FILL, 5-action cap, Period/resolution, high-res cost, cross-account AccountId, ANOMALY_DETECTION_BAND shape).
Load that reference before planning edge-case operations — each behavior changes a pre-check or verdict.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with failures in
PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Namespace and metric name spelled correctly (case-sensitive).
2. Dimensions match metric's native structure (wrong = no datapoints = INSUFFICIENT_DATA).
3. Metric currently publishing (get-metric-statistics returns datapoints within last 2 periods).
4. IAM role holds `cloudwatch:PutMetricAlarm` / `PutCompositeAlarm` / `EnableAlarmActions`.

**For create/tune metric alarm:**
5. `Period` >= metric native interval (300 basic, 60 detailed).
6. `DatapointsToAlarm <= EvaluationPeriods`.
7. `Threshold` achievable per observed range.
8. `Statistic` matches semantics (Sum for counts, Average for utilization, SampleCount for volume).
9. Every action ARN exists and is in-region. <= 5 ARNs per category.
10. `TreatMissingData` set explicitly.

**For composite alarm:**
5. Every `ALARM(name)` / `OK(name)` reference resolves to existing alarm.
6. Rule <= 512 chars, <= 100 distinct references.
7. AlarmActions includes at least one ESCALATION target (different SNS than children).

**For anomaly detection conversion:**
5. Metric has >= 15 min history (warm-up).
6. Existing detector surfaced (don't duplicate).
7. Stdev 2 (moderate) or 3 (conservative); stdev <= 1 flagged as over-sensitive.

**For diagnose operations:**
5. `describe-alarms` returns valid config.
6. `describe-alarm-history --history-type StateHistory` for last 72h fetched.
7. `get-metric-statistics` over same window confirms whether metric actually breached.

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected detection lag (Period * DatapointsToAlarm for first ALARM transition).
- Expected side-effects (SNS, AutoScaling, EC2 recover, Lambda).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI (`put-metric-alarm`, `put-composite-alarm`, `delete-alarms`, `disable-alarm-actions`, `enable-alarm-actions`), emit CONFIRM prompt. Do NOT execute until confirmed.
- Snapshot current config: `describe-alarms --alarm-names <name> --output json > /tmp/<name>-backup-$(date +%s).json`.
- Execute the CLI.
- For composite alarms, validate Rule by reading back via `describe-alarms` after apply (CloudWatch accepts invalid syntax at put time but evaluates only at next cycle).

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. `describe-alarms` returns expected config.
2. New alarm: StateValue is `INSUFFICIENT_DATA` initially or `OK` after first cycle — NOT `ALARM` unless metric already breaching.
3. Tune: new threshold/period/TreatMissingData reflected.
4. Action wiring: `ActionsEnabled: true`, ARNs populated, SNS has subscriptions.
5. Synthetic test (optional): publish breaching datapoint, verify ALARM transition + SNS delivery, clean up.
6. Composite: trigger one child, verify Rule evaluates correctly.

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common alarm patterns (boilerplate)

### CPU utilization threshold (EC2, 80% for 5 min)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-cpu-high-prod-web-1" \
  --alarm-description "CPU > 80% for 5 min on prod-web-1. Runbook: https://runbooks.example.com/high-cpu" \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Average --period 300 --evaluation-periods 1 --datapoints-to-alarm 1 \
  --threshold 80 --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical \
  --ok-actions arn:aws:sns:us-east-1:111111111111:on-call-info --unit Percent
```

### Memory threshold (requires CloudWatch agent)

Memory metrics are NOT published by default — the CWAgent must be
installed. Namespace is `CWAgent`. Dimensions include `ImageId`,
`InstanceId`, and sometimes `ObjectType` — verify via
`get-metric-statistics` first.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-memory-high-prod-web-1" \
  --namespace CWAgent --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 Name=ImageId,Value=ami-0abcdef1234567890 \
  --statistic Average --period 300 --evaluation-periods 2 --datapoints-to-alarm 2 \
  --threshold 90 --comparison-operator GreaterThanThreshold \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

### Request error rate (metric math: errors / requests)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "alb-error-ratio-prod" \
  --namespace AWS/ApplicationELB \
  --alarm-description "ALB 5xx / total > 1%. Runbook: https://runbooks.example.com/5xx" \
  --metrics \
    "m1,HTTPCode_ELB_5XX_Count,Sum,60,LoadBalancer,app/prod-alb/1234567890" \
    "m2,RequestCount,Sum,60,LoadBalancer,app/prod-alb/1234567890" \
    "e1,EXPRESSION(m1/m2),60" \
  --comparison-operator GreaterThanThreshold --threshold 0.01 \
  --evaluation-periods 3 --datapoints-to-alarm 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

### Latency (ALB TargetResponseTime, anomaly detection)

Two-step: create detector, wait 15 min, then alarm on band.

```bash
aws cloudwatch put-anomaly-detector \
  --namespace AWS/ApplicationELB --metric-name TargetResponseTime --stat Average \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890

# Wait 15 min for band to populate, then:
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

`GreaterThanUpperThreshold` triggers when value exceeds band upper edge.
Stdev 2 = moderate; 3 = conservative.

### SQS queue depth

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "sqs-depth-high-prod-orders" \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders \
  --statistic Average --period 300 --evaluation-periods 2 --datapoints-to-alarm 2 \
  --threshold 10000 --comparison-operator GreaterThanThreshold \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-warning
```

### Lambda errors and throttles

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-errors-high-prod-checkout" \
  --namespace AWS/Lambda --metric-name Errors \
  --dimensions Name=FunctionName,Value=prod-checkout \
  --statistic Sum --period 60 --evaluation-periods 5 --datapoints-to-alarm 3 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical

aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-throttles-high-prod-checkout" \
  --namespace AWS/Lambda --metric-name Throttles \
  --dimensions Name=FunctionName,Value=prod-checkout \
  --statistic Sum --period 60 --evaluation-periods 1 --datapoints-to-alarm 1 \
  --threshold 0 --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

### Composite alarm (reduce alarm fatigue)

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "prod-checkout-critical-rollup" \
  --alarm-description "Composite: any of {5xx, latency, lambda errors} firing. Escalation tier." \
  --actions-enabled \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-escalation \
  --alarm-rule "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)" \
  --treat-missing-data notBreaching
```

### EC2 recover (auto-remediation)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-status-check-recover-prod-web-1" \
  --namespace AWS/EC2 --metric-name StatusCheckFailed_System \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Maximum --period 60 --evaluation-periods 2 --datapoints-to-alarm 2 \
  --threshold 0 --comparison-operator GreaterThanThreshold \
  --treat-missing-data ignore \
  --alarm-actions arn:aws:automate:us-east-1:ec2:recover
```

The `arn:aws:automate:<region>:ec2:recover` action triggers in-place
recovery (healthy hardware, retains private IP, public IP, EBS volumes).

## Diagnostic flows

### Alarm stuck in INSUFFICIENT_DATA

1. `describe-alarms` — capture Namespace, MetricName, Dimensions, Period.
2. `get-metric-statistics` over last hour with same Period + Statistic.
3. If no datapoints: metric not publishing. Likely causes:
   - Wrong namespace (case-sensitive — `AWS/EC2` not `aws/ec2`).
   - Wrong dimension name or value (case-sensitive).
   - Resource stopped/terminated.
   - CWAgent not running or configured with different dimension set.
4. If datapoints exist: Period misalignment or EvaluationPeriods window hasn't accumulated enough data yet.
5. Remediation: fix namespace/dimensions, or set `--treat-missing-data breaching` so the alarm fires when the metric goes missing.

### Alarm not triggering despite apparent breach

1. `describe-alarms` — capture Threshold, ComparisonOperator, Statistic, Period, EvaluationPeriods, DatapointsToAlarm.
2. `get-metric-statistics` over same window and Period — verify the statistic actually crossed the threshold.
3. Common mismatches:
   - Operator expects `Sum` but alarm uses `Average` (or vice versa).
   - Operator looking at 1-min graph but alarm uses Period=300 (5-min average masks spikes).
   - M-of-N not satisfied (breach hasn't persisted long enough).
   - `ActionsEnabled: false` — alarm transitions to ALARM but suppresses notifications.
4. Remediation: align Statistic/Period with operator's mental model; reduce DatapointsToAlarm for faster response.

### Alarm stuck in ALARM (no OK action)

1. Metric returned to normal but alarm stays in ALARM — verify via `get-metric-statistics`.
2. If StateValue is still ALARM, metric has not actually returned to normal.
3. If StateValue is OK but no notification: OKActions is empty — add an OK action.
4. For slow-draining metrics (queue depth), consider `INSUFFICIENT_DATA -> OK` via TreatMissingData.

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

### Worked example — diagnose stuck alarm (BLOCKED)

Secondary example moved verbatim to [references/worked-examples.md](references/worked-examples.md) — full BLOCKED output block: metric not publishing (deleted-ALB dimension value), INSUFFICIENT_DATA stuck 6 days, snapshot-before-update note.
The primary worked example (create CPU alarm, READY) stays below; more worked examples live in [references/alarm-patterns-and-diagnosis.md](references/alarm-patterns-and-diagnosis.md).

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

- NEVER start with conversational preamble ("Let me analyze…") — the VERDICT block is the FIRST line, always. Use uppercase verdict values only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or `[FAIL]` and a specific reason for each failure.
- NEVER emit TreatMissingData as "missing" (the default) — always choose `breaching`, `notBreaching`, or `ignore` with rationale in NOTES.
- NEVER list a CLI command with placeholder flags in a READY plan — every flag must be populated with actual values from the input data.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`, and never omit the CONFIRM gate as the first STEPS entry for state-changing operations.

## Anti-Patterns — NEVER do these things

- NEVER leave TreatMissingData as default "missing" for production alarms. Set explicit `--treat-missing-data breaching|notBreaching|ignore` based on metric semantics. The default causes INSUFFICIENT_DATA on gaps — a silent blind spot.
- NEVER set DatapointsToAlarm > EvaluationPeriods. The condition is mathematically impossible to satisfy. CloudWatch accepts without validation error.
- NEVER confuse AlarmActions with InsufficientDataActions. For availability metrics, configure BOTH — InsufficientDataActions catches the "monitoring broken" case.
- NEVER PutMetricAlarm without a CONFIRM gate and config snapshot. It silently overwrites with no version history, no diff, and no rollback.
- NEVER create a static-threshold alarm on a high-variance metric (traffic, latency, error rate) without sampling first. Use anomaly detection for metrics with seasonality.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before modification:** `describe-alarms --alarm-names <name> --output json > /tmp/<name>-backup-$(date +%s).json`.
- **Verify action ARNs exist** and are in-region — non-existent ARNs fail silently at fire time.
- **Prefer additive changes** (add InsufficientDataActions, add OK action) over destructive (delete alarm, remove action).
- **Anomaly conversion = two steps:** (1) create detector + wait 15 min, (2) update alarm to use band.

## Expert heuristic: INSUFFICIENT_DATA vs ALARM

INSUFFICIENT_DATA does NOT mean "value is zero" or "healthy." It means
**the metric is not being reported at all** — monitoring is broken.

```
INSUFFICIENT_DATA
   ├─ Is the metric published at all?
   │    ├─ NO → Sensor failure (most common)
   │    │         • EC2: instance running? CloudWatch agent installed?
   │    │         • Lambda: function being invoked?
   │    │         • Custom metric: PUT-metric-data call succeeding?
   │    │         • RDS: instance in AVAILABLE state?
   │    └─ YES → Check alarm config
   │              • Namespace case-sensitive? (AWS/EC2 vs aws/ec2)
   │              • Dimension name/value case-sensitive?
   │              • Period < native publishing interval?
   │              • EvaluationPeriods window has not accumulated enough data?
```

**Per-service root causes:**

| Service / metric | What to check |
|---|---|
| `AWS/EC2 CPUUtilization` | Instance running? Detailed monitoring enabled (60s) vs basic (300s)? Period matches? |
| `CWAgent mem_used_percent` | Agent running? `ImageId` and `ObjectType` dimensions match agent config? |
| `AWS/Lambda Errors/Throttles` | Function being invoked? Name spelled correctly? |
| `AWS/SQS ApproximateNumberOfMessagesVisible` | Queue name correct? Same region? |
| `AWS/ApplicationELB HTTPCode_ELB_5XX_Count` | ALB exists? `LoadBalancer` dimension matches current ARN? |
| Custom namespace | `put-metric-data` succeeding (check CloudTrail)? Namespace case-sensitive? |

**TreatMissingData fix:**
- `breaching` — availability/heartbeat metrics where missing data IS the alert.
- `notBreaching` — utilization metrics where missing = resource gone.
- `ignore` — metrics where gaps are expected periodically.

ALWAYS pair with an `InsufficientDataActions` SNS target.

**Stuck in ALARM after metric stops:** with `breaching` (common for security
alarms), an alarm that fired legitimately then lost its metric source stays
in ALARM forever — no OK datapoint can clear the breach. Fix: if resource is
gone, `delete-alarms`; if sensor broken, fix sensor; to force-clear, use
`set-alarm-state` sparingly.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — "Recent AWS features (2024-2026)": Metric Explorer, Contributor Insights, Application Signals/SLOs, OTel metrics, composite improvements, Metric Streams, built-in anomaly detection.
Load when operating on 2024-2026 surfaces or choosing detection strategy.

## References (load on demand)

- [references/alarm-patterns-and-diagnosis.md](references/alarm-patterns-and-diagnosis.md) — full static/anomaly/composite creation procedures, action wiring matrix, TreatMissingData decision guide, M-of-N tuning, cost reference, INSUFFICIENT_DATA diagnostic procedure, edge cases.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked example: diagnose stuck alarm (BLOCKED) with full PRE_CHECKS/STEPS/POST_VERIFY output.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive (14 non-obvious alarm behaviors) and recent AWS features (2024-2026).

## Domain

AWS CloudOps / CloudWatch Alarm Lifecycle & Observability Operations.

## AWS documentation

- **Amazon CloudWatch User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- **CloudWatch Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- **Using Composite Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html
- **Anomaly Detection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html
- **Metric Math** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html
- **CloudWatch API Reference** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/
- **AWS CLI CloudWatch reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/
- **CloudWatch Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html
