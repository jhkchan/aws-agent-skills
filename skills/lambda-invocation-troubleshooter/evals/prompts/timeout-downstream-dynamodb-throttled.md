# Eval prompt: timeout-downstream-dynamodb-throttled

Diagnose the Lambda invocation failure for the following function. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application invokes `fn-timeout-downstream-dynamodb`
synchronously via API Gateway. About 30% of invocations return
`TaskTimeoutException` after exactly 30 seconds. The remaining 70%
succeed in 1-3 seconds. Errors metric shows 47 timeouts in the last
hour.

```text
FunctionName: fn-timeout-downstream-dynamodb
Qualifier: prod (version 42)
Runtime: nodejs20.x
Timeout: 30
MemorySize: 512
Handler: index.handler
PackageType: Zip
VpcConfig: (none — function is not VPC-attached)
LastUpdateStatus: Successful (last update 2 days ago)

Recent log pattern (last 10 timeouts):
  INFO  Putting item to orders-table (id=...)
  (no further log line)
  END RequestId: ... Duration: 30000.00 ms
    Memory Size: 512 MB Max Memory Used: 78 MB
  Task timed out after 30.00 seconds

CloudWatch metrics (last hour):
  - Duration p50: 1.2s, p99: 30s, Maximum: 30s
  - MemoryUtilization Maximum: 15%
  - Errors: 47

DynamoDB context:
  - Table orders-table
  - BillingModeSummary: PROVISIONED
  - WriteCapacityUnits: 100
  - WriteThrottleEvents (last hour): sustained
```

Distinguish config timeout (would affect every invocation uniformly)
from downstream timeout (bursty pattern). The function is not
VPC-attached, so VPC routing is not in play.
