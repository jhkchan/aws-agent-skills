# Eval prompt: content-filter-nested-depth

Diagnose the EventBridge rule failure for the following rule and event.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: PutEvents returns 200 but the rule never fires. The pattern
looks correct — the source, detail-type, and nested path all correspond
to the event. But `aws events test-event-pattern` returns
`{"Result": false}`.

```text
EventBusName: custom.events-bus
RuleName: ev-content-filter-nested-depth
EventPattern:
  source: ["myapp.events"]
  detail-type: ["Deep Event"]
  detail:
    l1:
      l2:
        l3:
          l4:
            l5:
              l6:
                l7:
                  l8:
                    l9:
                      l10:
                        l11: ["target-value"]
State: ENABLED

SampleEvent:
  version: "0"
  detail-type: "Deep Event"
  source: "myapp.events"
  detail:
    l1:
      l2:
        l3:
          l4:
            l5:
              l6:
                l7:
                  l8:
                    l9:
                      l10:
                        l11: "target-value"

aws events test-event-pattern --event-pattern '<pattern>' \
  --event '<event>' returns {"Result": false}.
```

The pattern and event values appear identical. Count the nesting depth
of the JSON path in the `detail` object. EventBridge has a maximum
depth limit for content-based filtering.
