# Baseline (no-skill) response: no-dlq-configured

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-policy-auditor skill loaded.

---

This SQS queue does not have a dead-letter queue configured. This means
if a message cannot be processed successfully, it will keep being retried
until it expires from the queue.

You should configure a dead-letter queue so that failed messages can be
sent there for analysis and replay. The queue has encryption enabled
which is good. There is no queue policy which means IAM controls access.

To fix this, create a new SQS queue to use as a dead-letter queue and
then set the RedrivePolicy on this queue.
