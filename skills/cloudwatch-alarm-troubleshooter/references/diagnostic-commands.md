# CloudWatch Alarm Troubleshooter — Diagnostic and Remediation Commands

Command listings moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Account-wide pre-flight commands

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

## Remediation guidance (per-layer fix commands)

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

