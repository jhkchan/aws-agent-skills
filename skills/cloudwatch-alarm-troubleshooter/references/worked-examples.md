# CloudWatch Alarm Troubleshooter — Worked Examples

Worked examples moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Worked example — ALARM fires, SNS topic policy missing

```text
TARGET: ProductionDiskSpaceAlarm
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Alarm has transitioned to ALARM 4 times in 24 hours (visible
  in describe-alarm-history StateHistory), but the SNS topic policy
  on the AlarmActions target does not grant cloudwatch.amazonaws.com
  permission to call sns:Publish. No notifications were delivered
  (Step 4a).
LAYER: ACTION_SNS_POLICY
EVIDENCE:
  - Symptom: alarm fires (visible on dashboard, ALARM confirmed), but
    the on-call Slack channel received nothing.
  - Probe: aws cloudwatch describe-alarms returns AlarmActions:
    [arn:aws:sns:us-east-1:111111111111:OpsNotifications].
  - Probe: aws cloudwatch describe-alarm-history --history-type Action
    returns no Action entries in the last 24 hours despite 4 ALARM
    transitions in StateHistory.
  - Probe: aws sns get-topic-attributes on OpsNotifications returns
    a Policy with NO statement granting cloudwatch.amazonaws.com
    sns:Publish.
  - Passing: the SNS topic works (CLI test publish delivers to the
    Slack subscription); the Lambda subscription is Confirmed.
REMEDIATION:
  1. Add the CloudWatch service principal to the SNS topic policy:
     aws sns add-permission --topic-arn \
       arn:aws:sns:us-east-1:111111111111:OpsNotifications \
       --label AllowCloudWatchAlarmPublish \
       --aws-account-id 111111111111 \
       --action-name Publish --profile <p>
  2. Verify by triggering a test alarm transition (set threshold to 0
     momentarily) and confirm Slack receives the notification within
     60 seconds. Then restore the original threshold.
CONFIRM: Before updating the topic policy, emit and await:
  "CONFIRM: About to add cloudwatch.amazonaws.com sns:Publish to
   OpsNotifications topic. Proceed? (yes/no)"
```

