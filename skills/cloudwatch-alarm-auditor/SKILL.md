---
name: cloudwatch-alarm-auditor
description: 'Audits CloudWatch alarm configurations for blind spots across six dimensions: detection strategy (anomaly detection vs static threshold), action wiring (SNS/Lambda/AutoScaling), missing-metric handling (TreatMissingData), composite-alarm integrity, alarm state history, and structural config errors. Emits a deterministic verdict (NO_ANOMALY | NO_ACTION | INSUFFICIENT_DATA | CONFIG_GAP | OK) per alarm with enumerated findings and CLI remediation. Use when reviewing CloudWatch alarms, checking for missing alarm actions, auditing insufficient-data handling, validating anomaly-detection coverage, or hardening alarm posture before production deployment.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline alarm-config classification. Live-account audits use aws cloudwatch describe-alarms, describe-alarm-history, and describe-anomaly-detectors (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  verdict_shape: NO_ANOMALY | NO_ACTION | INSUFFICIENT_DATA | CONFIG_GAP | OK
  when_to_use: Reviewing a CloudWatch alarm configuration before production deployment, checking whether alarm actions are wired (SNS/Lambda/AutoScaling), auditing insufficient-data handling, validating anomaly-detection coverage vs static thresholds, inspecting composite alarm integrity, or hardening alarm posture across an account.
  activation_triggers: audit this CloudWatch alarm, check my alarm actions, is this alarm configured correctly, alarm has no SNS topic, insufficient data handling, should I use anomaly detection, composite alarm audit, missing metric alarm, alarm blind spot, TreatMissingData
  invocation_schema: 'Input: either (a) a CloudWatch alarm configuration (MetricAlarm or CompositeAlarm JSON or text representation), optionally paired with alarm state history, OR (b) an alarm name for live-account audit. Output: deterministic ALARM/VERDICT/REASON/FINDINGS/REMEDIATION block per alarm, where VERDICT is one of NO_ANOMALY, NO_ACTION, INSUFFICIENT_DATA, CONFIG_GAP, OK.'
  version: 0.2.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch, alarms, alarm actions, SNS, anomaly detection, composite alarms, insufficient data, TreatMissingData, missing metric, alarm state history, threshold, DatapointsToAlarm, EvaluationPeriods, alarm audit, blind spot, ActionsEnabled, MetricMath, PutMetricAlarm
  tags: cloudwatch, monitoring, alarms, anomaly-detection, observability, audit
---

# CloudWatch Alarm Auditor

## Mindset

**One-line takeaway:** the verdict is the **first** matching condition in the
ordered classification — structural config errors (CONFIG_GAP) always win
because a broken alarm cannot fire at all, followed by missing-notification
wiring (NO_ACTION), missing-data blind spots (INSUFFICIENT_DATA), and detection
strategy gaps (NO_ANOMALY).

An alarm has one job: detect a condition and notify someone (or trigger an
auto-remediation). When any link in that chain breaks, the alarm becomes a
false sense of security — it exists on the dashboard but never pages anyone.
The most dangerous alarm is one that looks healthy but silently fails.

- A broken config (DatapointsToAlarm > EvaluationPeriods) means the alarm can
  **never transition to ALARM** — it is permanently stuck.
- A missing-metric alarm with default TreatMissingData enters INSUFFICIENT_DATA
  and does **NOT** trigger AlarmActions — it triggers InsufficientDataActions,
  which is almost always empty.
- An alarm with ActionsEnabled: false or empty AlarmActions fires but nobody
  notices — it is a **monitoring black hole**.
- A static threshold on a variable metric (traffic, latency) either floods
  on-call with false positives or misses real anomalies — AnomalyDetection
  adapts to normal patterns.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| DatapointsToAlarm > EvaluationPeriods | **CONFIG_GAP** | Step 1a |
| Composite Rule references unknown alarm | **CONFIG_GAP** | Step 1b |
| Period < metric native resolution | **CONFIG_GAP** | Step 1c |
| ActionsEnabled: false (global kill switch) | **NO_ACTION** | Step 2a |
| AlarmActions empty on metric alarm | **NO_ACTION** | Step 2b |
| Composite alarm with empty AlarmActions | **NO_ACTION** | Step 2c |
| TreatMissingData unset (defaults to "missing") + no InsufficientDataActions | **INSUFFICIENT_DATA** | Step 3a |
| Alarm stuck in INSUFFICIENT_DATA state for > 24h | **INSUFFICIENT_DATA** | Step 3b |
| Static threshold on high-variance metric (traffic/latency/error-rate) | **NO_ANOMALY** | Step 4a |
| AnomalyDetection band with stdev <= 1 (over-sensitive) | **NO_ANOMALY** | Step 4b |
| All dimensions pass + actions wired + data handling correct | **OK** | Step 5 |

See the ordered steps below for edge cases. Deep CloudWatch internals
(evaluation lag, MetricMath FILL trap, high-resolution alarm costs) are in the
[Expert edge cases](#expert-edge-cases) section.

## Pre-flight: alarm metadata gate (run before classification)

Before evaluating the alarm configuration, classify the alarm type. Several
attributes **short-circuit** the audit.

**Multi-alarm / account-wide sweep note (pagination):** when auditing every
alarm in an account, `aws cloudwatch describe-alarms` returns at most 100 per
page (`--max-records 100`). Use `--next-token` from the prior `NextToken` to
page through all alarms; iterating only the first page silently skips the long
tail. Filter by `--alarm-types Composite|Metric` to separate alarm types. For
each alarm, also fetch `describe-alarm-history` (max 100 records per call —
drain `NextToken`) to check for stuck states.

| Attribute | Value | Effect on audit |
|---|---|---|
| AlarmType | `CompositeAlarm` | **Composite alarm.** Derives state from a Rule expression over child alarm states. No MetricName, Namespace, Period, or TreatMissingData — these do not apply. Audit the Rule expression and actions only. |
| AlarmType | `MetricAlarm` | Proceed with full audit (Steps 1-5). |
| ActionsEnabled | `false` | **Global kill switch.** All action lists (AlarmActions, OKActions, InsufficientDataActions) are suppressed even if populated. Jump to Step 2a — this is NO_ACTION regardless of what actions are listed. |
| StateValue | `INSUFFICIENT_DATA` | Alarm is currently stuck in insufficient-data state. Elevates Step 3 to critical priority — the blind spot is active, not theoretical. |
| StateValue | `ALARM` | Alarm is currently firing. Still audit config — an alarm stuck in ALARM for days without clearing may indicate a threshold set too low or an auto-remediation that failed. |

**If the alarm configuration is malformed** (invalid JSON, missing required
fields like AlarmName, missing Metrics on a metric alarm, missing Rule on a
composite alarm), output:

```text
ALARM: <alarm-name or "unknown">
VERDICT: ERROR
REASON: Alarm configuration is not valid — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws cloudwatch describe-alarms --alarm-names <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious CloudWatch alarm behaviors

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — "Step 0: Expert knowledge" holds all 10 non-obvious behaviors (TreatMissingData default, INSUFFICIENT_DATA actions, M-of-N, ActionsEnabled kill switch, PutMetricAlarm overwrite, Rule limits, anomaly warm-up, MetricMath FILL, 5-action cap, Period/resolution, high-resolution cost).
Load that reference before classifying edge-case alarms — each behavior changes a verdict if ignored.

### Step 1: CONFIG_GAP — structural configuration errors

Check for configurations that make the alarm **non-functional or impossible
to satisfy**. These are the highest priority because the alarm cannot fire
regardless of data.

**1a: DatapointsToAlarm > EvaluationPeriods.** If DatapointsToAlarm exceeds
EvaluationPeriods, the alarm condition can never be met. This is a config
error that CloudWatch accepts without validation. Emit CONFIG_GAP.

**1b: Composite Rule references unknown alarm.** For composite alarms, if the
Rule expression references an alarm name that does not exist in the account
(invalid `ALARM(name)` or `OK(name)` reference), the expression evaluates to
false permanently. Emit CONFIG_GAP. Note: the auditor may need live
`describe-alarms` to verify existence; in offline mode, flag references that
look like typos or placeholders.

**1c: Period / metric resolution mismatch.** If the alarm Period is shorter
than the metric's native publishing interval, most evaluation windows will be
empty. For example, Period=60 on an AWS/RDS metric published every 5 minutes
produces 4 empty windows out of 5. This is not a hard error but degrades alarm
effectiveness. If the mismatch is severe (Period < publishing interval / 2),
emit CONFIG_GAP.

**1d: ComparisonOperator / Threshold impossibility.** If the threshold is
impossible for the metric (e.g., `LessThanThreshold: 0` on a metric that is
always >= 0, like `StatusCheckFailed`), the alarm can never enter the ALARM
state. Emit CONFIG_GAP.

### Step 2: NO_ACTION — alarm fires but nobody is notified

Check for missing notification wiring. An alarm without actions is a
monitoring black hole — it exists on the dashboard but never pages anyone.

**2a: ActionsEnabled: false.** Regardless of what actions are listed, this
flag suppresses all notifications and auto-remediations. Emit NO_ACTION with a
finding that ActionsEnabled is false.

**2b: Metric alarm with empty AlarmActions.** If AlarmActions is empty (or
absent), the alarm transitions to ALARM state but takes no action. Check
OKActions and InsufficientDataActions as well — if ALL three are empty, the
alarm provides zero notification value. Emit NO_ACTION.

**2c: Composite alarm with empty AlarmActions.** A composite alarm that
aggregates child alarms but has no AlarmActions of its own relies entirely on
child alarm actions. This is a common anti-pattern: operators assume the
composite alarm "rolls up" notifications, but it does not — each alarm
notifies independently. If the composite alarm's AlarmActions is empty, emit
NO_ACTION. The composite alarm should have at least one escalation action
distinct from child alarm actions.

### Step 3: INSUFFICIENT_DATA — missing-data blind spot

Check for configurations where the alarm is likely to enter INSUFFICIENT_DATA
without proper handling.

**3a: TreatMissingData unset or "missing" + no InsufficientDataActions.** If
TreatMissingData is not set (defaults to "missing") or explicitly set to
"missing", the alarm enters INSUFFICIENT_DATA state when no datapoints arrive.
If InsufficientDataActions is also empty, this transition is completely silent.
This is the most common alarm blind spot. Emit INSUFFICIENT_DATA.

Risk factors that elevate missing-data probability:
- Custom metrics (application-specific, may stop publishing during deploy or
  crash)
- Error/rate metrics (zero events = no datapoint)
- Metrics from stopped or terminated instances
- Cross-account/cross-region metrics (network disruption = missing data)

**3b: Alarm currently in INSUFFICIENT_DATA state.** If the alarm's StateValue
is INSUFFICIENT_DATA, the blind spot is active. This is more urgent than a
theoretical risk — the alarm is right now unable to detect anything. Emit
INSUFFICIENT_DATA regardless of TreatMissingData setting (the state is the
ground truth).

**TreatMissingData decision guide:**
- `breaching` — treat missing data as a threshold breach. Best for availability
  metrics where missing data itself indicates a problem (metric stopped
  publishing = system is down).
- `notBreaching` — treat missing data as within bounds. Best for metrics where
  absence is normal (error count = 0 means no datapoint published).
- `ignore` — maintain current alarm state. Best when you want the alarm to
  "hold" its last known state during transient gaps.
- `missing` (default) — enter INSUFFICIENT_DATA. Almost never the desired
  behavior for production alarms.

### Step 4: NO_ANOMALY — suboptimal detection strategy

Check whether the alarm uses a static threshold where anomaly detection would
provide better signal quality.

**4a: Static threshold on high-variance metric.** If the alarm uses a static
threshold (ComparisonOperator + Threshold) on a metric known for high
variance, seasonality, or time-of-day patterns, the alarm will either:
- Flood on-call with false positives (threshold too low during peak hours)
- Miss real anomalies (threshold too high to avoid noise)

Metrics that benefit from anomaly detection:
- **Traffic/volume:** RequestCount, InvocationCount, ConnectionCount
- **Latency:** Latency, Duration, TargetResponseTime
- **Error rates:** 5XXError, ErrorCount, ThrottledRequests
- **Custom business metrics:** orders/min, active-users, queue depth

Metrics well-suited for static thresholds:
- **Utilization with known ceiling:** DiskSpaceUtilization (> 80%),
  MemoryUtilization (> 90%)
- **Binary/status:** StatusCheckFailed (> 0), Backup job failures (> 0)
- **Countdown:** certificate DaysToExpiry (< 30)

If the metric namespace + name matches a high-variance pattern AND the alarm
uses a static threshold, emit NO_ANOMALY with a recommendation to adopt
AnomalyDetection.

**4b: AnomalyDetection band with stdev <= 1.** An anomaly detection band with
a standard deviation of 1 or less is extremely tight — normal operational
variance will trigger frequent false alarms. The typical recommendation is
stdev 2 (moderate sensitivity) or stdev 3 (low sensitivity, major incidents
only). If stdev <= 1, emit NO_ANOMALY (the detection config is present but
mis-calibrated).

### Step 5: OK — all dimensions pass

If the alarm passes all checks (valid config, actions wired, proper
missing-data handling, appropriate detection strategy), emit OK.

For OK alarms, still note:
- Whether the alarm has recent state history (an alarm that has never
  transitioned to ALARM may have a threshold set too conservatively).
- Whether OKActions are configured (clearing notifications are optional but
  useful for auto-remediation workflows).

## Output format (per alarm)

```text
ALARM: <alarm-name>
VERDICT: NO_ANOMALY | NO_ACTION | INSUFFICIENT_DATA | CONFIG_GAP | OK
REASON: <1-2 sentences citing the specific config gap and step number>
FINDINGS:
  - [<SEVERITY>] <finding description (Step Na)>
  - [<SEVERITY>] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

SEVERITY mapping: CONFIG_GAP = CRITICAL, NO_ACTION = CRITICAL,
INSUFFICIENT_DATA = HIGH, NO_ANOMALY = MEDIUM, OK = LOW.

### Worked example — missing-data blind spot with no actions

```text
ALARM: api-error-rate-prod
VERDICT: NO_ACTION
REASON: AlarmActions is empty — the alarm transitions to ALARM state but takes
no notification or auto-remediation action (Step 2b). TreatMissingData is also
unset, creating a secondary INSUFFICIENT_DATA risk on a custom error metric.
FINDINGS:
  - [CRITICAL] AlarmActions is empty — alarm fires into the void (Step 2b)
  - [HIGH] TreatMissingData unset (defaults to "missing") on a custom error
    metric with no InsufficientDataActions (Step 3a)
REMEDIATION:
  1. Add an SNS topic to AlarmActions:
     aws cloudwatch put-metric-alarm --alarm-name api-error-rate-prod \
       --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
  2. Set TreatMissingData to breaching (missing data = system down):
     aws cloudwatch put-metric-alarm --alarm-name api-error-rate-prod \
       --treat-missing-data breaching
```

## Expert edge cases

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — "Expert edge cases": M-of-N lag, MetricMath FILL(), composite short-circuit, action dedup, high-resolution cost, pagination, anomaly warm-up, cross-account AccountId.
Load when auditing composite, MetricMath, or cross-account alarms.

## Anti-Patterns — NEVER

- NEVER classify an alarm with DatapointsToAlarm > EvaluationPeriods as
  anything other than CONFIG_GAP. The condition is mathematically impossible
  to satisfy — the alarm is permanently non-functional, regardless of metric
  data or action wiring.

- NEVER treat `ActionsEnabled: false` as a minor flag. It is a global kill
  switch that suppresses ALL actions — SNS, Lambda, AutoScaling, every
  category. An alarm with ActionsEnabled: false is functionally identical to
  one with no actions at all.

- NEVER assume missing data means "no problem." The default TreatMissingData
  behavior is "missing" — the alarm enters INSUFFICIENT_DATA and does NOT
  trigger AlarmActions. For availability metrics, missing data often means
  the monitoring agent itself is down, which IS the problem.

- NEVER skip checking InsufficientDataActions. An alarm may have excellent
  AlarmActions wiring but if InsufficientDataActions is empty and
  TreatMissingData is "missing" (or unset), the alarm has a blind spot for
  the exact scenario where the metric stops reporting.

- NEVER recommend anomaly detection for every metric. Binary metrics
  (StatusCheckFailed), countdown metrics (certificate expiry), and metrics
  with well-understood capacity limits (disk utilization) are better served
  by static thresholds. Anomaly detection adds value for metrics with
  seasonality, trend drift, or unpredictable variance.

- NEVER flag a composite alarm for not having TreatMissingData. Composite
  alarms do not monitor metrics directly — they evaluate a Rule expression
  over child alarm states. TreatMissingData, Period, MetricName, and
  Namespace are not applicable to composite alarms.

- NEVER assume an alarm with populated AlarmActions will actually notify.
  Always check ActionsEnabled first. A common deployment mistake is disabling
  actions during testing and forgetting to re-enable.

- NEVER classify an AnomalyDetection alarm as NO_ANOMALY. The presence of an
  ANOMALY_DETECTION_BAND expression means the detection strategy is anomaly-
  based — the alarm passes the detection-strategy dimension. Only flag
  mis-calibrated bands (stdev <= 1) as NO_ANOMALY.

- NEVER assume PutMetricAlarm will reject an invalid configuration.
  CloudWatch accepts DatapointsToAlarm > EvaluationPeriods, impossible
  thresholds, and Period/resolution mismatches without validation errors.
  The API's leniency is a known source of silent alarm failures.

- NEVER recommend more than 5 actions per category. AlarmActions, OKActions,
  and InsufficientDataActions each accept a maximum of 5 ARNs. The 6th ARN
  is silently dropped. If more notification targets are needed, use SNS
  fan-out (one SNS topic triggers multiple downstream subscriptions).

- NEVER overlook alarm state history. An alarm that has been in
  INSUFFICIENT_DATA for weeks is a dead alarm — it provides zero monitoring
  value. Check `describe-alarm-history` for the last state transition
  timestamp. An alarm that has never transitioned to ALARM may have a
  threshold so high that it will never fire.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (PutMetricAlarm, DeleteAlarms, DisableAlarmActions, EnableAlarmActions),
  the auditor MUST emit:
  `CONFIRM: About to <action> on alarm <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.
- **PutMetricAlarm overwrites the entire alarm configuration.** Unlike IAM
  policies (which support versioning), PutMetricAlarm replaces the alarm
  atomically — no diff, no rollback. Always snapshot the current config:
  `aws cloudwatch describe-alarms --alarm-names <name> --output json >
  /tmp/<name>-backup-$(date +%s).json` BEFORE any modification.
- When adding actions, verify the SNS topic / Lambda function / AutoScaling
  policy ARN exists and is in the same region. A non-existent ARN in
  AlarmActions causes the action to fail silently at fire time.
- When changing TreatMissingData, consider the impact on currently-breaching
  alarms. Changing from "missing" to "notBreaching" while the alarm is in
  INSUFFICIENT_DATA will immediately transition it to OK — potentially
  clearing an important state.
- For composite alarm Rule changes, validate the expression syntax before
  applying. CloudWatch accepts the Rule at PutMetricAlarm time but evaluates
  it only at the next evaluation cycle — a syntax error in the expression
  produces no immediate error.

## Remediation guidance

### For CONFIG_GAP — structural errors (Step 1)

1. **DatapointsToAlarm > EvaluationPeriods:** reduce DatapointsToAlarm to
   <= EvaluationPeriods, or increase EvaluationPeriods. Use DatapointsToAlarm
   = 1 and EvaluationPeriods = 1 for immediate response on critical alarms.
2. **Composite Rule references unknown alarm:** fix the alarm name in the Rule
   expression, or create the referenced alarm first.
3. **Period/metric mismatch:** align Period with the metric's native resolution.
   For 5-minute metrics, use Period >= 300.
4. **Impossible threshold:** recalculate the threshold based on actual metric
   data (use `aws cloudwatch get-metric-statistics` to sample the metric range).

### For NO_ACTION — missing notification wiring (Step 2)

1. **ActionsEnabled: false:** re-enable:
   `aws cloudwatch enable-alarm-actions --alarm-names <name>`
2. **Empty AlarmActions:** add an SNS topic:
   ```
   aws cloudwatch put-metric-alarm --alarm-name <name> \
     --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
   ```
3. **Composite alarm with no actions:** add an escalation SNS topic distinct
   from child alarm actions — the composite should notify a different tier
   (e.g., escalation SNS -> manager, vs. child alarm -> on-call engineer).
4. **Best practice:** configure both AlarmActions (breach notification) and
   InsufficientDataActions (missing-data alert) for production-critical alarms.

### For INSUFFICIENT_DATA — missing-data handling (Step 3)

1. **Set TreatMissingData explicitly:**
   - For availability metrics: `--treat-missing-data breaching` (missing =
     system down)
   - For error/count metrics: `--treat-missing-data notBreaching` (missing =
     zero errors)
   - For metrics with transient gaps: `--treat-missing-data ignore` (hold
     last state)
2. **Add InsufficientDataActions** so that a transition to INSUFFICIENT_DATA
   triggers a notification:
   ```
   aws cloudwatch put-metric-alarm --alarm-name <name> \
     --insufficient-data-actions arn:aws:sns:us-east-1:111111111111:monitoring-alerts
   ```
3. **For a stuck alarm:** check the metric is still publishing:
   `aws cloudwatch get-metric-statistics --namespace <ns> --metric-name <mn> \
   --start-time <iso> --end-time <iso> --period 300 --statistics Sum`
   If no datapoints return, the metric source (agent, service, custom app)
   has stopped reporting.

### For NO_ANOMALY — detection strategy gap (Step 4)

1. **Create an anomaly detector:**
   ```
   aws cloudwatch put-anomaly-detector \
     --namespace AWS/ApplicationELB \
     --metric-name TargetResponseTime \
     --stat Average \
     --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
     --config '{"MetricMathConfig":{"AnomalyDetectorConfiguration":{"Expression":"e1","Period":300,"Stat":"Average"}}}'
   ```
2. **Convert the alarm to use the anomaly band:**
   Replace the static ComparisonOperator + Threshold with a
   `GreaterThanUpperThreshold` evaluation against the
   `ANOMALY_DETECTION_BAND` expression output.
3. **For over-sensitive bands (stdev <= 1):** increase the standard deviation
   to 2 (moderate) or 3 (conservative). Higher stdev = wider band = fewer
   false positives but slower anomaly detection.

### For OK — no remediation required

1. Verify the alarm has recent state transitions (check `describe-alarm-history`).
   An alarm that has never fired may need threshold tuning.
2. Consider adding InsufficientDataActions as defense-in-depth even if
   TreatMissingData is correctly set.
3. For composite alarms, verify child alarms are also audited — a composite is
   only as reliable as its children.

## Deep reference: CloudWatch alarm evaluation internals

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — "Deep reference": evaluation pipeline (collect/evaluate/count/decide/act), evaluation lag, composite evaluation cadence.
Load when reasoning about detection latency.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — "Recent AWS features (2024-2026)": OTel native metrics, composite alarm improvements, metric math enhancements.
Load when auditing recently-migrated or OTel-based alarms.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive (10 non-obvious alarm behaviors), the expert edge-case catalog (M-of-N lag, MetricMath FILL, composite short-circuit, high-resolution costs, pagination, cross-account AccountId), CloudWatch evaluation internals, and recent AWS features (2024-2026).

## Domain

AWS CloudOps / CloudWatch Observability & Alarm Reliability.

## AWS documentation

- **Amazon CloudWatch User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- **CloudWatch Security** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/security.html
- **CloudWatch API Reference** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/
- **CloudWatch CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/
- **CloudWatch Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
