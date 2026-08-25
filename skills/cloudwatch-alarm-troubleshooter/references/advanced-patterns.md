# CloudWatch Alarm Troubleshooter — Advanced Patterns

Deep-dive material moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Expert heuristic (moved deep dives)

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

4. **The evaluation window is `Period * EvaluationPeriods`, but
   `DatapointsToAlarm` can be less than `EvaluationPeriods`.** An
   alarm with `Period: 300, EvaluationPeriods: 5, DatapointsToAlarm: 3`
   evaluates the last 25 minutes (5 * 300s) and transitions to ALARM
   if ANY 3 of the 5 data points breach the threshold. The remaining
   2 data points can be non-breaching or missing. This "M-of-N" logic
   is the #1 cause of "alarm fired but the dashboard looks fine" —
   the operator sees 3 green periods and 2 red periods and expects
   the alarm to stay OK, but M=3 is sufficient. Always check
   `DatapointsToAlarm` alongside `EvaluationPeriods`.

5. **Composite alarm Rule evaluation short-circuits on the first
   false child under AND, and the first true child under OR.**
   `ALARM(c1) AND ALARM(c2) AND ALARM(c3)` — if c1 is OK, CloudWatch
   does not evaluate c2 or c3. This is unobservable in the console
   (all children show their current state) but means a recently-fixed
   child (c1 transitions to OK) instantly de-escalates the composite
   even if c2 and c3 are still ALARM. Under OR, the first ALARM child
   short-circuits to true. This matters for incident routing: a
   composite alarm may resolve faster than the individual child
   alarms suggest.

6. **The anomaly detection band is computed as `mean(history) +/-
   (stddev(history) * StandardDeviations)`, but the history window
   is a rolling ~15 days, not the alarm's evaluation period.** The
   band updates continuously as new data arrives. A sudden but
   sustained shift (e.g., traffic doubles and stays elevated for 5
   days) causes the band to widen over time until the new baseline
   is "normal" — the alarm stops firing even though the metric is
   still elevated vs. the original baseline. The band is also
   per-period: a metric with daily seasonality will have a wider
   band during peak hours and a narrower band off-peak, causing
   inconsistent alerting behavior across the day.

7. **New custom metrics cause INSUFFICIENT_DATA for the first
   `EvaluationPeriods * Period` seconds, not a fixed 15 minutes.**
   A freshly-created alarm on a new metric stays in
   INSUFFICIENT_DATA until enough data points exist to fill the
   evaluation window. For `Period: 300, EvaluationPeriods: 1`, that
   is 5 minutes. For `Period: 300, EvaluationPeriods: 5`, that is
   25 minutes. The 15-minute figure in AWS docs refers to the
   anomaly detector training window, not the alarm evaluation
   window. Operators who "just deployed the alarm" and see
   INSUFFICIENT_DATA for 25 minutes think the metric pipeline is
   broken; it is just the evaluation window filling up.

8. **Cross-account alarm actions require the SNS topic policy to
   trust the CloudWatch service principal in the ALARM's account,
   not the SNS topic's account.** When an alarm in account A
   publishes to an SNS topic in account B, the topic policy in B
   must allow `Principal: {Service: cloudwatch.amazonaws.com}` with
   a condition `aws:SourceAccount: <account-A>`. Without the
   `SourceAccount` condition, the publish may succeed but be
   rejected by some downstream subscriptions. Cross-account Lambda
   actions require `--source-arn <alarm-arn-in-account-A>` on the
   `lambda:add-permission` call in account B. This IAM gotcha is
   not surfaced in the alarm setup wizard.

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

## Step 0: Non-obvious behaviours that change diagnosis

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

## Recent AWS features (2024-2026)

- **DatapointsToAlarm M-of-N evaluation (2024-2025):** Alarms now
  support `DatapointsToAlarm` < `EvaluationPeriods`, enabling
  "breach M out of N periods" logic. A common source of "alarm fired
  but dashboard looks fine" — 3 of 5 periods breaching is sufficient.
- **Cross-account alarm actions with SourceAccount condition (2025):**
  SNS topic policies for cross-account alarm publishing now support
  `aws:SourceAccount` condition to scope the CloudWatch principal to
  the alarm's owning account. Required for secure cross-account
  alarm-to-SNS routing.
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

