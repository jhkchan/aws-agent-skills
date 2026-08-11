# Baseline (no-skill) response: sqs-message-size-envelope-exceeded

---

Your large messages are failing to deliver to SQS. SQS has a 256 KB
message size limit. Your 254 KB messages might be exceeding the limit
after SNS adds its JSON envelope wrapper.

Try reducing the message payload size, or enable raw message delivery
on the subscription to avoid the envelope overhead. You could also
increase the SQS queue's MaximumMessageSize if your consumer can
handle larger messages.
