---
description: Operate CloudWatch alarm lifecycles — create, tune, diagnose, and compose alarms with pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "create CloudWatch alarm"
  - "tune CloudWatch alarm"
  - "diagnose CloudWatch alarm"
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
routes_to: cloudwatch-alarm-operator
---

# /aws:operate-cloudwatch-alarm

Activate the `cloudwatch-alarm-operator` skill and plan/execute a
CloudWatch alarm operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads an alarm configuration plus the intended operation and applies
the priority-ordered pre-check sequence:

1. Pre-flight alarm/metric metadata gate — short-circuit cases where
   the metric is not publishing or ActionsEnabled is false.
2. Pre-check gate — BLOCKED if any check fails (wrong namespace,
   wrong dimensions, DatapointsToAlarm > EvaluationPeriods, SNS topic
   missing, > 5 ARNs per category, default TreatMissingData).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected detection lag (Period * DatapointsToAlarm), the expected
   side-effects (SNS delivery, AutoScaling policy execution, EC2
   recover), and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — snapshot describe-alarms first
   (PutMetricAlarm overwrites with no version history), execute the
   CLI, wait for the first evaluation cycle.
5. Post-verification — describe-alarms matches expected config,
   StateValue transitions correctly, action wiring verified.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

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

## When to invoke

Paste an alarm configuration plus the intended operation, or just
describe the scenario and ask any of:

- "create a CPU alarm on prod-web-1"
- "tune the latency alarm to anomaly detection"
- "build a composite to roll up these 3 alarms"
- "why is api-error-rate-prod stuck in INSUFFICIENT_DATA"
- "set up EC2 recover on status check failure"

A bare alarm name + any operation verb ("fix this alarm", "make it
less noisy") also routes here via the orchestrator.

## Inputs

- Target alarm name (existing or new).
- Namespace + MetricName + Dimensions (case-sensitive).
- Statistic, Period, EvaluationPeriods, DatapointsToAlarm.
- Threshold + ComparisonOperator (or ANOMALY_DETECTION_BAND stdev).
- AlarmActions / OKActions / InsufficientDataActions ARN lists (max 5
  per category).
- TreatMissingData choice (breaching | notBreaching | ignore | missing).
- For composite: Rule expression (boolean over child alarm names),
  AlarmActions escalation target.
- For diagnose: alarm name + describe-alarms output (optional:
  describe-alarm-history, get-metric-statistics).

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected detection lag, expected
  side-effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new
  alarm StateValue, and any follow-up tuning recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., fix the LoadBalancer dimension, set TreatMissingData
  explicitly, re-enable alarm-actions).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for CloudWatch alarm lifecycle).
- `/aws:audit-cloudwatch-alarm` for the audit/classification side —
  the auditor finds mis-configured alarms; this operator creates,
  tunes, and diagnoses them.
- `/aws:audit-cloudwatch-logs-retention` for the related logs-retention
  audit.
