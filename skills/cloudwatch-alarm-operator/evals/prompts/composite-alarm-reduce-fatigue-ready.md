# Eval prompt: composite-alarm-reduce-fatigue-ready

Plan the following composite alarm creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, STATE, NOTES).

Operation: composite
Composite alarm name: prod-checkout-critical-rollup
Rule: ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)
AlarmActions: arn:aws:sns:us-east-1:111111111111:on-call-escalation
TreatMissingData: notBreaching

```json
{
  "ChildAlarmChecks": {
    "describe-alarms.alb-error-ratio-prod": {"StateValue": "OK"},
    "describe-alarms.alb-latency-anomaly-prod": {"StateValue": "OK"},
    "describe-alarms.lambda-errors-high-prod-checkout": {"StateValue": "OK"}
  },
  "ActionTargetChecks": {
    "sns.get-topic-attributes.on-call-escalation": {
      "status": "OK",
      "subscriptions": 2
    }
  },
  "RuleMetadata": {
    "rule_length_chars": 91,
    "alarm_references": 3,
    "distinct_child_actions": [
      "arn:aws:sns:us-east-1:111111111111:on-call-critical",
      "arn:aws:sns:us-east-1:111111111111:on-call-critical",
      "arn:aws:sns:us-east-1:111111111111:on-call-critical"
    ]
  }
}
```
