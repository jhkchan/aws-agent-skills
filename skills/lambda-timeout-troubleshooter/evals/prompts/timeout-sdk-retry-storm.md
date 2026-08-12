# Eval prompt: timeout-sdk-retry-storm

Diagnose the Lambda timeout for the following function. Walk the
timeout-focused diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-sdk-retry-storm` started returning `TaskTimeoutException`
after the 09:00 traffic peak. 60% of invocations now time out at 30 s
during the peak; off-peak invocations complete in 2-4 s. Logs show
SDK retry entries before each kill.

```text
FunctionName: fn-sdk-retry-storm
Qualifier: prod (version 18)
Runtime: nodejs20.x
Timeout: 30
MemorySize: 512
Handler: index.handler
PackageType: Zip
VpcConfig: (none)
SnapStart: (not applicable — Node.js)

Recent log pattern (peak-hour timeouts):
  INFO  Putting item to orders-table (id=...)
  Retrying request ... attempt 2 of 3
  Retrying request ... attempt 3 of 3
  (no further log line)
  END RequestId: ... Duration: 30000.00 ms
    Memory Size: 512 MB Max Memory Used: 142 MB
  Task timed out after 30.00 seconds

CloudWatch metrics (last hour):
  - Duration p50: 2.1s (off-peak), p99: 30s (peak), Maximum: 30s
  - MemoryUtilization Maximum: 28%
  - Errors: 142 (correlated with traffic peak)

DynamoDB context:
  - Table orders-table
  - BillingModeSummary: PROVISIONED
  - WriteCapacityUnits: 200
  - WriteThrottleEvents (last hour): sustained during peak
```

The AWS SDK v3 default `maxRetries: 3` is multiplying the per-call
latency. Identify the layer and recommend the fix.
