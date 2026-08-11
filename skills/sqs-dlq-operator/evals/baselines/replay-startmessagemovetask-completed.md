# Baseline (no-skill) response: replay-startmessagemovetask-completed

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-operator skill loaded.

---

To replay messages from the DLQ back to the source queue, use
StartMessageMoveTask:

```bash
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq \
  --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders
```

You can check the status with:

```bash
aws sqs list-message-move-tasks --source-arn <dlq-arn>
```

Make sure the root cause is fixed before replaying, otherwise the
messages will just end up back in the DLQ. You can also throttle the
replay with `--max-number-of-messages-per-second` if you have a lot of
messages.
