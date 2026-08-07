# End-to-end usage scenario: cloudwatch-alarm-operator

A walkthrough showing the skill creating a CPU alarm for a production
EC2 instance, building a composite rollup to reduce alarm fatigue, and
diagnosing an alarm stuck in INSUFFICIENT_DATA. Each path includes
pre-checks, CONFIRM gate, and post-verification — and is contrasted
with the BLOCKED case where pre-checks catch a problem.

## Input (user prompt)

> Create a CPU alarm on prod-web-1 that fires on-call-critical when
> CPU > 80% for 5 min. Then build a composite rollup of all three
> prod-checkout alarms. Then diagnose why api-error-rate-prod has
> been stuck in INSUFFICIENT_DATA for 6 days.

```json
{
  "Operation": "create",
  "Alarm name": "ec2-cpu-high-prod-web-1",
  "Namespace": "AWS/EC2",
  "Metric": "CPUUtilization",
  "Dimensions": {"InstanceId": "i-0123456789abcdef0"},
  "Statistic": "Average",
  "Period": 300,
  "EvaluationPeriods": 1,
  "DatapointsToAlarm": 1,
  "Threshold": 80,
  "ComparisonOperator": "GreaterThanThreshold",
  "AlarmActions": "arn:aws:sns:us-east-1:111111111111:on-call-critical",
  "OKActions": "arn:aws:sns:us-east-1:111111111111:on-call-info",
  "TreatMissingData": "notBreaching",
  "MetricChecks": {
    "get-metric-statistics": {"datapoints": 60, "Average": 45.2, "Maximum": 72.1},
    "sns.on-call-critical": {"subscriptions": 3},
    "sns.on-call-info": {"subscriptions": 8}
  }
}
```

## Skill output — create

```text
OPERATION: create
VERDICT: READY
TARGET: ec2-cpu-high-prod-web-1
PRE_CHECKS:
  - [PASS] Namespace AWS/EC2, MetricName CPUUtilization valid
  - [PASS] Dimensions InstanceId=i-0123456789abcdef0 returns 60 datapoints
    (Average ~45%, Maximum 72%) over the last hour
  - [PASS] Period 300 >= metric native 60s (detailed monitoring)
  - [PASS] DatapointsToAlarm 1 <= EvaluationPeriods 1
  - [PASS] Threshold 80 achievable (current max ~72%)
  - [PASS] Statistic Average matches utilization semantics
  - [PASS] AlarmActions SNS arn:aws:sns:us-east-1:111111111111:on-call-critical
    exists with 3 subscriptions
  - [PASS] OKActions SNS arn:aws:sns:us-east-1:111111111111:on-call-info
    exists with 8 subscriptions
  - [PASS] 2 ARNs total <= 5 per category
  - [PASS] TreatMissingData notBreaching explicit (CPU gap = instance
    stopped = not a CPU problem)
STEPS:
  1. CONFIRM: About to put-metric-alarm ec2-cpu-high-prod-web-1 in
     account 111111111111 region us-east-1. This will CREATE a new
     alarm that fires on-call-critical when CPU > 80% for 5 min.
     Estimated detection lag: ~5-10 min from first breach. Proceed?
     (yes/no)
  2. aws cloudwatch put-metric-alarm --alarm-name ec2-cpu-high-prod-web-1 \
       --alarm-description "CPU > 80% for 5 min. Runbook: https://runbooks.example.com/high-cpu" \
       --namespace AWS/EC2 --metric-name CPUUtilization \
       --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
       --statistic Average --period 300 --evaluation-periods 1 \
       --threshold 80 --comparison-operator GreaterThanThreshold \
       --treat-missing-data notBreaching \
       --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical \
       --ok-actions arn:aws:sns:us-east-1:111111111111:on-call-info
POST_VERIFY:
  - (pending execution)
  - describe-alarms returns the alarm with StateValue INSUFFICIENT_DATA
    (initial) transitioning to OK after the first evaluation cycle (~5 min)
STATE: (pending — INSUFFICIENT_DATA for the first ~5 min, then OK)
NOTES:
  - Detection lag: Period(300) * DatapointsToAlarm(1) = 5 min from
    first breach to ALARM transition.
  - TreatMissingData notBreaching: if the instance stops and CPU
    metrics stop, the alarm stays in OK (correct — stopped instance
    is not a CPU problem). Set to breaching only if missing CPU data
    itself indicates a problem.
  - No InsufficientDataActions configured — if you want to be alerted
    when the metric goes missing entirely, add an InsufficientDataActions
    SNS target as defense-in-depth.
```

## Skill output — composite

```text
OPERATION: composite
VERDICT: READY
TARGET: prod-checkout-critical-rollup
PRE_CHECKS:
  - [PASS] Child alarm alb-error-ratio-prod exists, StateValue OK
  - [PASS] Child alarm alb-latency-anomaly-prod exists, StateValue OK
  - [PASS] Child alarm lambda-errors-high-prod-checkout exists,
    StateValue OK
  - [PASS] Rule length 91 chars <= 512 cap
  - [PASS] 3 alarm references <= 100 cap
  - [PASS] AlarmActions SNS on-call-escalation exists with 2
    subscriptions (ESCALATION target, distinct from child alarm
    on-call-critical)
STEPS:
  1. CONFIRM: About to put-composite-alarm prod-checkout-critical-rollup
     in account 111111111111 region us-east-1. This will CREATE a new
     composite alarm that fires on-call-escalation when ANY of the 3
     child alarms enters ALARM state. Composite evaluates every 60s
     on top of child detection latency. Proceed? (yes/no)
  2. aws cloudwatch put-composite-alarm --actions-enabled \
       --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-escalation \
       --alarm-name prod-checkout-critical-rollup \
       --alarm-description "Escalation: any of {5xx, latency, lambda errors}" \
       --alarm-rule "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)"
POST_VERIFY:
  - (pending execution)
  - describe-alarms returns the composite with StateValue INSUFFICIENT_DATA
    (initial — composite needs the first 60s evaluation cycle to derive
    state from children)
STATE: (pending — INSUFFICIENT_DATA for ~60s, then OK since all children
  are OK)
NOTES:
  - Use OR for escalation (any child triggers the composite). AND would
    require ALL children to be in ALARM simultaneously — fragile if
    child alarms have different detection latencies.
  - The composite's on-call-escalation is a DIFFERENT SNS topic than
    the child alarms' on-call-critical. This is intentional — composite
    actions should be escalation (manager, incident channel), not
    duplication.
  - Composite does NOT auto-aggregate child alarm actions. Each child
    still notifies its own actions independently. The composite adds
    a rollup signal on top.
```

## Skill output — diagnose (BLOCKED on stale dimension)

```text
OPERATION: diagnose
VERDICT: BLOCKED
TARGET: api-error-rate-prod
PRE_CHECKS:
  - [PASS] describe-alarms returns the alarm
  - [FAIL] Metric not publishing: get-metric-statistics on
    AWS/ApplicationELB, HTTPCode_ELB_5XX_Count, dimensions
    LoadBalancer=app/prod-alb/abc-def-OLD returns 0 datapoints over
    the last 1 hour. The current ALB ARN is app/prod-alb/1234567890
    (the alarm references a deleted ALB).
  - [PASS] describe-alarm-history shows the alarm entered
    INSUFFICIENT_DATA 6 days ago (2026-08-01T14:30:00Z) and has not
    transitioned since
  - [PASS] ActionsEnabled is true, AlarmActions is populated — the
    alarm config is healthy EXCEPT for the stale dimension
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: INSUFFICIENT_DATA (stuck 6 days)
NOTES:
  - Root cause: the LoadBalancer dimension value app/prod-alb/abc-def-OLD
    references a deleted ALB. The current ALB is app/prod-alb/1234567890.
  - Secondary issue: TreatMissingData is "missing" (the default). If
    this had been set to "breaching", the alarm would have fired on
    day 1 when the metric went missing, alerting on-call to the ALB
    replacement.
  - Remediation (in two steps):
    1. Snapshot the existing config:
       aws cloudwatch describe-alarms --alarm-names api-error-rate-prod \
         --output json > /tmp/api-error-rate-prod-backup-$(date +%s).json
    2. Update the dimension value AND set TreatMissingData:
       aws cloudwatch put-metric-alarm --alarm-name api-error-rate-prod \
         --namespace AWS/ApplicationELB \
         --metric-name HTTPCode_ELB_5XX_Count \
         --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
         --statistic Sum --period 60 \
         --evaluation-periods 5 --datapoints-to-alarm 3 \
         --threshold 10 --comparison-operator GreaterThanThreshold \
         --treat-missing-data breaching \
         --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
  - Verify the new ALB is publishing:
    aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
      --metric-name HTTPCode_ELB_5XX_Count \
      --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
      --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
      --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
      --period 60 --statistics Sum
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the put-metric-alarm command directly. The skill runs 10
   deterministic pre-checks and confirms the metric is actually
   publishing, the SNS topic exists, the threshold is achievable, and
   TreatMissingData is explicitly set.

2. **TreatMissingData default trap.** A generic assistant leaves
   TreatMissingData unset (defaults to "missing"). The skill forces
   an explicit choice — notBreaching for utilization metrics (CPU gap
   = stopped instance = not a CPU problem), breaching for availability
   metrics (missing metric = system down).

3. **M-of-N detection lag.** A generic assistant omits that
   Period(300) * DatapointsToAlarm(1) = 5 min from first breach to
   ALARM transition. The skill surfaces this in the STEPS so the
   operator knows what latency to expect.

4. **Composite escalation vs. duplication.** A generic assistant
   creates the composite with the same SNS topic as the child alarms.
   The skill requires the composite to have an ESCALATION action
   distinct from child alarm actions — otherwise the composite adds
   zero notification value (subscribers get two notifications for
   the same event).

5. **Dimension mismatch root cause.** A generic assistant suggests
   "check the CloudWatch console" for the INSUFFICIENT_DATA diagnosis.
   The skill pinpoints the exact dimension value that's stale
   (`app/prod-alb/abc-def-OLD` vs current `app/prod-alb/1234567890`),
   runs get-metric-statistics to prove the metric is not publishing,
   and surfaces the secondary TreatMissingData issue.

6. **Composite does NOT auto-aggregate.** A generic assistant implies
   the composite will silence child alarms. The skill clarifies that
   each child still notifies independently — the composite adds a
   rollup signal on top.

7. **CONFIRM gate.** A generic assistant auto-executes. The skill
   emits `CONFIRM:` and waits — PutMetricAlarm silently overwrites
   any existing alarm config with no version history.

8. **Snapshot before modify.** A generic assistant updates in place.
   The skill snapshots via `describe-alarms --output json` first,
   because PutMetricAlarm has no diff or rollback path.

## Slash-command invocation

```
/aws:operate-cloudwatch-alarm
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a CPU alarm on prod-web-1 at 80% for 5 min"
```

The orchestrator emits
`[Phase: Operate | Skills routed: cloudwatch-alarm-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create CloudWatch alarm CPU on prod-web-1"
# [Phase: Operate | Skills routed: cloudwatch-alarm-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the alarms are applied:

```bash
# Verify the CPU alarm is in OK state after the first evaluation cycle
aws cloudwatch describe-alarms --alarm-names ec2-cpu-high-prod-web-1 \
  --profile default \
  --query 'MetricAlarms[0].{State:StateValue,TMD:TreatMissingData,Actions:ActionsEnabled}' \
  --output json

# Trigger a synthetic breach (test only)
aws cloudwatch put-metric-data \
  --namespace AWS/EC2 \
  --metric-data MetricName=CPUUtilization,Dimensions=[{Name=InstanceId,Value=i-0123456789abcdef0}],Value=95,Timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --profile default
# Wait 5-10 min, then verify the alarm transitioned to ALARM and SNS delivered

# Verify the composite derived state from children correctly
aws cloudwatch describe-alarms --alarm-names prod-checkout-critical-rollup \
  --profile default \
  --query 'CompositeAlarms[0].{State:StateValue,Rule:AlarmRule,Actions:AlarmActions}'
```
