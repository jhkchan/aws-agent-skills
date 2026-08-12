# Eval prompt: pattern-detail-type-mismatch

Diagnose the EventBridge rule failure for the following rule and event.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: PutEvents returns 200 with `FailedEntryCount: 0` for events on
`custom.orders-bus`, but the target Lambda `fn-ev-pattern-detail-type` is
never invoked. The rule State is ENABLED.

```text
EventBusName: custom.orders-bus
RuleName: ev-pattern-detail-type-mismatch
EventPattern:
  source: ["myapp.orders"]
  detail-type: ["Order Created"]
  detail:
    status: ["confirmed"]
State: ENABLED

SampleEvent:
  version: "0"
  id: "abc-123"
  detail-type: "OrderCreated"
  source: "myapp.orders"
  account: "111111111111"
  region: "us-east-1"
  detail:
    status: "confirmed"
    orderId: "ord-9912"

Target Lambda: fn-ev-pattern-detail-type (same account)
Target Lambda resource-based policy: includes events.amazonaws.com
  principal with SourceArn matching the rule ARN.
```

Run `test-event-pattern` mentally: does the pattern match the event?
Compare each field. The source matches, the detail.status matches — but
examine the `detail-type` field closely.
