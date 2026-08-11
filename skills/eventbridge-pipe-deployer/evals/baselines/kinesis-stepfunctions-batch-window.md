# Baseline (no-skill) response: kinesis-stepfunctions-batch-window

This file captures what a generic assistant produces WITHOUT the
eventbridge-pipe-deployer skill loaded — contrast proves the skill
adds structure around streaming-source batch windowing, Step Functions
Standard target permissions, and OnPartialBatchItemFailure tuning.

---

Here's a plan for your Kinesis to Step Functions pipe.

The pipe will:
- Read from your Kinesis stream
- Send batches to the state machine
- Retry on failure

Steps:

1. Create the pipe with the Kinesis source and Step Functions target.
2. Start the pipe.

Commands:

```
aws pipes create-pipe --name prod-events-orchestration \
  --source <kinesis-arn> --target <state-machine-arn>
aws pipes start-pipe --name prod-events-orchestration
```

For batch windowing, you can configure MaximumBatchingWindowInSeconds
when creating the pipe. Set it to 30 to gather batches. Let me know
if you need help with the IAM role.
