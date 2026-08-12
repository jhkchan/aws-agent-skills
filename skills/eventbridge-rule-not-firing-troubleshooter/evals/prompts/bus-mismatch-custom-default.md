# Eval prompt: bus-mismatch-custom-default

Diagnose the EventBridge rule failure for the following rule and event.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: PutEvents returns 200 with `FailedEntryCount: 0`. The target
Lambda is never invoked. The rule State is ENABLED and the pattern
matches the event (`test-event-pattern` returns `true` when tested
manually with the same pattern and event).

```text
EventBusName (rule): custom.events-bus
RuleName: ev-bus-mismatch-custom-default
EventPattern:
  source: ["myapp.events"]
  detail-type: ["EventPublished"]
State: ENABLED

PutEvents call (from CloudTrail):
  requestParameters.entries[0].eventBusName: "default"
  (operator omitted EventBusName in PutEvents, defaulting to
  the default bus)

SampleEvent:
  source: "myapp.events"
  detail-type: "EventPublished"
  detail: {"status": "ok"}

Target Lambda: fn-ev-bus-mismatch (has
  events.amazonaws.com principal, SourceArn scoped to
  custom.events-bus rule ARN).
```

The pattern matches, the rule is ENABLED, the target Lambda has the
correct principal. The event was put on the bus — but which bus?
Compare the PutEvents `eventBusName` against the rule's `EventBusName`.
