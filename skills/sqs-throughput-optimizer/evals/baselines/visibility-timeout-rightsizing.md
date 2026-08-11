# Baseline (no-skill) response: visibility-timeout-rightsizing

This file captures what a generic assistant produces WITHOUT the
sqs-throughput-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, re-delivery rate citation,
visibility timeout formula, CONFIRM gate).

---

Your visibility timeout is set to 30 seconds but your Lambda function
takes 38-45 seconds to process. This means messages become visible again
before processing is done, causing them to be picked up by another
invocation and re-processed.

You should increase the visibility timeout to at least 60 seconds, or
even 90 seconds to be safe. Since your p95 processing time is 45
seconds, a 90-second timeout gives you a comfortable buffer.

```
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes VisibilityTimeout=90
```

If you're using Lambda ESM, also update the ESM visibility timeout:

```
aws lambda update-event-source-mapping \
  --uuid <uuid> --visibility-timeout 90
```

This should reduce the re-delivery rate and save on duplicate processing.
