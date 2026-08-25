# Init-Phase and Caller-Timeout Reference

Supplementary reference for the Lambda Timeout Troubleshooter skill.
Loaded on-demand when a diagnostic needs init-phase wall-clock budgets,
SnapStart eligibility, provisioned concurrency behaviour, or caller-side
timeout caps (API Gateway, ALB, Step Functions).

## Lambda wall-clock model

Lambda measures wall clock from the moment the service receives the
Invoke API call until the handler returns (or the timeout fires). On a
cold start, the budget is shared between the init phase and the invoke
phase:

```
+--- configured Timeout (wall-clock budget) ---+
|  init phase         |  invoke phase          |
|  (Runtime, modules, |  (handler execution,   |
|   static init)      |   downstream calls)    |
+---------------------+------------------------+
```

A function with `InitDuration: 4500 ms` and `Timeout: 5000 ms` has only
500 ms of invoke budget on every cold start. Warm invocations skip
init entirely and use the full budget for the handler.

## SnapStart eligibility and effect

| Runtime | SnapStart supported | Typical init without SnapStart | With SnapStart |
|---|---|---|---|
| java21 (Corretto) | Yes | 1500-3500 ms (up to 8000 ms with Spring Boot) | 50-200 ms (restore) |
| java17 (Corretto) | Yes | 1500-3500 ms | 50-200 ms (restore) |
| java11 (Corretto) | Yes | 1500-3500 ms | 50-200 ms (restore) |
| nodejs20.x, nodejs22.x | No | 100-300 ms | n/a (already fast) |
| python3.11, python3.12 | No | 100-300 ms | n/a |
| dotnet8 | No | 300-800 ms | n/a |
| ruby3.3 | No | 100-300 ms | n/a |
| provided.al2023 | No | varies | n/a |
| container (PackageType: Image) | No | base runtime + image pull | n/a |

### SnapStart requirements

- Runtime: Java 11, 17, or 21 on the managed AWS runtime (Corretto).
- Enable: `update-function-configuration --snap-start
  ApplyOn=PublishedVersion`, then publish a new version.
- Only newly published versions benefit; existing versions do NOT
  retroactively apply.
- Restore cost: typically 50-200 ms.

### SnapStart unique-state gotchas

SnapStart restores the same memory snapshot to every new execution
environment. Code that captures unique-per-instance state at init time
behaves identically across "fresh" environments:

| State | Symptom | Fix |
|---|---|---|
| Network connections (DB, HTTP pools) | Stale connections fail on first use | Re-establish in `afterRestore` hook |
| Random UUIDs generated at init | Same UUID across all invocations | Regenerate in `afterRestore` |
| Cached timestamps | Same timestamp across invocations | Refresh in `afterRestore` |
| Thread pools | Threads from snapshot may be in inconsistent state | Re-initialise in `afterRestore` |

The `afterRestore` hook is part of the AWS SDK for Java SnapStart
integration (`com.amazonaws.services.lambda.runtime.LambdaSnapStart`).

## Provisioned concurrency and init timeout

Provisioned concurrency pre-initialises N execution environments and
keeps them warm. Billing is per-second regardless of invocations.

### Failure mode: spillover

When traffic exceeds N concurrent invocations, overflow invocations
fall through to on-demand environments — every spillover is a cold
start. The metric to watch:

```
ProvisionedConcurrencySpilloverInvocations
```

A sustained non-zero spillover count means the allocation is too low.
For Java functions without SnapStart, every spillover invocation pays
the full init cost (1-8 s), which can exceed the configured Timeout.

### Provisioned concurrency init-phase timeout

Provisioned concurrency init runs at version-publish time, not at
invoke time. If init fails (SnapStart disabled + heavy framework, image
too large, init crashing), the provisioned environments never become
ready. Invoke-time spillover then pays the init cost.

### Diagnostic probes

```bash
# Provisioned concurrency allocation vs spillover
aws lambda list-provisioned-concurrency-configs \
  --function-name <name> --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ProvisionedConcurrencySpilloverInvocations \
  --dimensions Name=FunctionName,Value=<name>,Name=Resource,Value=<alias> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ProvisionedConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<name>,Name=Resource,Value=<alias> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

## Caller-side timeout matrix

The caller's timeout may fire BEFORE the Lambda function's own Timeout.
This produces confusing symptoms where the caller reports a timeout but
the Lambda succeeded.

| Caller | Default timeout | Tunable? | Symptom when it fires |
|---|---|---|---|
| API Gateway REST API | 29 s | No (hard cap) | 504 Gateway Timeout; Lambda continues |
| API Gateway HTTP API | 29 s | No (hard cap) | 504 Gateway Timeout; Lambda continues |
| ALB | 60 s | Yes (1-4000 s, but Lambda Timeout caps) | 504; Lambda continues |
| Step Functions `Task` | 60 s | Yes (`TimeoutSeconds` per state) | `States.Timeout`; Lambda continues |
| Step Functions `Task` with Retry | per-attempt (TimeoutSeconds) | Yes | Retry exhausted; final state `States.Timeout` |
| Direct Invoke (sync) | caller-side | caller-side | Caller's own SDK timeout |
| EventBridge | n/a (async) | n/a | Caller gets 202 immediately |
| S3 trigger | n/a (async) | n/a | n/a |
| SQS event source mapping | `VisibilityTimeout` default 30 s | Yes | Partial-batch failure; record returns to queue |

### Step Functions `TimeoutSeconds` semantics

- Default: 60 s.
- Per-attempt: each retry attempt has its own `TimeoutSeconds` budget.
- A `Task` with `TimeoutSeconds: 30` and `Retry: [{MaxAttempts: 2}]`
  has up to 90 s of total wall clock (3 attempts * 30 s), not 30 s.
- `HeartbeatSeconds` is separate; if set, the task must send heartbeats
  more frequently than `HeartbeatSeconds` or it times out.

### API Gateway 29-second cap

- Applies to REST API and HTTP API integrations.
- NOT configurable — it's a hard service limit.
- The Lambda function continues running to its own Timeout after the
  504 is returned. The function's response (if any) is discarded.
- For workloads exceeding 29 s, redesign as async (Event invocation)
  so the client receives 202 immediately and the function processes in
  the background.

## Hyperplane ENI history (why "VPC cold start" is mostly a myth)

| Period | Behaviour | Cold-start cost |
|---|---|---|
| Pre-2019 (Hyperplane launch) | Each function got its own ENI per subnet | 5-10 s for ENI creation on cold start |
| 2019+ (Hyperplane ENIs) | Shared, pre-provisioned per-AZ ENIs | 100-500 ms (lookup, not creation) |

### When to actually diagnose TIMEOUT_VPC_ENI

Only with positive evidence:

1. `aws ec2 describe-network-interfaces --filters Name=description,Values='AWS Lambda VPC ENI:*'`
   returns no interfaces for the function's subnets (Hyperplane limit
   or service event).
2. AWS Health reports a regional Lambda or EC2 networking event.
3. The function is in a sub-optimal VPC config (e.g., subnets exhausted,
   SG limiting the function's own egress to the Hyperplane ENI range).

Do NOT diagnose TIMEOUT_VPC_ENI from pre-2019 blog posts or runbooks.

## EFS mount timeout

`FileSystemConfigs` populated; first invocation of an environment times
out at EFS mount.

| Configuration | Cold-mount cost |
|---|---|
| Same-AZ mount target + access point | < 500 ms |
| Cross-AZ mount target | 1-3 s |
| Cross-region (not supported) | n/a |
| Access point misconfigured | timeout (infinite) |

### Diagnostic probe

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.FileSystemConfigs'

aws efs describe-mount-targets \
  --file-system-id <fs-id> --output json | \
  jq '.MountTargets[] | {SubnetId, AvailabilityZoneName, LifeCycleState}'

aws efs describe-access-points \
  --output json | jq '.AccessPoints[] | {Name, FileSystemId, PosixUser}'
```

## Child-process timeout

`child_process.exec` (Node) and `subprocess.run` (Python) without an
explicit `timeout` inherit the Lambda Timeout. Fork+exec overhead on
small Lambda environments (128 MB) can be 500-1000 ms per spawn.

### Safe patterns

```javascript
// Node — pass exec timeout
const { exec } = require('child_process');
exec(cmd, { timeout: 3000 }, (err, stdout, stderr) => { /* ... */ });
```

```python
# Python — pass timeout
import subprocess
result = subprocess.run(cmd, timeout=3.0, capture_output=True)
```

For workloads spawning many child processes, consider a container
function with a larger memory allocation; the per-spawn overhead scales
with available CPU.

## Caller-side hard caps (moved from SKILL.md)

| Caller | Hard cap | Tunable? |
|---|---|---|
| API Gateway REST API | 29 s | No |
| API Gateway HTTP API | 29 s | No |
| ALB | 60 s default | Yes (1-4000 s) |
| Step Functions | per `Task.TimeoutSeconds` | Yes |
