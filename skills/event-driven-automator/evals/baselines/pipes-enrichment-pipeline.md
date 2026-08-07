# Baseline (no-skill) response: pipes-enrichment-pipeline

This file captures what a generic assistant produces WITHOUT the
event-driven-automator skill loaded.

---

For a DynamoDB Streams to Lambda to Step Functions pipeline, you can
use EventBridge Pipes. Create a pipe with the stream as source, the
Lambda as enrichment, and Step Functions as target.

```
aws pipes create-pipe --name orders-pipe --source <stream-arn> --target <sfn-arn> ...
```

You'll need an IAM role with DynamoDB Streams read and Step
Functions StartExecution permissions.

Start the pipe with `aws pipes start-pipe --name orders-pipe`.
