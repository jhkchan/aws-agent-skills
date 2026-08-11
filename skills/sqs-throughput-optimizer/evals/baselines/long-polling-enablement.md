# Baseline (no-skill) response: long-polling-enablement

This file captures what a generic assistant produces WITHOUT the
sqs-throughput-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, empty-receive ratio citation,
dollar savings estimate, CONFIRM gate).

---

Your SQS queue has a high number of empty receives. With 85 million
empty receives per month out of 100 million total requests, you're
wasting a lot of money on calls that return nothing.

You should enable long polling by setting ReceiveMessageWaitTimeSeconds
to 20. This will make your consumers wait up to 20 seconds for messages
to arrive instead of polling repeatedly and getting empty responses.

```
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/q-long-polling-enablement \
  --attributes ReceiveMessageWaitTimeSeconds=20
```

This should reduce your empty receives significantly and save on request
costs.
