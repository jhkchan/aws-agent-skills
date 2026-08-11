# Baseline (no-skill) response: analyze-dlq-visibility-timeout-race-blocked

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-operator skill loaded.

---

To analyze messages in your DLQ, receive them and inspect the body:

```bash
aws sqs receive-message --queue-url <dlq-url> \
  --max-number-of-messages 10 --attribute-names All
```

If the payloads look valid, the issue might be with your consumer. Check
the Lambda function's CloudWatch Logs for errors. You may also want to
increase the visibility timeout on the source queue if processing takes
longer than expected.

Also consider enabling partial batch responses on your Lambda event
source mapping so that only failed messages are retried instead of the
entire batch.
