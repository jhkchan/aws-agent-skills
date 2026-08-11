---
description: Diagnose CloudWatch alarm issues through a nine-category (dimension mismatch, namespace typo, period misalignment, statistic mismatch, threshold, composite rule, math expression, action target policy, treat-missing-data) diagnostic tree — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "CloudWatch alarm INSUFFICIENT_DATA"
  - "alarm stuck in INSUFFICIENT_DATA"
  - "CloudWatch alarm not firing"
  - "alarm never goes to ALARM"
  - "CloudWatch dimension mismatch"
  - "alarm dimension case-sensitive"
  - "CloudWatch alarm period misaligned"
  - "high-resolution alarm"
  - "CloudWatch composite alarm"
  - "alarm math expression error"
  - "CloudWatch alarm action not triggering"
  - "SNS topic alarm action"
  - "Lambda alarm action permission"
  - "CloudWatch alarm statistic"
  - "treat-missing-data"
  - "troubleshoot CloudWatch alarm"
  - "diagnose CloudWatch alarm"
  - "alarm fires but no notification"
routes_to: cloudwatch-alarm-troubleshooter
---

# /aws:troubleshoot-cloudwatch-alarm

Activate the `cloudwatch-alarm-troubleshooter` skill and diagnose an
AWS CloudWatch alarm issue through the nine-category diagnostic tree.

## What it does

Reads a symptom description (alarm name, observed state —
INSUFFICIENT_DATA / OK-but-expected-ALARM / ALARM-with-no-action)
plus the alarm configuration, then walks the symptom-driven
diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — alarm state and history
   (`describe-alarms`, `describe-alarm-history`), raw metric points
   (`get-metric-data` with the alarm's exact query), metric-filter
   config, anomaly-detector config. Short-circuits on alarm-state
   patterns (INSUFFICIENT_DATA since creation = metric query issue;
   ALARM with no Action entries = action target policy issue).
2. **Symptom entry** — map the symptom to one of: metric query
   mismatch (dimension / namespace / period), threshold / statistic
   divergence from the dashboard, action target policy failure,
   composite rule evaluation, math expression error, anomaly band
   miscalibration, treat-missing-data masking.
3. **Layer-specific probes** —
   - Metric mismatch: `describe-alarms` (Namespace, MetricName,
     Dimensions, Period), `get-metric-data` with the alarm's exact
     query and with a dimensionless control, `list-metrics` to
     discover the actual emitted dimension values.
   - Threshold / statistic: `describe-alarms` (Threshold,
     ComparisonOperator, Statistic, Period, EvaluationPeriods,
     DatapointsToAlarm) vs the dashboard query; high-resolution vs
     standard-resolution period alignment.
   - Action target: `describe-alarms` (AlarmActions),
     `describe-alarm-history --history-type Action`, SNS topic policy
     (`get-topic-attributes`), Lambda resource-based policy
     (`get-policy`), ASG scaling policy
     (`autoscaling describe-policies`).
   - Composite: `describe-alarms` (AlarmRule), child alarm
     `StateValue`; INSUFFICIENT_DATA propagation under AND / OR.
   - Math expression: `describe-alarms` (Metrics, Expression),
     `get-metric-data` with the same expression; divide-by-zero,
     missing-Id, SEARCH rejection.
   - Anomaly: `describe-alarms` (ThresholdMetricId),
     `describe-anomaly-detectors`; training window, band width.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom) or INSUFFICIENT_DATA (alarm-side config is
   clean; issue is upstream in the metric pipeline).

Emits a deterministic diagnostic block per target:

```text
TARGET: <alarm-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <METRIC_DIMENSION_MISMATCH | NAMESPACE_TYPO | PERIOD_MISALIGNMENT |
        RESOLUTION_MISMATCH | STATISTIC_MISMATCH | THRESHOLD_STATIC |
        THRESHOLD_ANOMALY | MATH_EXPRESSION | COMPOSITE_RULE |
        TREAT_MISSING_DATA | INSUFFICIENT_DATA_CONFIG |
        ACTION_SNS_POLICY | ACTION_LAMBDA_POLICY |
        ACTION_AUTOSCALING_POLICY | ACTION_SSM_POLICY |
        ACTION_MISSING | UNKNOWN>
EVIDENCE:
  - <observed symptom — StateValue or operator report>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "CloudWatch alarm stuck in INSUFFICIENT_DATA"
- "alarm never goes to ALARM"
- "dimension mismatch CloudWatch alarm"
- "alarm period misaligned with metric"
- "composite alarm never fires"
- "alarm math expression error"
- "alarm fires but no notification"
- "SNS topic alarm action permission"
- "treat-missing-data configuration"

A bare alarm name + any state verb ("alarm is broken", "alarm not
firing", "alarm INSUFFICIENT") also routes here via the orchestrator.

## Inputs

- Symptom description: alarm name, observed StateValue, how long it
  has been in that state, what the dashboard shows.
- Alarm configuration: Namespace, MetricName, Dimensions, Period,
  Statistic, Threshold, ComparisonOperator, EvaluationPeriods,
  DatapointsToAlarm, TreatMissingData, AlarmActions, Metrics (for
  math / composite).
- For live-account diagnosis: `describe-alarms` output,
  `get-metric-data` output with the alarm's exact query,
  `describe-alarm-history` output, action target policies (SNS topic
  policy, Lambda resource-based policy).

## Outputs

- One diagnostic block per target alarm.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: dimension / namespace / period / statistic
  correction, threshold adjustment, composite rule rewrite, math
  expression restructure, anomaly detector re-training,
  treat-missing-data change, SNS / Lambda / ASG action target policy
  fix, or routing to `cloudwatch-metrics-troubleshooter` for the
  metric pipeline.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for CloudWatch alarm issues).
- `/aws:audit-cloudwatch-alarm` for configuration posture audits on
  the same alarm (coverage gaps, action target policy review).
- `/aws:troubleshoot-cloudwatch-metrics` for deeper diagnosis when the
  underlying metric pipeline (application, CloudWatch Agent,
  put-metric-data) is not emitting points.
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  SNS topic or Lambda function policy is denied by an SCP or
  permissions boundary.
