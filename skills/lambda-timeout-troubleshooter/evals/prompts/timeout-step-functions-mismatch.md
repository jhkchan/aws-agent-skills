# Eval prompt: timeout-step-functions-mismatch

Diagnose the Lambda timeout for the following function. Walk the
timeout-focused diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-step-functions-mismatch` is invoked by a Step Functions
state machine. Executions fail with `States.Timeout` at exactly 30.00 s
on the ETL Task state, but the Lambda function's own CloudWatch shows
Duration: 38000 ms (success) for the same RequestId. The operator
sees Step Functions failures and assumes the Lambda timed out.

```text
FunctionName: fn-step-functions-mismatch
Qualifier: prod (version 11)
Runtime: python3.12
Timeout: 60
MemorySize: 1024
Handler: app.handler
VpcConfig: (none)

Step Functions state machine (Task state):
  "ETL": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:us-east-1:111111111111:function:fn-step-functions-mismatch:prod",
    "TimeoutSeconds": 30,
    "Next": "Notify"
  }

Step Functions execution history (last failure):
  - 2025-08-05T09:14:22.011Z: TaskStateEntered (ETL)
  - 2025-08-05T09:14:52.018Z: ExecutionFailed (error: States.Timeout)

Lambda CloudWatch (same RequestId):
  - START RequestId: 8f3...
  - INFO  Starting ETL batch
  - INFO  Processing 1247 records
  - INFO  Batch complete
  - END RequestId: 8f3... Duration: 38000.00 ms
    Memory Size: 1024 MB Max Memory Used: 410 MB
    Status: SUCCESS
```

The Step Functions Task-level timeout fired before the Lambda function's
own timeout. Identify the layer and recommend the fix.
