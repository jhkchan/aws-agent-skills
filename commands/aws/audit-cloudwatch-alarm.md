---
description: Audit a CloudWatch alarm configuration for blind spots — missing alarm actions (SNS/Lambda/AutoScaling), insufficient-data handling, anomaly-detection coverage vs static thresholds, composite alarm integrity, and structural config errors.
nl_triggers:
  - "audit this CloudWatch alarm"
  - "check my alarm actions"
  - "is this alarm configured correctly"
  - "alarm has no SNS topic"
  - "insufficient data handling"
  - "should I use anomaly detection"
  - "composite alarm audit"
  - "missing metric alarm"
  - "alarm blind spot"
  - "TreatMissingData"
  - "alarm fires but nobody notified"
  - "DatapointsToAlarm"
  - "alarm never fires"
  - "ActionsEnabled false"
  - "hardening CloudWatch alarms"
routes_to: cloudwatch-alarm-auditor
---

# /aws:audit-cloudwatch-alarm

Activate the `cloudwatch-alarm-auditor` skill and audit one or more CloudWatch
alarm configurations for operational blind spots.

## What it does

Reads a CloudWatch alarm configuration (MetricAlarm or CompositeAlarm) and
applies the ordered classification logic:

1. CONFIG_GAP — structural errors (DatapointsToAlarm > EvaluationPeriods,
   impossible thresholds, unknown composite Rule references, Period/resolution
   mismatch).
2. NO_ACTION — missing notification wiring (empty AlarmActions,
   ActionsEnabled: false, composite alarm with no escalation actions).
3. INSUFFICIENT_DATA — missing-data blind spots (TreatMissingData defaults to
   "missing", no InsufficientDataActions, alarm stuck in INSUFFICIENT_DATA
   state).
4. NO_ANOMALY — suboptimal detection strategy (static threshold on high-
   variance metric, anomaly band with stdev <= 1).
5. OK — all dimensions pass.

Emits a deterministic VERDICT per alarm:

```text
ALARM: <alarm-name>
VERDICT: NO_ANOMALY | NO_ACTION | INSUFFICIENT_DATA | CONFIG_GAP | OK
REASON: <1-2 sentences citing the specific config gap and step number>
FINDINGS:
  - [<SEVERITY>] <finding description (Step Na)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CloudWatch alarm configuration and ask any of:

- "audit this CloudWatch alarm"
- "check my alarm actions"
- "is this alarm configured correctly?"
- "why does my alarm never fire?"
- "should I use anomaly detection?"
- "is my alarm handling missing data?"
- "audit this composite alarm"

An alarm name + any audit verb ("audit this alarm", "check alarm config") also
routes here via the orchestrator.

## Inputs

- A CloudWatch alarm configuration (JSON or text representation), pasted inline
  or referenced by file path.
- Alarm type: MetricAlarm (Namespace, MetricName, Dimensions, Period,
  EvaluationPeriods, DatapointsToAlarm, ComparisonOperator, Threshold,
  TreatMissingData, ActionsEnabled, AlarmActions, OKActions,
  InsufficientDataActions) or CompositeAlarm (Rule expression + action lists).
- For anomaly-detection alarms: the Metrics array with ANOMALY_DETECTION_BAND
  expression.
- For live-account audit: alarm name for `aws cloudwatch describe-alarms` +
  `describe-alarm-history`.

## Outputs

- One VERDICT block per alarm (first matching condition in ordered
  classification).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: add SNS/Lambda actions, set TreatMissingData, adopt
  AnomalyDetection, fix structural config errors.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CloudWatch alarm reliability).
- `/aws:audit-cloudtrail-org-trail` for auditing the CloudTrail trail that
  captures alarm state-change events for forensics.
