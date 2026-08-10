# Eval prompt: cross-account-bus-policy-deploy

Design a cross-account EventBridge rule deployment for the
following scenario. Emit the standard PLAN block including the
cross-account bus policy configuration.

Design reference: cross-account-bus-policy-deploy
Producer account: 222222222222
Receiver account: 111111111111
Region: us-east-1

Source: my.app.order (custom application event)
Detail-type: order.created
Receiver event bus: arn:aws:events:us-east-1:111111111111:event-bus/app-events
  (already created in receiver account).
Receiver Lambda target:
  arn:aws:lambda:us-east-1:111111111111:function:process-order
  (idempotent on order_id; invocation permission granted).
DLQ in receiver account:
  arn:aws:sqs:us-east-1:111111111111:eventbridge-order-dlq
  (created with 14-day retention).

The deployment must include:
1. The bus policy on the receiver bus granting the producer account
   events:PutEvents (with aws:SourceAccount condition).
2. The rule on the receiver bus matching my.app.order events.
3. The Lambda target wiring with DLQ and retry.
4. The producer-side PutEvents CLI template.
