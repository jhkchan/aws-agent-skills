# Baseline (no-skill) response: max-receive-count-too-low

This file captures what a generic assistant produces WITHOUT the
sqs-dead-letter-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

Your SQS dead-letter queue is filling up. This is probably because your
consumer Lambda is failing to process some messages. The payment gateway
is returning 503 errors, which causes the Lambda to fail. You should
add retry logic or fix the downstream API issue. Also check if your
maxReceiveCount is set appropriately — you might want to increase it.

You could also consider adding exponential backoff in your Lambda
handler to handle transient failures from the payment gateway.
