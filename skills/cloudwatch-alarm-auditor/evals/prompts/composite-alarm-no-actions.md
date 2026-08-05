# Eval prompt: composite-alarm-no-actions

Audit the following CloudWatch alarm configuration for blind spots. Emit the
standard VERDICT block (ALARM, VERDICT, REASON, FINDINGS, REMEDIATION).

Alarm name: composite-alarm-no-actions
Alarm type: CompositeAlarm
State: OK

Configuration:
  Rule: ALARM(high-cpu-prod) OR ALARM(high-memory-prod)
  ActionsEnabled: true
  AlarmActions: []
  OKActions: []
  InsufficientDataActions: []

Child alarms referenced:
  - high-cpu-prod (exists, has AlarmActions configured)
  - high-memory-prod (exists, has AlarmActions configured)
