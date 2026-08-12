---
description: Diagnoses AWS Lambda TaskTimeoutException through a focused timeout decision tree — init-phase timeout (SnapStart), SDK retry storms, HTTP client missing connect timeouts, DB connection overhead, Step Functions vs Lambda timeout mismatch, API Gateway 504 vs async 202, provisioned concurrency init timeout, OOM-before-timeout masking. Emits ROOT_CAUSE_IDENTIFIED with the specific failure layer.
nl_triggers:
  - "Lambda TaskTimeoutException"
  - "Task timed out Lambda"
  - "Lambda timeout init phase"
  - "Lambda cold start timeout"
  - "Lambda SnapStart timeout"
  - "Lambda SDK retry storm"
  - "Lambda exponential backoff timeout"
  - "Lambda HTTP client hang"
  - "axios no connect timeout Lambda"
  - "Lambda RDS Proxy timeout"
  - "database connection Lambda timeout"
  - "Lambda VPC ENI timeout"
  - "Lambda EFS mount timeout"
  - "Step Functions Lambda timeout mismatch"
  - "States.Timeout Lambda"
  - "API Gateway 504 Lambda"
  - "Lambda async 202 caller timeout"
  - "provisioned concurrency init timeout"
  - "Lambda OOM before timeout"
  - "Lambda child process timeout"
  - "Lambda X-Ray bottleneck"
  - "Lambda Duration p99"
  - "diagnose Lambda timeout"
routes_to: lambda-timeout-troubleshooter
---

# /aws:troubleshoot-lambda-timeout

Activate the `lambda-timeout-troubleshooter` skill and diagnose an AWS
Lambda `TaskTimeoutException` through the focused timeout diagnostic
tree.

## What it does

Reads a TaskTimeoutException symptom description (error message, REPORT
log line with Duration ≈ Timeout, observed pattern — every invocation
vs bursty) plus the function configuration, then walks the timeout-
focused diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — function state and LastUpdateStatus
   (`get-function-configuration`), Duration p99/p99.9 and InitDuration
   metrics, MemoryUtilization (rule out OOM-before-timeout), AWS Health
   (regional incidents).
2. **Symptom entry** — map the timeout pattern to one of: TIMEOUT_CONFIG
   (timeout too low), TIMEOUT_DOWNSTREAM (slow downstream), TIMEOUT_INIT_PHASE
   (cold-start init exceeds budget), TIMEOUT_SDK_RETRY_STORM (retry
   multiplier), TIMEOUT_HTTP_CLIENT (missing connect/read timeouts),
   TIMEOUT_DB_CONNECTION (handshake overhead without RDS Proxy),
   TIMEOUT_STEP_FUNCTIONS_MISMATCH (Task.TimeoutSeconds < Lambda Timeout),
   TIMEOUT_ASYNC_APIGW (29s cap on sync invokes), TIMEOUT_PROV_CONCURRENCY_INIT
   (spillover), TIMEOUT_OOM_BEFORE_TIMEOUT, TIMEOUT_VPC_ENI, TIMEOUT_EFS_MOUNT,
   TIMEOUT_CHILD_PROCESS.
3. **Layer-specific probes** —
   - Config vs downstream: CloudWatch Duration p99/Maximum vs configured
     Timeout; downstream service metrics (DynamoDB Throttles, RDS
     connections); last log line before kill.
   - Init phase: InitDuration metric; SnapStart config (Java only);
     MemorySize (CPU scales with memory for CPU-bound init).
   - SDK retry storm: log lines "Retrying request ... attempt N of M";
     SDK `maxRetries` / `maxAttempts` config; per-attempt `requestTimeout`.
   - HTTP client: function code review for axios/fetch/requests config;
     connect and read timeout defaults by client library.
   - DB connection: RDS Proxy presence; module-scope connection reuse;
     TLS handshake cost; cross-AZ mount.
   - Step Functions: Task `TimeoutSeconds` vs Lambda `Timeout`;
     `HeartbeatSeconds`; Retry `MaxAttempts` semantics.
   - API Gateway: 29s integration cap (REST and HTTP APIs); ALB
     configurable timeout.
   - Provisioned concurrency: `ProvisionedConcurrencySpilloverInvocations`
     metric; SnapStart on Java; image size for container functions.
   - OOM-before-timeout: `MemoryUtilization Maximum: 100` correlates
     with timeout; raise memory first.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input).

Emits a deterministic diagnostic block per target:

```text
TARGET: <function-name with qualifier>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <TIMEOUT_CONFIG | TIMEOUT_DOWNSTREAM | TIMEOUT_INIT_PHASE |
        TIMEOUT_VPC_ENI | TIMEOUT_DB_CONNECTION | TIMEOUT_HTTP_CLIENT |
        TIMEOUT_SDK_RETRY_STORM | TIMEOUT_EFS_MOUNT |
        TIMEOUT_STEP_FUNCTIONS_MISMATCH | TIMEOUT_ASYNC_APIGW |
        TIMEOUT_PROV_CONCURRENCY_INIT | TIMEOUT_OOM_BEFORE_TIMEOUT |
        TIMEOUT_CHILD_PROCESS | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or pattern>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a TaskTimeoutException symptom and ask any of:

- "Lambda function returns TaskTimeoutException"
- "Lambda times out at 30s every invocation"
- "Lambda cold start times out, warm invocations succeed"
- "Lambda SDK retry storm exhausts the timeout"
- "Lambda axios.get hangs on a dead host"
- "Lambda database connection times out under concurrency"
- "Step Functions States.Timeout but Lambda succeeded"
- "API Gateway 504 but Lambda function succeeded"
- "Provisioned concurrency spillover invocations time out"
- "Lambda MaxMemoryUsed hits MemorySize and times out"

A bare function name + any timeout verb ("Lambda failing", "function
times out", "invocation error at 30s") also routes here via the
orchestrator.

## Inputs

- Symptom description: error string, observed pattern (every invocation
  vs bursty), correlation with traffic peaks, caller (Step Functions /
  API Gateway / EventBridge / direct Invoke).
- Function configuration: name, qualifier (alias or version), runtime,
  timeout, memory, SnapStart, VpcConfig, FileSystemConfigs,
  LastUpdateStatus.
- For live-account diagnosis: caller context — invocation type (sync
  RequestResponse vs async Event), Step Functions `TimeoutSeconds`,
  API Gateway integration type, source ARN, region. The skill uses
  `get-function-configuration`, `filter-log-events`, `get-metric-statistics`
  (Duration p99/p99.9, InitDuration, MemoryUtilization,
  ProvisionedConcurrencySpilloverInvocations), `xray get-trace-summaries`,
  `stepfunctions describe-execution`, `ec2 describe-route-tables`,
  `lambda list-provisioned-concurrency-configs`.

## Outputs

- One diagnostic block per target function/qualifier.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: timeout/memory raise, SnapStart enablement,
  SDK `maxAttempts` config, HTTP client timeout config, RDS Proxy
  setup, Step Functions `TimeoutSeconds` alignment, async-invocation
  redesign, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Lambda timeout failures).
- `/aws:troubleshoot-lambda-invocation` for non-timeout Lambda failures
  (AccessDenied, OOM, KMS decrypt, ECR pull, async retry storms).
- `/aws:audit-lambda-function` for configuration posture audits on the
  same function (security exposure, runtime deprecation, logging
  coverage).
- `/aws:troubleshoot-step-functions-execution` for Step Functions state-
  machine-level debugging when the Lambda is invoked by Step Functions.
