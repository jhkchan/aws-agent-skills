# End-to-end usage scenario: cloudwatch-alarm-auditor

A walkthrough showing the skill auditing a CloudWatch alarm that has both a
missing-actions gap (NO_ACTION) and a secondary insufficient-data risk,
demonstrating ordered classification, the first-match-wins logic, and the
per-verdict remediation workflow with CLI commands.

## Input (user prompt)

> Audit this CloudWatch alarm before we deploy it to production. It monitors
> our checkout service error rate.

```text
Alarm name: checkout-error-rate-prod
Alarm type: MetricAlarm
State: OK

Configuration:
  Namespace: App/CheckoutService
  MetricName: ErrorCount
  Dimensions: [{Name: Environment, Value: prod}]
  Statistic: Sum
  Period: 60
  EvaluationPeriods: 5
  DatapointsToAlarm: 3
  ComparisonOperator: GreaterThanThreshold
  Threshold: 50
  TreatMissingData: (not set)
  ActionsEnabled: true
  AlarmActions: []
  OKActions: []
  InsufficientDataActions: []
```

## Skill output

```text
ALARM: checkout-error-rate-prod
VERDICT: NO_ACTION
REASON: AlarmActions is empty — the alarm transitions to ALARM state but
takes no notification or auto-remediation action (Step 2b). TreatMissingData
is also unset, creating a secondary INSUFFICIENT_DATA risk on a custom error
metric that goes missing when no errors occur.
FINDINGS:
  - [CRITICAL] AlarmActions is empty — alarm fires into the void (Step 2b)
  - [HIGH] TreatMissingData unset (defaults to "missing") on a custom error
    metric with no InsufficientDataActions (Step 3a)
REMEDIATION:
  1. Add an SNS topic to AlarmActions:
     aws cloudwatch put-metric-alarm --alarm-name checkout-error-rate-prod \
       --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
  2. Set TreatMissingData to breaching (missing data = checkout service down):
     aws cloudwatch put-metric-alarm --alarm-name checkout-error-rate-prod \
       --treat-missing-data breaching
  3. Add InsufficientDataActions for defense-in-depth:
     aws cloudwatch put-metric-alarm --alarm-name checkout-error-rate-prod \
       --insufficient-data-actions arn:aws:sns:us-east-1:111111111111:monitoring-alerts
```

## What the skill caught that a generic assistant misses

1. **The verdict ordering: NO_ACTION wins over INSUFFICIENT_DATA.** The alarm
   has BOTH missing actions AND missing-data handling gaps. A generic assistant
   lists both issues without prioritization. The skill's ordered classification
   (Step 2 before Step 3) produces a single deterministic verdict: NO_ACTION,
   because a notification gap is a deterministic failure (the alarm WILL be
   useless when it fires), while the insufficient-data gap is conditional
   (depends on the metric going missing).

2. **TreatMissingData defaults to "missing" — not "notBreaching."** A generic
   assistant says "consider setting TreatMissingData." The skill explains that
   the default behavior enters INSUFFICIENT_DATA, which triggers
   InsufficientDataActions (empty), NOT AlarmActions — creating a silent blind
   spot when the checkout service stops emitting error metrics (e.g., during a
   crash where the metric agent also dies).

3. **The MetricMath FILL() trap context.** While not present in this alarm,
   the skill's expert knowledge flags that a FILL(0) on an error-count metric
   would mask the same blind spot differently — making the alarm look healthy
   when the metric stops reporting. The generic assistant does not have this
   context.

4. **Actionable CLI remediation.** The skill provides the exact
   `put-metric-alarm` commands to fix each finding, with the correct flags for
   adding actions and setting TreatMissingData.

## Slash-command invocation

```
/aws:audit-cloudwatch-alarm
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our checkout service error rate alarm before production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cloudwatch-alarm-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this CloudWatch alarm"
# [Phase: Audit | Skills routed: cloudwatch-alarm-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the alarm, validate the configuration:

```bash
# Verify actions were added
aws cloudwatch describe-alarms --alarm-names checkout-error-rate-prod \
  --profile default --output json | jq '.MetricAlarms[0].AlarmActions'

# Confirm TreatMissingData is set
aws cloudwatch describe-alarms --alarm-names checkout-error-rate-prod \
  --profile default --output json | jq '.MetricAlarms[0].TreatMissingData'

# Check recent state history for flapping or stuck states
aws cloudwatch describe-alarm-history \
  --alarm-name checkout-error-rate-prod \
  --history-item-type StateUpdate \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-05T00:00:00Z \
  --profile default --output json
```

Then monitor the alarm for 1-2 days to confirm it transitions correctly
between OK and ALARM states when the error rate changes.
