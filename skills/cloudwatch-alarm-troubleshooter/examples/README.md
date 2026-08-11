# Example usage: cloudwatch-alarm-troubleshooter

A walkthrough showing the skill diagnosing an alarm stuck in
INSUFFICIENT_DATA due to a dimension case mismatch, demonstrating the
dimension-exactness heuristic, the symptom-to-layer triage, the
evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the alarm-side
fix.

## Input (user prompt)

> Our HighErrorRateAlarm has been in INSUFFICIENT_DATA for 3 days.
> The Lambda function fn-orders-api is clearly emitting Errors — we
> can see them on the dashboard. We've been debugging the metric
> pipeline and can't figure out why the alarm won't evaluate.

```text
AlarmName: HighErrorRateAlarm
StateValue: INSUFFICIENT_DATA
Namespace: AWS/Lambda
MetricName: Errors
Dimensions: [{Name: FunctionName, Value: Fn-Orders-API}]
Period: 300
Statistic: Sum
Threshold: 5
ComparisonOperator: GreaterThanThreshold
EvaluationPeriods: 1
DatapointsToAlarm: 1
TreatMissingData: missing

Metric evidence: dashboard (dimensionless query on AWS/Lambda Errors)
shows non-zero values for fn-orders-api every 5 minutes for 24 hours.

list-metrics output for AWS/Lambda Errors includes:
  {Namespace: AWS/Lambda, MetricName: Errors,
   Dimensions: [{Name: FunctionName, Value: fn-orders-api}]}

get-metric-data with the alarm's exact dimension
(FunctionName=Fn-Orders-API) returns Values: [].
get-metric-data with the corrected dimension
(FunctionName=fn-orders-api) returns Values: [3, 1, 0, 7, 2].
```

## Skill output

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
    native 60s resolution (5x multiple); Statistic Sum is valid.
REMEDIATION:
  1. Update the alarm with the corrected dimension value:
     aws cloudwatch put-metric-alarm --alarm-name HighErrorRateAlarm \
       --namespace AWS/Lambda --metric-name Errors \
       --dimensions Name=FunctionName,Value=fn-orders-api \
       --period 300 --statistic Sum --threshold 5 \
       --comparison-operator GreaterThanThreshold \
       --evaluation-periods 1 --profile <p>
  2. Verify the alarm transitions out of INSUFFICIENT_DATA within
     one evaluation period (5 minutes):
     aws cloudwatch describe-alarms --alarm-names HighErrorRateAlarm \
       --query 'MetricAlarms[0].StateValue'
CONFIRM: Before updating the alarm, emit and await:
  "CONFIRM: About to update HighErrorRateAlarm dimension from
   Fn-Orders-API to fn-orders-api. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Distinguished dimension mismatch from metric-pipeline failure.**
   A generic assistant assumes "the metric isn't being emitted" and
   tells the operator to check the Lambda function. The skill
   cross-references `list-metrics` output against the alarm's
   dimension value and identifies the case mismatch character-by-
   character — the metric exists, the alarm query is wrong.

2. **Used the dimensionless query as the control.** The skill probes
   with both the alarm's exact (scoped) query AND a dimensionless
   query. The scoped query returns nothing; the dimensionless query
   returns points. That positive / negative pair isolates the
   dimension as the failure surface.

3. **Ruled out the other INSUFFICIENT_DATA layers with positive
   evidence.** The skill's EVIDENCE block notes that the namespace
   `AWS/Lambda` is correct (not a typo), the Period 300 is a multiple
   of the 60s native resolution (not misaligned), and the Statistic
   Sum is valid. A generic assistant would not have ruled these out.

4. **Recommended the alarm-side fix, not a metric-pipeline
   investigation.** The remediation is `put-metric-alarm` with the
   corrected dimension value, not a deep-dive into why the Lambda
   function's Errors metric "isn't reaching CloudWatch."

## Slash-command invocation

```
/aws:troubleshoot-cloudwatch-alarm
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why HighErrorRateAlarm is stuck in INSUFFICIENT_DATA"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: cloudwatch-alarm-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the alarm transitions out of
INSUFFICIENT_DATA:

```bash
# Verify the alarm is now evaluating (should be OK or ALARM, not
# INSUFFICIENT_DATA)
aws cloudwatch describe-alarms --alarm-names HighErrorRateAlarm \
  --query 'MetricAlarms[0].StateValue' --profile default

# Confirm the metric points exist at the alarm's resolution
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"q1","MetricStat":{"Metric":{"Namespace":"AWS/Lambda","MetricName":"Errors","Dimensions":[{"Name":"FunctionName","Value":"fn-orders-api"}]},"Period":300,"Stat":"Sum"}}]' \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --profile default --output json
```

Then monitor the alarm state for 1-2 hours to confirm it transitions
to ALARM when the error rate exceeds the threshold.
