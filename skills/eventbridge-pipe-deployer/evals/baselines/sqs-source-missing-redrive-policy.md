# Baseline (no-skill) response: sqs-source-missing-redrive-policy

This file captures what a generic assistant produces WITHOUT the
eventbridge-pipe-deployer skill loaded — the contrast that proves
the skill catches the SQS-source DLQ-placement bug (pipe-level DLQ
silently ignored, source queue RedrivePolicy required).

---

Here's a plan for your SQS to Lambda pipe.

The pipe will:
- Pull messages from the SQS queue
- Send batches to the Lambda
- Use the configured DLQ for failed messages

Steps:

1. Create the pipe with the SQS source and Lambda target.
2. Configure the DeadLetterConfig on the pipe to point to your DLQ.
3. Start the pipe.

Commands:

```
aws pipes create-pipe --name prod-jobs-pipe --source <queue-arn> \
  --target <lambda-arn> \
  --source-parameters '{"SQSQueueParameters":{"DeadLetterConfig":{"Arn":"<dlq-arn>"}}}'
aws pipes start-pipe --name prod-jobs-pipe
```

Your DLQ should now catch any messages that fail processing. Let me
know if you'd like help with the IAM role.
