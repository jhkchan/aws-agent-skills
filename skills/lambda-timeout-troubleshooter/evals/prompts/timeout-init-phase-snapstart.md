# Eval prompt: timeout-init-phase-snapstart

Diagnose the Lambda timeout for the following function. Walk the
timeout-focused diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-init-phase-snapstart` returns `TaskTimeoutException` on
every cold start. Warm invocations succeed in 50 ms. There are zero
application log lines before each kill — the handler never ran.

```text
FunctionName: fn-init-phase-snapstart
Qualifier: prod (version 5)
Runtime: java21
Timeout: 8
MemorySize: 1024
Handler: com.example.Handler::handleRequest
PackageType: Zip
VpcConfig: (none — function is not VPC-attached)
FileSystemConfigs: (none)
SnapStart: { ApplyOn: None }
LastUpdateStatus: Successful (last update 3 days ago)

Recent log pattern (each cold start):
  START RequestId: ...
  (no further log line — no application logs)
  END RequestId: ... Duration: 8000.00 ms
    Memory Size: 1024 MB Max Memory Used: 440 MB
  Init Duration: 8200.34 ms
  Task timed out after 8.00 seconds

CloudWatch metrics (last hour):
  - Duration p50: 50 ms (warm), p99: 8000 ms (cold)
  - InitDuration Average: 8200 ms, Maximum: 8400 ms
  - MemoryUtilization Maximum: 43%
  - Errors: 18 (matches cold-start count)
```

The init phase is consuming the entire timeout budget; the handler
never runs. Identify the layer and recommend the fix.
