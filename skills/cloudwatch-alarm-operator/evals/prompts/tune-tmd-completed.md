# Eval prompt: tune-tmd-completed

Post-verification of a TreatMissingData tune operation. Emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, STATE, NOTES) in post-verification form.

Operation: tune (post-verification after execution)
Alarm name: prod-alb-availability
Change: TreatMissingData missing -> breaching
Reason: ALB stopped publishing due to a VPC route table issue; the
  alarm should fire when the metric goes missing rather than going
  dark.

```json
{
  "PreTuneSnapshot": {
    "TreatMissingData": "missing",
    "StateValue": "INSUFFICIENT_DATA",
    "StateUpdatedTimestamp": "2026-08-07T08:00:00Z"
  },
  "ExecutedCLI": [
    "aws cloudwatch describe-alarms --alarm-names prod-alb-availability --output json > /tmp/prod-alb-availability-backup-2026-08-07.json",
    "aws cloudwatch put-metric-alarm --alarm-name prod-alb-availability --treat-missing-data breaching [rest of config preserved]"
  ],
  "PostExecutionChecks": {
    "describe-alarms.prod-alb-availability": {
      "TreatMissingData": "breaching",
      "StateValue": "ALARM",
      "ActionsEnabled": true,
      "AlarmActions": ["arn:aws:sns:us-east-1:111111111111:on-call-critical"]
    },
    "sns.list-subscriptions-by-topic.on-call-critical": {
      "subscriptions_confirmed": 3
    },
    "OperatorConfirmation": "On-call confirmed receiving the page within 60s of state transition"
  }
}
```
