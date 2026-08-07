# Baseline (no-skill) response: dlq-idempotency-gap

This file captures what a generic assistant produces WITHOUT the
event-driven-automator skill loaded.

---

Your S3 trigger looks fine. EventBridge will invoke the Lambda when
objects are created. The duplicate invocations in CloudWatch are
probably from S3 sometimes retrying on its own.

If you're worried about duplicate processing, you could maybe add a
DLQ to the Lambda target. I think the syntax is something like:

```
aws events put-targets --rule s3-object-created-trigger --targets '[...]'
```

You might also want to make the Lambda idempotent if you haven't.
