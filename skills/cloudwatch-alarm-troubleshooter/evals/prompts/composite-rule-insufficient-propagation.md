# Eval prompt: composite-rule-insufficient-propagation

Diagnose the CloudWatch alarm issue for the following composite alarm.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `PaymentServiceDegradation` composite alarm stays in OK
even though one of its child alarms (`HighErrorRate`) has been in
ALARM for 30 minutes. The operator intended the composite to fire
when EITHER child is in ALARM.

```text
AlarmName: PaymentServiceDegradation
StateValue: OK
AlarmRule: ALARM(HighErrorRate) AND ALARM(HighLatency)
AlarmActions: [arn:aws:sns:us-east-1:111111111111:OpsPager]

Child alarms (describe-alarms):
  - HighErrorRate: StateValue ALARM (last 30 minutes)
  - HighLatency:   StateValue INSUFFICIENT_DATA (last 30 minutes;
    the latency metric source stopped emitting 2 hours ago)

Operator's stated intent: "page the on-call when either the error
rate OR the latency spikes."
```

The composite has one child in ALARM but does not fire. Identify why
the composite rule does not match the operator's intent.
