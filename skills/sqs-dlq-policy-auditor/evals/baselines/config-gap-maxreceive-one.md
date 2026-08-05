# Baseline (no-skill) response: config-gap-maxreceive-one

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-policy-auditor skill loaded.

---

This SQS queue has a dead-letter queue configured, but the
maxReceiveCount is set to 1. This means that if a consumer fails to
process a message even once, it will be immediately moved to the
dead-letter queue. This is quite aggressive and may result in messages
being sent to the DLQ that would have succeeded on a retry.

You should consider increasing the maxReceiveCount to at least 3 or 5
to give messages a few chances before being dead-lettered.

The DLQ also has a retention period of only 1 day which is quite short.
You may want to increase this to give yourself more time to investigate
failed messages.
