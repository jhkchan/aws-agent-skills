# Baseline (no-skill) response: fifo-poison-message

---

Your FIFO queue seems stuck for one customer group. The DLQ has messages
all from MessageGroupId "cust-9912", and the Lambda is throwing JSON
parse errors. You should fix the Lambda to handle bad JSON, and delete
the bad messages from the queue. FIFO queues process messages in order,
so if one message fails it blocks the rest.

Also consider increasing maxReceiveCount or adding error handling for
malformed messages.
