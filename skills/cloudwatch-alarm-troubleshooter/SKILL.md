---
name: cloudwatch-alarm-troubleshooter
description: >-
  Diagnoses CloudWatch alarm issues through a nine-category diagnostic
  tree: alarm stuck in INSUFFICIENT_DATA (missing metric, missing
  dimension, period misaligned), alarm not firing (static threshold
  vs anomaly detection band, statistic mismatch Sum/Average/Maximum),
  high-resolution vs standard-resolution period mismatch, metric
  namespace typo or wrong source, composite alarm rule evaluation
  failure, math expression errors, dimension case-sensitivity and
  exact-string matching, alarm actions not triggering (SNS topic
  policy, Lambda invoke permission, missing action), alarm history
  analysis for state transitions, and treat-missing-data
  configuration. Walks symptoms to a verified root cause with
  evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or
  INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted alarm state and metric configuration. Live-account diagnosis uses aws cloudwatch describe-alarms, get-metric-data, get-metric-statistics, describe-alarm-history, aws logs describe-metric-filters, aws sns get-topic-attributes, aws lambda get-policy, and aws cloudwatch put-metric-data for a test point (AWS CLI v2,
  SSO or key-based credentials).
keywords:
- CloudWatch
- alarm
- INSUFFICIENT_DATA
- alarm not firing
- metric dimension
- period alignment
- anomaly detection
- composite alarm
- math expression
- alarm actions
- treat-missing-data
- troubleshooting
tags:
- cloudwatch
- management
- troubleshooting
- alarm
- INSUFFICIENT_DATA
- anomaly-detection
- composite-alarm
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a CloudWatch alarm that does not behave as expected — stuck in INSUFFICIENT_DATA, never transitions to ALARM, fires inconsistently with the metric, alarm actions (SNS, Lambda, Auto Scaling, SSM) do not invoke, composite alarm rule evaluates incorrectly, math-expression alarm errors out, or a metric-filter alarm never matches log lines. Use whenever the operator says "the alarm is broken" and the root cause may be metric config, namespace, dimension, period, statistic, threshold model, action target policy, or treat-missing-data setting — not necessarily the metric pipeline itself.
  when_not_to_use: Designing a new alarm policy from scratch (use cloudwatch-alarm-auditor for posture review), debugging the underlying application metric emission path (use cloudwatch-metrics-troubleshooter), building dashboards (use cloudwatch-dashboard-deployer), investigating Logs Insights performance (use cloudwatch-logs-insights-troubshooter), or auto-remediating a firing alarm for a known issue (use auto-remediation-automator). This skill diagnoses alarm-behaviour failures; it does not redesign alarm coverage or fix the upstream metric.
  activation_triggers:
  - CloudWatch alarm INSUFFICIENT_DATA
  - alarm stuck in INSUFFICIENT_DATA
  - CloudWatch alarm not firing
  - alarm never goes to ALARM
  - CloudWatch dimension mismatch
  - alarm dimension case-sensitive
  - CloudWatch alarm period misaligned
  - high-resolution alarm
  - CloudWatch composite alarm
  - alarm math expression error
  - CloudWatch alarm action not triggering
  - SNS topic alarm action
  - Lambda alarm action permission
  - treat-missing-data
  - troubleshoot CloudWatch alarm
  invocation_schema: 'Input: either (a) a symptom description (alarm name, observed state — INSUFFICIENT_DATA / OK-but-expected-ALARM / ALARM-with-no-action, time window), optionally paired with the alarm configuration (describe-alarms output) and the raw metric points (get-metric-data output) for offline classification, OR (b) an AlarmName plus the metric namespace, metric name, dimensions, period, statistic, and threshold for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {METRIC_DIMENSION_MISMATCH, NAMESPACE_TYPO, PERIOD_MISALIGNMENT, RESOLUTION_MISMATCH, STATISTIC_MISMATCH, THRESHOLD_STATIC, THRESHOLD_ANOMALY, MATH_EXPRESSION, COMPOSITE_RULE, TREAT_MISSING_DATA, INSUFFICIENT_DATA_CONFIG, ACTION_SNS_POLICY, ACTION_LAMBDA_POLICY, ACTION_AUTOSCALING_POLICY, ACTION_SSM_POLICY, ACTION_MISSING, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Alarm HighErrorRateAlarm has been in INSUFFICIENT_DATA\nfor 3 days. The Lambda function fn-orders-api is clearly emitting\nErrors, we can see them on the dashboard.\"\nAlarmName: HighErrorRateAlarm\nNamespace: AWS/Lambda\nMetricName: Errors\nDimensions: [{Name: FunctionName, Value: fn-orders-api}]\nPeriod: 300\nStatistic: Sum\nThreshold: 5 (GreaterThanThreshold)\nTreatMissingData: missing\nStateValue: INSUFFICIENT_DATA\nMetric evidence: dashboard shows non-zero Errors for fn-orders-api\n  every 5 minutes for the last 24 hours"
---

# CloudWatch Alarm Troubleshooter

## Quick navigation

| Section | Purpose |
|---|---|
| Quick start | Symptom-to-layer map; non-obvious behaviours to check before diagnosing |
| Mindset / Philosophy | What separates senior CloudOps alarm diagnosis from a generalist |
| Symptom triage table | One-line per symptom: most-likely layer + first probe |
| Pre-flight gate | Alarm-state short-circuit; gather-info commands |
| Diagnostic tree (Steps 0-9) | Symptom-driven probes; each ends in ROOT_CAUSE_IDENTIFIED or pass |
| Output format | TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION contract |
| NEVER section | Anti-patterns that produce misdiagnosis |
| Remediation guidance | Per-layer fix commands |
| Configuration dependency graph | What the alarm reads from, what reads the alarm |
| AWS documentation | Canonical AWS docs by topic |

## STRICT output contract

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
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <alarm-name> in <region>.
  Proceed? (yes/no)"
```

**Verdict contract:** `ROOT_CAUSE_IDENTIFIED` requires a failing probe
that matches the symptom. `INSUFFICIENT_DATA` is emitted when the
alarm-side configuration is clean and the issue is upstream in the
metric pipeline (route to `cloudwatch-metrics-troubleshooter`) or when a
required probe needs operator input the run does not have. There is no
third verdict value.

## NEVER section — anti-patterns

- **NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom.** A process-of-elimination diagnosis erodes
  operator trust when the real cause is elsewhere.
- **NEVER assume dimension values are case-insensitive.** CloudWatch
  treats `FunctionName=fn-orders-api` and `FunctionName=Fn-Orders-API`
  as different metrics. Cross-check against `list-metrics` output
  character-by-character before declaring the metric pipeline broken.
- **NEVER set the alarm Period below the metric's native resolution.**
  `Period: 1` on a standard 60-second metric returns no points; the
  alarm goes INSUFFICIENT_DATA. Period must be a multiple of the
  metric's storage resolution.
- **NEVER treat INSUFFICIENT_DATA as "no traffic / app is fine."** It
  means "CloudWatch found zero metric points that matched the alarm's
  query." Just as often a broken metric pipeline as a quiet app.
- **NEVER assume the alarm's Statistic matches the dashboard's.** Sum,
  Average, Maximum, SampleCount, and extended statistics (p99, TM99)
  produce different values from the same raw points. Dashboard-on-p99
  vs alarm-on-Average is the #1 cause of "dashboard breaches, alarm
  stays OK."
- **NEVER conclude "alarm actions are broken" without checking
  `describe-alarm-history --history-type Action`.** If Action entries
  exist, CloudWatch fired the action; the failure is downstream. If
  Action entries are absent despite ALARM transitions, the target
  policy is blocking CloudWatch.
- **NEVER create an SNS / Lambda alarm action via CLI, Terraform, or
  CloudFormation without explicitly adding the target policy granting
  `cloudwatch.amazonaws.com` permission to invoke.** Console auto-adds;
  IaC does NOT.
- **NEVER use the SEARCH function in an alarm math expression.** SEARCH
  is dashboard-only; alarms reject it and the alarm goes
  INSUFFICIENT_DATA.
- **NEVER conflate an anomaly-detection alarm's training window with a
  broken detector.** A freshly-created detector returns no band for
  several hours. Wait before declaring mis-config.
- **NEVER reference a child alarm by its old name in a composite Rule
  after renaming the child.** The Rule string is not auto-updated; the
  composite silently stops matching. INSUFFICIENT children evaluate as
  false under AND / OR.
- **NEVER wire an ASG ARN directly into AlarmActions.** AlarmActions
  must list a scaling-policy ARN, not the ASG. CloudWatch does not
  validate the action ARN shape; mis-wired actions fail silently.
- **NEVER use `TreatMissingData: breaching` as a substitute for fixing
  a dead metric source.** Useful for silent-failure detection, but the
  operator will eventually need to restore the pipeline.

## Expert heuristic

A senior CloudOps engineer applies three quick checks before any deep
diagnosis. Each is non-obvious and routes the diagnosis away from the
obvious layer:

1. **Dimension values are case-sensitive exact strings.** CloudWatch
   does no normalisation. `FunctionName=Fn-Orders-API` does NOT match
   `FunctionName=fn-orders-api`. The alarm silently falls into
   INSUFFICIENT_DATA. First probe: `list-metrics --namespace <ns>
   --metric-name <m>` and compare character-by-character.
2. **Period must match metric resolution (or be a multiple).**
   High-resolution metrics (1-second storage) accept any multiple of 1.
   Standard metrics (60-second storage) queried with `Period: 1` return
   no points — the alarm goes INSUFFICIENT_DATA. The metric exists; the
   alarm query is wrong.
3. **INSUFFICIENT_DATA means missing data points, NOT zero.** Either
   the source stopped emitting, or the alarm's namespace / dimension /
   period is wrong. `TreatMissingData: breaching` masks the symptom by
   treating absent data as a breach — useful for silent-failure
   detection, but the underlying missing-data issue remains.

## Configuration dependency graph

```
[metric source]                [CloudWatch metric]
 application / Agent ──emit──►  (namespace, metric name,
 put-metric-data / EMF  ──────►   dimensions, native resolution)
                                       │ alarm query
                                       ▼
                              [CloudWatch alarm]
                               (period, statistic, threshold,
                                comparison, evaluation periods,
                                treat-missing-data)
                                       │ state: OK / ALARM / INSUFFICIENT_DATA
                                       ▼
                              [Alarm action targets]
                               SNS topic    (needs sns:Publish
                                              from cloudwatch.amazonaws.com)
                               Lambda fn    (needs lambda:InvokeFunction
                                              from cloudwatch.amazonaws.com)
                               ASG policy   (AlarmActions = policy ARN, not ASG ARN)
                               SSM OpsItem / composite Rule
```

A mis-behaving alarm has exactly three layers to investigate: the
metric source (does the data exist?), the alarm query (does the
configuration match the data?), and the action target (does the target
accept CloudWatch's invocation?). The diagnostic tree walks each in
order based on the symptom.

## Quick reference — symptom triage table

| Symptom phrase / observed state | Most likely layer | First probe |
|---|---|---|
| `StateValue: INSUFFICIENT_DATA` since creation; never transitions | METRIC_DIMENSION_MISMATCH / NAMESPACE_TYPO / PERIOD_MISALIGNMENT / TREAT_MISSING_DATA | `describe-alarms` (Namespace, MetricName, Dimensions, Period), then `get-metric-data` with the same query |
| Dashboard shows metric crossing threshold; alarm stays OK | THRESHOLD_STATIC / STATISTIC_MISMATCH / RESOLUTION_MISMATCH | `describe-alarms` (Threshold, ComparisonOperator, Statistic, Period) vs the dashboard query |
| Alarm transitions ALARM but no notification / no Lambda invocation / no Auto Scaling | ACTION_SNS_POLICY / ACTION_LAMBDA_POLICY / ACTION_AUTOSCALING_POLICY / ACTION_MISSING | `describe-alarms` (AlarmActions), then topic policy / Lambda policy / ASG policy |
| Composite alarm stays OK / INSUFFICIENT despite child alarms in ALARM | COMPOSITE_RULE | `describe-alarms` (AlarmRule), child alarm `StateValue` |
| Math expression alarm INSUFFICIENT or never evaluates | MATH_EXPRESSION | `describe-alarms` (Metrics, Expression), `get-metric-data` with the same expression |
| Anomaly-detection alarm pinned in ALARM; band never widens | THRESHOLD_ANOMALY | `describe-alarms` (ThresholdMetricId, DatapointsToAlarm, EvaluationPeriods), `describe-anomaly-detectors` |
| Alarm fires once then never recovers to OK | TREAT_MISSING_DATA / THRESHOLD_STATIC | `describe-alarms` (TreatMissingData, EvaluationPeriods), `describe-alarm-history` |
| Alarm fires inconsistently with dashboard | PERIOD_MISALIGNMENT / STATISTIC_MISMATCH | Compare alarm Period/Statistic against dashboard query |

## Pre-flight: alarm state and gather-info gate

Before running symptom-specific probes, gather the canonical alarm
configuration and short-circuit on alarm states that mimic alarm
failures.

### Account-wide pre-flight commands

```bash
# 1. Alarm configuration (Namespace, MetricName, Dimensions, Period,
#    Statistic, Threshold, ComparisonOperator, TreatMissingData,
#    AlarmActions, EvaluationPeriods, DatapointsToAlarm, Metrics)
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json

# 2. State history (transitions, config updates, action invocations)
aws cloudwatch describe-alarm-history --alarm-name <alarm-name> \
  --history-type StateHistory \
  --start-time $(date -d '-24 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --output json

# 3. Raw metric points for the alarm's exact query
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"q1","MetricStat":{"Metric":{"Namespace":"<ns>","MetricName":"<m>","Dimensions":<dims>},"Period":<p>,"Stat":"<s>"}}]' \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --output json

# 4. Metric-filter alarms: the filter pattern + log group
aws logs describe-metric-filters --metric-name <m> --namespace <ns> --output json

# 5. Anomaly-detection alarms: the detector configuration
aws cloudwatch describe-anomaly-detectors --namespace <ns> \
  --metric-name <m> --output json
```

### Alarm-state short-circuit

| `StateValue` / pattern | Effect on diagnosis |
|---|---|
| `OK` for the whole life, dashboard clearly shows a breach | Proceed with THRESHOLD_STATIC / STATISTIC_MISMATCH / RESOLUTION_MISMATCH. |
| `INSUFFICIENT_DATA` since creation | Proceed with METRIC_DIMENSION_MISMATCH / NAMESPACE_TYPO / PERIOD_MISALIGNMENT. Most common by an order of magnitude. |
| `ALARM` for the whole life, never recovers to OK | Proceed with THRESHOLD_STATIC (threshold wrong) / TREAT_MISSING_DATA (missing points treated as breaching) / THRESHOLD_ANOMALY (band mis-calibrated). |
| `ALARM` fires, action invoked (visible in history), operator says "no notification" | Action target policy is fine; check the SNS subscription / Lambda invocation logs downstream. Not an alarm-side issue. |
| `ALARM` fires, no action in history | Proceed with ACTION_SNS_POLICY / ACTION_LAMBDA_POLICY / ACTION_MISSING. |
| `OK` → `INSUFFICIENT_DATA` → `OK` cycle | The metric pipeline is intermittent. Investigate the source. TreatMissingData may be masking the breaching impact. |

If the input is malformed (missing AlarmName, absent symptom, no metric
configuration for live diagnosis), emit the INSUFFICIENT_DATA block with
`LAYER: UNKNOWN` listing the missing fields and the next probe to run.

## Process — Diagnostic decision tree (apply in symptom order)

Pick the entry point based on the observed state, then walk the
layer-specific probes in order. Each layer ends with a positive
root-cause confirmation (a failing probe that matches the symptom) or
a pass that moves to the next layer. **Never emit ROOT_CAUSE_IDENTIFIED
without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

- **Dimension values are case-sensitive exact strings; the dimension
  SET must match exactly.** No normalisation. Partial sets query a
  different (usually empty) metric.
- **The alarm Period controls aggregation, not native resolution.**
  `Period: 1` on a standard 60s metric returns no points. Period must
  be a multiple of native resolution.
- **INSUFFICIENT_DATA is the default for new alarms until first
  evaluation completes** (`EvaluationPeriods * Period` seconds). Normal;
  not a bug. If still INSUFFICIENT after that window, the query returns
  no points.
- **`TreatMissingData: breaching` turns a missing-metric alarm into a
  permanently ALARM alarm.** Masks the underlying pipeline issue.
- **Composite Rule is a boolean over child alarm STATE, NOT over the
  underlying metrics.** INSUFFICIENT children propagate as false-ish
  under AND / OR.
- **Math expression alarms: if ANY referenced metric is missing, the
  expression evaluates to INSUFFICIENT_DATA.** Probe each referenced
  metric independently.
- **Anomaly-detection alarms need a training window.** A freshly-created
  detector returns no band for several hours; the alarm sits in
  INSUFFICIENT_DATA until the band is established.
- **SNS / Lambda alarm actions require the target policy to grant
  `cloudwatch.amazonaws.com` invoke permission.** Console auto-adds;
  CLI / Terraform / CloudFormation do NOT. ASG actions require the
  scaling-policy ARN, not the ASG ARN; mis-wired actions fail silently.

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| `StateValue: INSUFFICIENT_DATA` since creation | Step 2 — Metric mismatch |
| Dashboard shows breach; alarm stays OK | Step 3 — Threshold / statistic |
| ALARM fires; no notification / action | Step 4 — Action target |
| Composite alarm never transitions | Step 5 — Composite rule |
| Math expression alarm stuck | Step 6 — Math expression |
| Anomaly alarm pinned or never breaches | Step 7 — Anomaly band |
| Alarm fires once, never recovers | Step 8 — Treat missing data |
| None of the above | Step 9 — INSUFFICIENT_DATA verdict |

### Step 2: INSUFFICIENT_DATA — metric query returns no points

The most common CloudWatch alarm failure. The alarm is syntactically
correct but no metric points exist for the exact query it issues.

#### 2a: Verify the alarm's exact query

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[0] | {Namespace, MetricName, Dimensions, Period, Statistic}'
```

#### 2b: Run the same query via get-metric-data, then without dimensions

```bash
# With the alarm's exact dimensions
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"q1","MetricStat":{"Metric":{"Namespace":"<ns>","MetricName":"<m>","Dimensions":<dims>},"Period":<p>,"Stat":"<s>"}}]' \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) --output json

# Dimensionless — if this returns points but the scoped query does not,
# METRIC_DIMENSION_MISMATCH is confirmed.
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"q1","MetricStat":{"Metric":{"Namespace":"<ns>","MetricName":"<m>"},"Period":<p>,"Stat":"<s>"}}]' \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) --output json
```

#### 2c: Identify which dimension is wrong

```bash
aws cloudwatch list-metrics --namespace <ns> --metric-name <m> --output json | \
  jq '.Metrics[].Dimensions'
```

| Pattern | Likely cause |
|---|---|
| Alarm dimension value differs in case from list-metrics output | Case-sensitivity. Fix to match exactly. |
| Alarm has MORE dimensions than list-metrics shows | Over-specified query. Remove the extra dimension. |
| Namespace string differs (`AWS/lambda` vs `AWS/Lambda`) | Namespace typo. Case-sensitive on namespace. |
| Metric name differs in case or hyphenation | Metric-name typo. |

#### 2d: If both queries return no points

The metric pipeline is broken. NOT an alarm-side issue; route to
`cloudwatch-metrics-troubleshooter`.

**Verdicts:** Dimension mismatch → ROOT_CAUSE_IDENTIFIED,
`LAYER: METRIC_DIMENSION_MISMATCH`. Namespace typo →
`LAYER: NAMESPACE_TYPO`. Period misaligned →
`LAYER: PERIOD_MISALIGNMENT`. Metric genuinely not emitted →
INSUFFICIENT_DATA, `LAYER: UNKNOWN`.

### Step 3: Alarm stays OK while dashboard shows breach

#### 3a: Read the threshold configuration

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[0] | {Threshold, ComparisonOperator, EvaluationPeriods, DatapointsToAlarm, Period, Statistic, TreatMissingData}'
```

#### 3b: Compare alarm query against dashboard query

| Divergence | Effect |
|---|---|
| Dashboard `Average`, alarm `Sum` (or vice versa) | STATISTIC_MISMATCH. A high-error minute looks large on Sum but small on Average. |
| Dashboard period 1 min, alarm period 5 min | PERIOD_MISALIGNMENT. Aggregation smooths spikes. |
| Dashboard `p99`, alarm `Average` | STATISTIC_MISMATCH. Extended statistics must use `ExtendedStatistic`, not `Statistic`. |
| `EvaluationPeriods: 5, DatapointsToAlarm: 5` | Breach must persist 5 periods. A 1-period breach does not fire. |
| `GreaterThanThreshold`, threshold 100, metric peaks at exactly 100 | Strict comparison; equal-to does not breach. Use `GreaterThanOrEqualToThreshold`. |

#### 3c: High-resolution vs standard resolution mismatch

If the metric is high-resolution (1-second storage via
`put-metric-data --storage-resolution 1`) but the alarm Period is 60,
the alarm aggregates 60 1-second points per evaluation. A 10-second
spike visible on the 1-second dashboard is averaged away. Either lower
the alarm Period to 1 (or a small multiple) or accept the smoothed view.

If the metric is standard-resolution but the alarm Period is 1, the
alarm goes INSUFFICIENT_DATA because no sub-60s points exist. Route
back to Step 2 (PERIOD_MISALIGNMENT).

**Verdicts:** Statistic mismatch → `LAYER: STATISTIC_MISMATCH`. Period
aggregation smoothing spikes → `LAYER: PERIOD_MISALIGNMENT`. Threshold
comparison wrong (strict vs inclusive) → `LAYER: THRESHOLD_STATIC`.
High-resolution metric seen through standard period →
`LAYER: RESOLUTION_MISMATCH`.

### Step 4: ALARM fires but no action triggers

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[0] | {AlarmActions, OKActions, InsufficientDataActions}'

aws cloudwatch describe-alarm-history --alarm-name <alarm-name> \
  --history-type Action \
  --start-time $(date -d '-24 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --output json
```

The Action history records each attempted invocation. If history shows
the action fired but the operator reports no notification, the issue is
downstream (SNS subscription, Lambda invocation) — not alarm-side. If
history shows no Action entries despite ALARM transitions in
StateHistory, the action target policy is blocking CloudWatch.

#### 4a-c: Action target policies

| Target | Probe | Required permission | Layer if missing |
|---|---|---|---|
| SNS topic | `aws sns get-topic-attributes --topic-arn <arn>` | `sns:Publish` from `cloudwatch.amazonaws.com` | `ACTION_SNS_POLICY` |
| Lambda fn | `aws lambda get-policy --function-name <fn>` | `lambda:InvokeFunction` from `cloudwatch.amazonaws.com` | `ACTION_LAMBDA_POLICY` |
| ASG policy | `aws autoscaling describe-policies --auto-scaling-group-name <asg> --policy-names <name>` | AlarmActions ARN must match an existing policy | `ACTION_AUTOSCALING_POLICY` |

If `AlarmActions: []`, no action is configured →
`LAYER: ACTION_MISSING`.

### Step 5: Composite alarm never transitions

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.CompositeAlarms[] | {AlarmRule, StateValue}'

aws cloudwatch describe-alarms --alarm-names <child-1> <child-2> ... \
  --output json | jq '.MetricAlarms[] | {AlarmName, StateValue}'
```

| Pattern | Cause |
|---|---|
| Rule is `ALARM(c1) AND ALARM(c2)`, only one child ALARM | AND requires both. Use OR for either-child semantics. |
| Rule references a child by NAME, but the child was renamed | Rule string is not auto-updated; composite never matches. |
| Child alarm INSUFFICIENT_DATA | INSUFFICIENT propagates as false in AND / OR. Composite stays OK / INSUFFICIENT. |
| Rule uses `TRUE` / `FALSE` literals incorrectly | Syntax error in the rule. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: COMPOSITE_RULE`.

### Step 6: Math expression alarm stuck

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[0] | {Metrics, Threshold, ComparisonOperator}'
```

| Pattern | Cause |
|---|---|
| Expression divides by zero (`e2 / e1`, e1 has no points) | Returns no value; alarm INSUFFICIENT. Guard with `FILL(e1, 0)`. |
| Expression references an `Id` with no points | Whole expression returns nothing. Probe each referenced metric independently. |
| Expression uses `m1 + m2` at different periods | Aggregation mismatch. Align periods. |
| `SEARCH` function used in alarm | SEARCH is dashboard-only; alarms reject it. |
| Threshold on the wrong `Id` | Threshold applies to the wrong output. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MATH_EXPRESSION`.

### Step 7: Anomaly-detection alarm

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[0] | {ThresholdMetricId, DatapointsToAlarm, EvaluationPeriods, Metrics}'

aws cloudwatch describe-anomaly-detectors --namespace <ns> \
  --metric-name <m> --output json
```

| Pattern | Cause |
|---|---|
| Detector freshly created; band not established | Wait for training window (15 min to hours). |
| Band too wide; anomalies never breach | Detector learned on high-variance period. Re-train or raise `StandardDeviation`. |
| Band too narrow; alarm pinned ALARM | Detector learned on calm period. Re-train or widen. |
| Threshold references wrong metric Id | `ThresholdMetricId` must point to the band expression. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: THRESHOLD_ANOMALY`.

### Step 8: Alarm fires once, never recovers

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[0] | {TreatMissingData, EvaluationPeriods, DatapointsToAlarm, Period}'

aws cloudwatch describe-alarm-history --alarm-name <alarm-name> \
  --history-type StateHistory \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --output json
```

If the metric pipeline stopped emitting after the initial breach and
`TreatMissingData: breaching`, every subsequent missing period is
treated as a breach. The alarm stays ALARM forever even though no new
points exist. ROOT_CAUSE_IDENTIFIED, `LAYER: TREAT_MISSING_DATA`. Fix:
change TreatMissingData to `notBreaching` (or `missing` to surface the
issue) and investigate why the metric stopped emitting.

### Step 9: INSUFFICIENT_DATA verdict

If none of the above produced a positive root-cause match, OR the
symptom clearly indicates an AWS-side CloudWatch service degradation
(visible in AWS Health), emit `VERDICT: INSUFFICIENT_DATA` with
`LAYER: UNKNOWN` listing the missing pieces (alarm configuration, raw
metric evidence, action target policy) and the next probe to run.
Recommend routing to `cloudwatch-metrics-troubleshooter` for the metric
pipeline if the alarm-side configuration is clean.

## Worked examples

### Worked example — INSUFFICIENT_DATA, dimension case mismatch

```text
TARGET: HighErrorRateAlarm
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Alarm queries AWS/Lambda Errors with dimension
  FunctionName=Fn-Orders-API (capitalised), but the metric is emitted
  with FunctionName=fn-orders-api (lowercase). CloudWatch dimension
  values are case-sensitive exact strings; no points exist for the
  capitalised value, so the alarm sits in INSUFFICIENT_DATA (Step 2c).
LAYER: METRIC_DIMENSION_MISMATCH
EVIDENCE:
  - Symptom: alarm has been INSUFFICIENT_DATA since creation 3 days ago.
  - Probe: aws cloudwatch describe-alarms returns Dimensions:
    [{Name: FunctionName, Value: Fn-Orders-API}].
  - Probe: aws cloudwatch list-metrics --namespace AWS/Lambda
    --metric-name Errors returns the metric with
    FunctionName=fn-orders-api (lowercase).
  - Probe: aws cloudwatch get-metric-data with the alarm's exact
    query returns Values: [] (no points).
  - Probe: aws cloudwatch get-metric-data with the corrected
    (lowercase) dimension returns Values: [3, 1, 0, 7, 2, ...].
  - Passing: namespace AWS/Lambda is correct; Period 300 matches
    native 60s resolution; Statistic Sum is valid for Errors.
REMEDIATION:
  1. Update the alarm with the corrected dimension value:
     aws cloudwatch put-metric-alarm --alarm-name HighErrorRateAlarm \
       --namespace AWS/Lambda --metric-name Errors \
       --dimensions Name=FunctionName,Value=fn-orders-api \
       --period 300 --statistic Sum --threshold 5 \
       --comparison-operator GreaterThanThreshold \
       --evaluation-periods 1 --profile <p>
  2. Verify the alarm transitions out of INSUFFICIENT_DATA within one
     evaluation period (5 minutes):
     aws cloudwatch describe-alarms --alarm-names HighErrorRateAlarm \
       --query 'MetricAlarms[0].StateValue'
CONFIRM: Before updating the alarm, emit and await:
  "CONFIRM: About to update HighErrorRateAlarm dimension from
   Fn-Orders-API to fn-orders-api. Proceed? (yes/no)"
```

### Worked example — ALARM fires, SNS topic policy missing

```text
TARGET: ProductionDiskSpaceAlarm
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Alarm has transitioned to ALARM 4 times in 24 hours (visible
  in describe-alarm-history StateHistory), but the SNS topic policy
  on the AlarmActions target does not grant cloudwatch.amazonaws.com
  permission to call sns:Publish. No notifications were delivered
  (Step 4a).
LAYER: ACTION_SNS_POLICY
EVIDENCE:
  - Symptom: alarm fires (visible on dashboard, ALARM confirmed), but
    the on-call Slack channel received nothing.
  - Probe: aws cloudwatch describe-alarms returns AlarmActions:
    [arn:aws:sns:us-east-1:111111111111:OpsNotifications].
  - Probe: aws cloudwatch describe-alarm-history --history-type Action
    returns no Action entries in the last 24 hours despite 4 ALARM
    transitions in StateHistory.
  - Probe: aws sns get-topic-attributes on OpsNotifications returns
    a Policy with NO statement granting cloudwatch.amazonaws.com
    sns:Publish.
  - Passing: the SNS topic works (CLI test publish delivers to the
    Slack subscription); the Lambda subscription is Confirmed.
REMEDIATION:
  1. Add the CloudWatch service principal to the SNS topic policy:
     aws sns add-permission --topic-arn \
       arn:aws:sns:us-east-1:111111111111:OpsNotifications \
       --label AllowCloudWatchAlarmPublish \
       --aws-account-id 111111111111 \
       --action-name Publish --profile <p>
  2. Verify by triggering a test alarm transition (set threshold to 0
     momentarily) and confirm Slack receives the notification within
     60 seconds. Then restore the original threshold.
CONFIRM: Before updating the topic policy, emit and await:
  "CONFIRM: About to add cloudwatch.amazonaws.com sns:Publish to
   OpsNotifications topic. Proceed? (yes/no)"
```

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-metric-alarm`, `delete-alarms`, `set-topic-attributes`,
  `add-permission`, `put-metric-data`), emit and await operator
  approval. Include the diff (old vs new value) in the prompt.
- **Read-only first.** Every diagnostic probe is read-only
  (`describe-alarms`, `get-metric-data`, `describe-alarm-history`,
  `list-metrics`, `get-topic-attributes`, `get-policy`,
  `describe-anomaly-detectors`, `describe-policies`). Never perform
  state-changing operations as diagnostic probes.
- **`put-metric-alarm`** with the same alarm name overwrites the
  existing alarm. Prefer this over `delete-alarms` (irreversible) —
  use `ActionsEnabled: false` to disable while preserving config.
- **`put-metric-data`** for a test point pollutes the metric history.
  Use a dedicated `<metric>-test` name; test points are not removable.
- **SNS topic / Lambda policy changes** affect every alarm and invoker
  on the target. Scope Lambda permissions to `--source-arn <alarm-arn>`;
  tighten SNS policy gradually.
- **Anomaly detector changes** trigger a re-training window. The band
  will be absent for several hours; downstream alarms go
  INSUFFICIENT_DATA during the window.
- **Bulk remediation batch limit.** Batch same-root-cause remediation
  across multiple alarms into groups of at most 5; emit a single
  CONFIRM per batch; verify between batches.

## Remediation guidance

Every remediation uses `put-metric-alarm` (or `put-composite-alarm` for
composite) to overwrite the existing alarm configuration, OR a target-
side policy command for action-layer fixes. Always emit CONFIRM before
executing; include the diff (old vs new value) in the prompt.

### Metric-side fixes (METRIC_DIMENSION_MISMATCH, NAMESPACE_TYPO, PERIOD_MISALIGNMENT, STATISTIC_MISMATCH, THRESHOLD_STATIC, RESOLUTION_MISMATCH)

```bash
aws cloudwatch put-metric-alarm --alarm-name <name> \
  --namespace <corrected-ns> --metric-name <m> \
  --dimensions Name=<d1>,Value=<corrected-value> \
  --period <corrected-p> --statistic <corrected-s> \
  --threshold <t> --comparison-operator <op> \
  --evaluation-periods <n> --alarm-actions <actions> --profile <p>
```
- Dimension / namespace values must match `list-metrics` output
  character-for-character (case, hyphen, underscore).
- Period must be a multiple of the metric's native resolution (60s for
  standard, 1s for high-resolution).
- Statistic must match the dashboard view (Sum / Average / Maximum /
  SampleCount / extended-statistic p99).
- Comparison-operator boundary: use `GreaterThanOrEqualToThreshold` when
  the metric value equals the threshold at the boundary.

### THRESHOLD_ANOMALY

Re-create the detector via `put-anomaly-detector` on a calmer window,
OR raise / lower `--standard-deviations` to widen / narrow the band.

### MATH_EXPRESSION

Restructure `--metrics` JSON: add `FILL(metricId, 0)` guards, align
periods across referenced metrics, remove SEARCH, fix the threshold's
target `Id`.

### COMPOSITE_RULE

```bash
aws cloudwatch put-composite-alarm --alarm-name <name> \
  --alarm-rule 'ALARM(child1) OR ALARM(child2)' \
  --alarm-actions <actions> --profile <p>
```
Rewrite the rule to express the intended boolean semantics; verify
child alarm names against `describe-alarms` output (names are not
auto-updated on child rename).

### TREAT_MISSING_DATA

```bash
aws cloudwatch put-metric-alarm --alarm-name <name> \
  ... --treat-missing-data notBreaching --profile <p>
```
Options: `breaching` (silent-failure detection — pair with pipeline
investigation), `notBreaching` (missing is benign), `ignore` (hold
state), `missing` (default; alarm goes INSUFFICIENT_DATA).

### Action-side fixes (ACTION_SNS_POLICY, ACTION_LAMBDA_POLICY, ACTION_AUTOSCALING_POLICY, ACTION_MISSING)

```bash
# SNS topic: grant cloudwatch.amazonaws.com permission to Publish
aws sns add-permission --topic-arn <topic-arn> \
  --label AllowCloudWatchAlarmPublish \
  --aws-account-id <topic-owner-account-id> \
  --action-name Publish --profile <p>

# Lambda: grant cloudwatch.amazonaws.com permission to InvokeFunction
aws lambda add-permission --function-name <fn> \
  --statement-id AllowCloudWatchAlarm \
  --action lambda:InvokeFunction \
  --principal cloudwatch.amazonaws.com \
  --source-arn arn:aws:cloudwatch:<region>:<account-id>:alarm:<alarm-name> \
  --profile <p>

# ASG: create the scaling policy, then reference its ARN in AlarmActions
aws autoscaling put-scaling-policy --auto-scaling-group-name <asg> \
  --policy-name ScaleUpOnAlarm --adjustment-type ChangeInCapacity \
  --scaling-adjustment 1 --profile <p>
# Then update the alarm's AlarmActions with the returned PolicyARN.
```
For ACTION_MISSING: add an action target ARN to AlarmActions in the
next `put-metric-alarm` call; verify the target accepts the CloudWatch
service principal.

## Deep reference — quick lookup matrices

### TreatMissingData values

`missing` (default; alarm goes INSUFFICIENT_DATA), `breaching` (treat
missing as breach — silent-failure detection), `notBreaching` (missing
is benign), `ignore` (hold current state).

### Native metric resolution

AWS service metrics, CloudWatch Agent default, `put-metric-data`
default: 60 seconds. CloudWatch Agent high-resolution,
`put-metric-data --storage-resolution 1`, Embedded Metric Format:
1 second. Alarm Period must be a multiple of native resolution.

### Statistic semantics

`Sum` (counts), `Average` (latency, CPU), `Maximum` (peak), `Minimum`
(lowest), `SampleCount` (throughput), `p99`/`p95`/`TM99` via
`--extended-statistic` (tail latency). Switching statistic without
re-checking the dashboard view is the #1 source of "dashboard
breaches, alarm stays OK."

### Composite rule grammar

`ALARM(name)` / `OK(name)` / `INSUFFICIENT(name)` predicates with
`AND` / `OR` / `NOT` and parentheses; `TRUE` / `FALSE` literals.
INSUFFICIENT children evaluate as false under AND / OR. Child names
are NOT auto-updated on rename.

### Math expression support

Each entry in `Metrics` has an `Id` (`m1`, `e1`); expressions
reference other `Id`s. Supported: `AVG`, `SUM`, `MIN`, `MAX`,
`STDDEV`, `FILL`, `ABS`, `CEIL`, `FLOOR`, `TIME_SERIES`,
`DATAPOINT_COUNT`. SEARCH is dashboard-only. Divide-by-zero returns
no value; guard with `FILL(divisorId, 0)`.

### Action target permission matrix

| Target | Required permission | Principal |
|---|---|---|
| SNS topic | `sns:Publish` | `cloudwatch.amazonaws.com` |
| Lambda function | `lambda:InvokeFunction` | `cloudwatch.amazonaws.com` |
| Auto Scaling policy | AlarmActions = policy ARN, not ASG ARN | n/a |
| SSM OpsItem | Automatic for the account's OpsCenter | n/a |

Console-created alarms auto-add SNS / Lambda permission; CLI /
Terraform / CloudFormation alarms do NOT.

## Recent AWS features (2024-2026)

- **Composite alarm rule expressions (2024):** GA of the full boolean
  grammar; INSUFFICIENT predicate now enables detection of children in
  INSUFFICIENT_DATA state.
- **Built-in anomaly-detection alarms (2024-2025):** CloudWatch auto-
  creates the detector when the alarm references a band. Detector still
  needs a training window; freshly-created anomaly alarms sit in
  INSUFFICIENT_DATA for 15 min to several hours.
- **DSP (Data Protection) on logs affecting metric filters (2025):**
  Masked sensitive fields change metric-filter match patterns. A
  metric-filter alarm that worked yesterday may stop matching today if a
  new data-protection policy masks the anchored field.
- **Metric Streams high-resolution passthrough (2024-2025):** Streams
  forward 1-second metrics at 1-second granularity; alarms at
  `Period: 1` are now meaningful for streamed sources.
- **Cross-account observability (2024-2025):** Alarms can reference
  metrics in a monitoring account; source-account dimension values are
  preserved and case-sensitivity still applies across aggregation.

## Domain

AWS CloudOps / CloudWatch Alarms, Metric Configuration, Alarm Action Delivery, Composite Alarms, Anomaly Detection, Treat-Missing-Data.

## AWS documentation

- **Creating alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- **TreatMissingData** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html#console-alarm-missing-data
- **High-resolution metrics** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html#high-resolution-metrics
- **Composite alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html
- **Math expression alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html
- **Anomaly detection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html
- **SNS topic policies for alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html
- **Lambda permissions for alarms** — https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchalerts.html
