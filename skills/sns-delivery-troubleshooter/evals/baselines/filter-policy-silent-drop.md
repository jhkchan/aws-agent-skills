# Baseline (no-skill) response: filter-policy-silent-drop

---

Some of your messages aren't being delivered to the SQS queue. Since
there are no errors in the metrics, the messages are probably being
published correctly. Check that the SQS queue is receiving by looking
at the ApproximateNumberOfMessagesVisible metric.

The filter policy is set to order.created only. If you want
order.updated messages too, you might need to update it. Also verify
the consumer is polling the queue.
