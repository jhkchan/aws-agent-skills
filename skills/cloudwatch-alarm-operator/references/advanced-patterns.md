# CloudWatch Alarm Operator — Advanced Patterns and Expert Knowledge

Deep-dive material moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Step 0: Expert knowledge — non-obvious CloudWatch alarm behaviors

- **TreatMissingData defaults to "missing" (NOT "notBreaching").** Unset = INSUFFICIENT_DATA on gaps. This is the #1 alarm blind spot.
- **INSUFFICIENT_DATA triggers InsufficientDataActions, NOT AlarmActions.** If that list is empty (common), the transition is silent — a monitoring black hole.
- **DatapointsToAlarm must be <= EvaluationPeriods.** If it exceeds, the condition can NEVER be satisfied. CloudWatch accepts without error.
- **ActionsEnabled: false is a global kill switch.** Suppresses ALL actions (SNS, Lambda, AutoScaling, EC2 recover). Often set during testing and forgotten.
- **PutMetricAlarm silently overwrites.** No version history, no diff, no rollback. Always snapshot first.
- **Composite Rule <= 512 chars, max 100 alarm references.** Evaluates every 60s fixed. `AND` requires both children in ALARM simultaneously — if child-a clears before child-b fires, composite never enters ALARM. Use `OR` for escalation; use `AND` with time-window awareness.
- **Composite actions ordering:** actions execute in order listed but are NOT deduplicated. Same SNS in child + composite = two notifications. Design composite actions as escalation (different on-call tier).
- **AnomalyDetection requires ~15 min warm-up.** New detector on metric with no history returns empty bands. Do NOT classify as broken during warm-up.
- **MetricMath FILL(m1, 0) masks missing data.** Prevents INSUFFICIENT_DATA but can cause false negatives (error-count filled with 0 looks healthy). Pair with a heartbeat alarm.
- **Alarm actions capped at 5 per category.** The 6th ARN is silently rejected. Use one SNS topic with multiple subscriptions for fan-out.
- **Period must be >= metric native resolution.** 5-min metric with Period=60 produces 4 empty windows out of 5.
- **High-resolution alarms (10s/30s Period) cost more.** Reserve for critical metrics (payment fraud, security).
- **Cross-account/cross-region alarms use AccountId in the Metrics array member**, not Dimensions. Wrong AccountId = silently monitors wrong account.
- **PutMetricAlarm for ANOMALY_DETECTION_BAND:** the Metrics array uses `Expression: ANOMALY_DETECTION_BAND(m1, stdev)` and ComparisonOperator becomes `GreaterThanUpperThreshold` / `LessThanLowerThreshold`.


## Recent AWS features (2024-2026)

- **CloudWatch Metric Explorer:** cross-account/region metric exploration without pre-configuring alarms.
- **Contributor Insights:** top-N contributors to a metric (e.g., top IPs driving 5xx errors).
- **Application Signals:** auto-discovered SLOs from CWAgent on EC2/ECS/EKS; alarms on burn rate instead of raw metrics.
- **OpenTelemetry native metrics:** alarms on OTel metrics may have different namespace/dimension structures.
- **Composite alarm improvements:** more complex boolean expressions, cross-region references.
- **Metric Streams:** real-time streaming to S3/third-party (Datadog, New Relic) — complementary to alarms.
- **Built-in anomaly detection:** some AWS consoles (RDS Performance Insights, Application Signals) ship pre-built anomaly detection.


