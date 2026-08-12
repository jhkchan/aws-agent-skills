# Example usage: eventbridge-rule-not-firing-troubleshooter

A walkthrough showing the skill diagnosing an EventBridge rule that
matches PutEvents 200 but never fires its target Lambda, demonstrating
the `test-event-pattern` probe, the case-sensitive exact-match
semantics, the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
pattern-mismatch root cause.

## Input (user prompt)

> Our EventBridge rule `ev-orders-prod-rule` is not firing. PutEvents
> returns 200 with zero failed entries — the events are definitely on
> the bus. But the target Lambda `fn-order-processor` is never invoked.
> We've been debugging this for an hour and can't figure out why.

```text
EventBusName: custom.orders-bus
RuleName: ev-orders-prod-rule
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

Target Lambda: fn-order-processor (same account)
Target Lambda resource-based policy: includes events.amazonaws.com
  principal with SourceArn matching the rule ARN.
```

## Skill output

```text
TARGET: ev-orders-prod-rule on custom.orders-bus
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rule's EventPattern filters on detail-type "Order Created"
  but the sample event has detail-type "OrderCreated" (no space). The
  test-event-pattern API returns Result: false. The source and detail
  fields match; only the detail-type value differs by spacing (Step 2b).
LAYER: PATTERN_DETAIL_TYPE_MISMATCH
EVIDENCE:
  - Symptom: PutEvents returns 200 with FailedEntryCount: 0 for events
    on custom.orders-bus, but the target Lambda fn-order-processor is
    never invoked. The rule State is ENABLED.
  - Probe: aws events test-event-pattern with the rule's pattern and
    the sample event returns {"Result": false}.
  - Probe: Field-by-field comparison shows source matches
    ("myapp.orders" = "myapp.orders"), detail.status matches
    ("confirmed" in both), but detail-type does NOT match: pattern has
    "Order Created", event has "OrderCreated".
  - Passing: EventBusName matches (custom.orders-bus in both PutEvents
    and rule); rule State is ENABLED; target Lambda has
    events.amazonaws.com principal in its resource-based policy.
REMEDIATION:
  1. Update the rule's EventPattern to match the actual detail-type:
     aws events put-rule --name ev-orders-prod-rule \
       --event-bus-name custom.orders-bus \
       --event-pattern '{"source":["myapp.orders"],"detail-type":["OrderCreated"],"detail":{"status":["confirmed"]}}'
  2. Verify the fix:
     aws events test-event-pattern \
       --event-pattern '{"source":["myapp.orders"],"detail-type":["OrderCreated"],"detail":{"status":["confirmed"]}}' \
       --event '{"version":"0","id":"abc","detail-type":"OrderCreated","source":"myapp.orders","account":"111111111111","region":"us-east-1","detail":{"status":"confirmed","orderId":"ord-9912"}}' \
       --output json
     Expected: {"Result": true}
CONFIRM: Before updating the rule, emit and await:
  "CONFIRM: About to update ev-orders-prod-rule EventPattern on
   custom.orders-bus. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Ran the decisive probe.** The skill's first action is
   `test-event-pattern`, which returns a boolean and eliminates all
   ambiguity. A generic assistant eyeballs the pattern and concludes it
   "looks right" — missing the spacing difference.

2. **Identified the exact mismatched field.** The skill compares each
   pattern field against the event field and isolates the mismatch to
   `detail-type`. The pattern has `"Order Created"` (with a space); the
   event has `"OrderCreated"` (no space). Exact-string matching means
   these are different strings.

3. **Ruled out bus mismatch and target permissions with positive
   evidence.** The skill confirms EventBusName matches in both PutEvents
   and the rule, and that the target Lambda has the
   `events.amazonaws.com` principal. These layers are ruled out with
   evidence, not assumed.

4. **Provided a verifiable fix.** The skill gives the corrected pattern
   and the `test-event-pattern` command to verify the fix BEFORE
   applying it. The operator can confirm the pattern matches before
   touching the rule.

## Slash-command invocation

```
/aws:troubleshoot-eventbridge-rule
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why ev-orders-prod-rule is not firing"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: eventbridge-rule-not-firing-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After fixing the pattern, verify the rule fires:

```bash
# Put a test event on the bus
aws events put-events \
  --entries '[{"EventBusName":"custom.orders-bus","Source":"myapp.orders","DetailType":"OrderCreated","Detail":"{\"status\":\"confirmed\",\"orderId\":\"test-001\"}"}]' \
  --profile default --output json

# Check the Lambda was invoked
aws logs filter-log-events \
  --log-group-name /aws/lambda/fn-order-processor \
  --start-time $(date -d '-5 minutes' +%s)000 \
  --profile default --output json

# Confirm test-event-pattern returns true
aws events test-event-pattern \
  --event-pattern '{"source":["myapp.orders"],"detail-type":["OrderCreated"],"detail":{"status":["confirmed"]}}' \
  --event '{"version":"0","id":"abc","detail-type":"OrderCreated","source":"myapp.orders","account":"111111111111","region":"us-east-1","detail":{"status":"confirmed","orderId":"test-001"}}' \
  --output json
```

Then monitor the Lambda's CloudWatch logs for 5-10 minutes to confirm
events are being processed.
