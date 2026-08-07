# Eval prompt: oom-memory-too-low

Diagnose the Lambda invocation failure for the following function. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-oom-memory-too-low` fails on image payloads larger than
4 MB. Logs show `Runtime.ExitError: ErrorType: OutOfMemory` on the same
invocations. Smaller payloads succeed in under 2 seconds.

```text
FunctionName: fn-oom-memory-too-low
Qualifier: prod (version 7)
Runtime: nodejs20.x
Timeout: 60
MemorySize: 256
Handler: index.handler
PackageType: Zip
VpcConfig: (none)

Recent log pattern:
  INFO  Processing image of size 6.2 MB
  FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript
    heap out of memory
  Runtime.ExitError: ErrorType: OutOfMemory

CloudWatch metrics (last hour):
  - Duration p99: 1.2s
  - MemoryUtilization Maximum: 100
  - Errors: 12 (all on payloads > 4 MB)
```

The function reads the full image into memory for resizing. Memory
is the bottleneck — the function is OOMing on payloads that fit easily
on disk. Lambda CPU scales with memory, so raising memory will also
reduce Duration on the larger payloads.
