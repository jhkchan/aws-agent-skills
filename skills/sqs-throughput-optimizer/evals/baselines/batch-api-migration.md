# Baseline (no-skill) response: batch-api-migration

This file captures what a generic assistant produces WITHOUT the
sqs-throughput-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, batch request-unit math,
dollar savings estimate, CONFIRM gate).

---

You're sending and deleting messages one at a time, which means a lot of
API calls. SQS supports batch operations that can handle up to 10
messages per request.

For the producer, switch from SendMessage to SendMessageBatch. For the
consumer, switch from DeleteMessage to DeleteMessageBatch. This will
reduce your API request count by about 10x for send and delete
operations.

Here's an example of batch send:

```javascript
await sqs.sendMessageBatch({
  QueueUrl: queueUrl,
  Entries: messages.map((m, i) => ({ Id: String(i), MessageBody: m }))
}).promise();
```

This should bring your request count down from ~30M to ~12M per month
and save some cost.
