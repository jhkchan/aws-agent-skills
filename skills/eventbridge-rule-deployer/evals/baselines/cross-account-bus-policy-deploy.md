# Baseline (no-skill) response: cross-account-bus-policy-deploy

This file captures what a generic assistant produces WITHOUT the
eventbridge-rule-deployer skill loaded — note the absence of the
explicit bus policy grant, the aws:SourceAccount condition, and
the producer-side PutEvents CLI that the skill adds.

---

For cross-account event delivery, the producer account can call
PutEvents on the receiver's event bus. Set up a rule on the
receiver bus matching the event source, then have the producer
publish events.

```
# On receiver account
aws events put-rule --name order-events --event-bus-name app-events --event-pattern '{"source":["my.app.order"]}'
aws events put-targets --rule order-events --event-bus-name app-events --targets '[...]'

# On producer account
aws events put-events --entries '[{"EventBusName":"<receiver-bus-arn>","Source":"my.app.order","DetailType":"order.created","Detail":"{}"}]'
```

Make sure the receiver bus allows the producer to put events.
