# Baseline (no-skill) — event-tracker-realtime

> This is the response a model produces **without** the skill
> definition. It writes a Lambda function that calls PutEvents without
> creating the event tracker first (which would fail without a valid
> tracking ID) and omits the one-tracker-per-group constraint.
> Generated for with-skill-vs-baseline comparison.

---

Write a Lambda handler that calls PutEvents on each click:

```python
def lambda_handler(event, context):
    personalize_events.put_events(
        trackingId="???",
        userId=event["user_id"],
        sessionId=event["session_id"],
        eventList=[{"eventType": "click", "itemId": event["item_id"]}]
    )
```

You will need to find the tracking ID somewhere.
