# Baseline (no-skill) response: no-encryption-queue

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-policy-auditor skill loaded.

---

This SQS queue does not have encryption enabled. You should enable
server-side encryption to protect message data at rest. The queue has a
dead-letter queue configured which is good, and there is no public
policy.

You can enable encryption by setting either SqsManagedSseEnabled to true
or by specifying a KMS key ID. The managed option is simpler and free.

Without encryption, message bodies are stored in plaintext which may
not meet compliance requirements.
