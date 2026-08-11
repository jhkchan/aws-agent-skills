# Baseline (no-skill) response: ddb-streams-lambda-filter-dlq

This file captures what a generic assistant produces WITHOUT the
eventbridge-pipe-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated
CHECKLIST, expert knowledge of pipe-as-poller semantics, dual IAM
grants, pipe-level vs. source-queue DLQ distinction).

---

Here's a plan for your EventBridge Pipe.

The pipe will:
- Read from your DynamoDB stream
- Filter to only CONFIRMED orders
- Send each batch to your orders-processor Lambda
- Use the SQS queue as a DLQ for failed records

Steps:

1. Create an IAM role for the pipe.
2. Create the pipe with the source, filter, and target.
3. Start the pipe.

Commands:

```
aws pipes create-pipe --name prod-orders-pipe --source <stream-arn> --target <lambda-arn>
aws pipes start-pipe --name prod-orders-pipe
```

You may also want to add a Lambda event source mapping on the
stream to be safe. Let me know if you need help with the IAM role
policy.
