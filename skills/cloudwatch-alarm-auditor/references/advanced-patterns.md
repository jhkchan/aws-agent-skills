# CloudWatch Alarm Auditor — Advanced Patterns and Expert Knowledge

Deep-dive material moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Step 0: Expert knowledge — non-obvious CloudWatch alarm behaviors

These behaviors are easy to misjudge without operational CloudWatch experience.
Each changes a verdict if ignored:

- **TreatMissingData defaults to "missing" — NOT "notBreaching".** If unset,
  the alarm enters INSUFFICIENT_DATA when no datapoints arrive during the
  evaluation window. This is the single most common alarm blind spot: operators
  assume missing data means "no problem" but the alarm actually goes dark. The
  API field `TreatMissingData` must be explicitly set to `breaching`,
  `notBreaching`, or `ignore` to control behavior.

- **INSUFFICIENT_DATA triggers InsufficientDataActions, NOT AlarmActions.**
  When an alarm enters the INSUFFICIENT_DATA state, it fires only the actions
  in `InsufficientDataActions` — never `AlarmActions`. If
  InsufficientDataActions is empty (the common case), the transition is
  silent. This is why an alarm that enters INSUFFICIENT_DATA is a monitoring
  black hole.

- **DatapointsToAlarm must be <= EvaluationPeriods.** This is the M-of-N
  pattern: `DatapointsToAlarm=2, EvaluationPeriods=5` means the alarm fires
  when 2 of the last 5 evaluation windows are breaching. If DatapointsToAlarm
  exceeds EvaluationPeriods, the condition can **never** be satisfied — the
  alarm is permanently non-functional. CloudWatch accepts this config at
  PutMetricAlarm time without validation error (a known API quirk).

- **ActionsEnabled: false is a global kill switch.** Even if AlarmActions lists
  five SNS topics, a Lambda function, and three AutoScaling policies, setting
  ActionsEnabled to false suppresses ALL of them. This flag is often set
  during testing and forgotten. Checking AlarmActions alone is insufficient —
  always check ActionsEnabled first.

- **PutMetricAlarm silently overwrites existing alarms.** Alarm names must be
  unique within an account+region, but PutMetricAlarm does NOT error on
  duplicate names — it replaces the entire configuration atomically. A
  deployment that recreates an alarm with different (possibly degraded)
  settings has no audit trail in the alarm config itself. Only CloudTrail
  `PutMetricAlarm` events reveal the change.

- **Composite alarm Rule expression is limited to 512 characters** and can
  reference up to 100 other alarms. A Rule near the 512-char limit may be
  correct but fragile — a minor logic change can exceed the limit and fail
  silently on update.

- **AnomalyDetection requires ~15 minutes of metric history** before producing
  valid bands. A newly created anomaly detector on a metric with no history
  returns empty bands — the alarm will not fire until enough data accumulates.
  Do NOT classify a new anomaly-detection alarm as broken during this warm-up
  window.

- **MetricMath FILL() can mask missing data.** When an alarm uses a MetricMath
  expression with `FILL(m1, 0)`, missing datapoints are replaced with 0. This
  prevents INSUFFICIENT_DATA but can cause false negatives — an error-count
  metric filled with 0 looks healthy when the metric simply stopped reporting.
  Always inspect FILL() usage in the expression.

- **Alarm actions are capped at 5 per category.** AlarmActions, OKActions, and
  InsufficientDataActions each accept a maximum of 5 ARNs. The 6th is silently
  rejected. When listing many SNS topics or Lambda functions, verify the count.

- **Period must be >= the metric's native resolution.** A metric published
  every 5 minutes evaluated with Period=60 produces mostly empty windows. The
  alarm should use a Period >= the publishing interval. For AWS services, the
  native resolution is typically 1 minute (detailed monitoring) or 5 minutes
  (basic monitoring).

- **High-resolution alarms (10s or 30s Period) cost more.** Standard alarms
  evaluate at 60-second resolution at no extra charge. High-resolution alarms
  evaluate at 10 or 30 seconds and incur a higher per-alarm monthly cost.
  Flag high-resolution alarms that monitor low-urgency metrics — the cost may
  not justify the faster evaluation.


## Expert edge cases

These patterns represent genuine, non-obvious CloudWatch alarm pitfalls that a
senior site-reliability engineer would catch but a generalist would miss.

### The "M-of-N" evaluation lag trap

An alarm with `DatapointsToAlarm=3, EvaluationPeriods=5, Period=300` requires
3 breaching datapoints out of 5 five-minute windows. The alarm cannot fire
until at least 3 evaluation windows have completed — a minimum 15-minute delay
from the first breach. Operators often expect 1-minute alarm latency but the
M-of-N config introduces a multi-period delay. For critical alarms (availability,
security), prefer `DatapointsToAlarm=1, EvaluationPeriods=1` for immediate
response. The trade-off: 1-of-1 increases false positives from transient spikes.

### MetricMath FILL() and false negatives

A MetricMath expression like `e1 = m1 + m2` with `FILL(m1, 0)` replaces missing
datapoints with 0. For error-count or failure metrics, FILL(0) makes the alarm
look healthy when the metric simply stopped reporting (sensor failure, agent
crash, instance termination). Always pair FILL() with a secondary "heartbeat"
alarm that detects the metric itself going missing. The FILL value should be
contextually correct: FILL with 0 for counters, FILL with REPEAT for gauges.

### Composite alarm short-circuit evaluation

The composite alarm Rule expression evaluates child alarm states. `ALARM(child-a)
AND ALARM(child-b)` requires BOTH children to be in ALARM state simultaneously.
If child-a fires and clears before child-b fires, the composite never enters
ALARM. This is a timing hazard — use `ALARM(child-a) OR ALARM(child-b)` for
escalation (either child triggers the composite) or add time-window awareness
via the child alarm's EvaluationPeriods.

### Alarm actions ordering and deduplication

CloudWatch executes AlarmActions in the order listed, but does NOT deduplicate.
If the same SNS topic appears in both a child alarm's AlarmActions and the
composite alarm's AlarmActions, the subscriber receives two notifications for
the same event. Design composite alarm actions as escalation (different SNS
topic, different on-call tier) rather than duplication.

### High-resolution alarm cost trap

High-resolution alarms (Period=10 or Period=30) incur a higher per-alarm
monthly charge than standard alarms (Period=60). For a fleet of 100 alarms,
the cost difference is material. Reserve high-resolution for critical
metrics where 60-second latency is unacceptable (payment fraud, security
anomalies). Use standard resolution for operational metrics (CPU, memory,
queue depth).

### DescribeAlarmHistory pagination

`describe-alarm-history` returns at most 100 records per call. For an alarm
with frequent state transitions (flapping), a single 24-hour window may span
multiple pages. Always drain `NextToken` to get the complete history. A flapping
alarm (transitions between ALARM and OK more than 5 times per hour) indicates
either a threshold set exactly at the metric's average value or a metric with
extreme variance — both warrant threshold recalibration.

### Anomaly detection warm-up window

A new AnomalyDetection configuration requires approximately 15 minutes of
metric history before the model produces valid bands. During this warm-up
window, the alarm evaluates against empty bands and may behave unpredictably.
Do not classify a new anomaly-detection alarm as broken during warm-up —
note the warm-up period and recommend re-checking after 30 minutes.

### Cross-account metric alarm dimension quirk

When monitoring metrics from linked accounts (AWS Organizations
CloudWatch cross-account observability), the metric's account ID is embedded
in the `AccountId` dimension field, not in the Dimensions array. An alarm
configured with the wrong AccountId will silently monitor the wrong account
(or find no data). Always verify the AccountId matches the intended source.


## Deep reference: CloudWatch alarm evaluation internals

### Evaluation pipeline

CloudWatch evaluates a metric alarm in this order:
1. **Collect** — gather metric datapoints for the last `EvaluationPeriods *
   Period` seconds.
2. **Evaluate** — for each Period window, compare the aggregated statistic
   (Sum, Average, etc.) against the Threshold using the ComparisonOperator.
3. **Count** — count how many of the EvaluationPeriods windows are breaching.
4. **Decide** — if breaching count >= DatapointsToAlarm, transition to ALARM.
   If breaching count == 0, transition to OK. Otherwise, hold current state.
5. **Act** — execute AlarmActions (ALARM), OKActions (OK), or
   InsufficientDataActions (INSUFFICIENT_DATA).

### Evaluation lag

The evaluation cycle runs every Period seconds. A standard alarm (Period=300)
evaluates every 5 minutes. The first evaluation after a breach may be delayed
by up to one Period. Combined with M-of-N (DatapointsToAlarm < EvaluationPeriods),
the total detection latency can be `Period * DatapointsToAlarm` seconds.

### Composite alarm evaluation

Composite alarms evaluate their Rule expression every 60 seconds (fixed,
regardless of any child alarm Period). The expression resolves each
`ALARM(name)` reference to the child alarm's current StateValue. Boolean
operators (AND, OR, NOT) combine the results. The composite then follows the
same Act step as metric alarms.


## Recent AWS features (2024-2026)

- **OpenTelemetry native metrics (2024):** CloudWatch now ingests OpenTelemetry-format metrics natively. Alarms built on OTel metrics may have different namespace and dimension structures. Auditors should verify that alarms on OTel metrics use correct namespace/dimension mappings.
- **Composite alarm improvements (2024):** Composite alarms now support more complex boolean expressions and can reference alarms across regions. Auditors should verify that composite alarm rules are not overly complex (cascading alarm dependencies can create silent blind spots if one component is deleted).
- **Metric math enhancements:** Additional statistical functions and period support. No new audit-surface fields, but auditors should verify that alarms using metric math are not silently broken by dimension changes.


