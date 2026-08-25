---
name: lambda-timeout-troubleshooter
description: 'Diagnoses AWS Lambda TaskTimeoutException through a focused timeout decision tree: configured timeout vs observed Duration, init-phase (cold-start) timeout vs invoke-phase timeout, SDK retry storms with exponential backoff multiplier, HTTP client missing connect timeouts, database connection overhead without RDS Proxy, VPC ENI attachment delay (hyperplane-eliminated cold start), EFS mount latency, Step Functions task timeout vs Lambda Timeout mismatch, API Gateway 504 vs async Lambda 202, provisioned concurrency init-phase timeout, OOM-before-timeout masking, child-process fork overhead, and p99/p99.9 Duration analysis with X-Ray trace bottleneck identification. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages, REPORT log lines, and function configuration. Live-account diagnosis uses aws lambda get-function-configuration, aws logs get-log-events / filter-log-events, aws cloudwatch get-metric-statistics (Duration p99/p99.9, InitDuration, Throttles), aws xray get-trace-summaries / batch-get-traces, aws stepfunctions describe-execution, aws ec2...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a Lambda TaskTimeoutException where the root cause may be init-phase timeout (cold start), invoke-phase downstream latency, SDK retry multiplier exhausting the budget, HTTP client missing connect/read timeouts, DB connection overhead without RDS Proxy, Step Functions vs Lambda timeout mismatch, API Gateway 504 on sync invokes, provisioned concurrency init-phase timeout, OOM masking as timeout, or child-process fork overhead — walking the symptom to the failed layer with verify commands, validating why a function returns TaskTimeoutException, or triaging a "Lambda times out" page where the actual bottleneck is init, retry, downstream, or memory — not the configured timeout alone.
  when_not_to_use: Invocation AccessDenied or KMS decrypt errors (use lambda-invocation-troubleshooter), code-level debugging of the function handler (use the application logs and a debugger), CloudFront/Lambda@Edge origin timeouts (use the CloudFront distribution logs), or steady-state p99 latency tuning without TaskTimeoutException (use lambda-cold-start-optimizer). This skill diagnoses TaskTimeoutException root causes; it does not author handler code or audit steady-state config posture.
  activation_triggers: Lambda TaskTimeoutException, Task timed out Lambda, Lambda timeout init phase, Lambda cold start timeout, Lambda SnapStart timeout, Lambda SDK retry storm, Lambda exponential backoff timeout, Lambda HTTP client hang, axios no connect timeout Lambda, Lambda RDS Proxy timeout, database connection Lambda timeout, Lambda VPC ENI timeout, Lambda EFS mount timeout, Step Functions Lambda timeout mismatch, API Gateway 504 Lambda, Lambda async 202 caller timeout, provisioned concurrency init timeout, Lambda OOM before timeout, Lambda child process timeout, Lambda X-Ray bottleneck, Lambda Duration p99, diagnose Lambda timeout
  invocation_schema: 'Input: either (a) a TaskTimeoutException symptom description (error message, REPORT log line with Duration ≈ Timeout, observed pattern — every invocation vs bursty), optionally paired with the function configuration (get-function-configuration output, Runtime, Timeout, MemorySize, SnapStart, VpcConfig, FileSystemConfigs) and recent CloudWatch logs / X-Ray trace, OR (b) a FunctionName plus caller context (Step Functions / API Gateway / EventBridge / direct Invoke) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {TIMEOUT_CONFIG, TIMEOUT_DOWNSTREAM, TIMEOUT_INIT_PHASE, TIMEOUT_VPC_ENI, TIMEOUT_DB_CONNECTION, TIMEOUT_HTTP_CLIENT, TIMEOUT_SDK_RETRY_STORM, TIMEOUT_EFS_MOUNT, TIMEOUT_STEP_FUNCTIONS_MISMATCH, TIMEOUT_ASYNC_APIGW, TIMEOUT_PROV_CONCURRENCY_INIT, TIMEOUT_OOM_BEFORE_TIMEOUT, TIMEOUT_CHILD_PROCESS, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Lambda function fn-prod-order-handler started\nreturning TaskTimeoutException after the 09:00 traffic peak; 60%\nof invocations now time out at 30s; the rest succeed in 2-4s.\"\nFunctionName: fn-prod-order-handler\nRuntime: nodejs20.x\nTimeout: 30\nMemorySize: 512\nHandler: index.handler\nSnapStart: (not applicable — Node.js)\nVpcConfig: (none)\nFileSystemConfigs: (none)\nLastLogEvents: 1 timeout at \"await dynamodb.put(...).promise()\"\n  retrying (attempt 2 of 3) ... then \"Task timed out after 30.00 seconds\"\nCaller: Step Functions task with TimeoutSeconds: 30"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, TaskTimeoutException, Task timed out, timeout, init phase, cold start, SnapStart, provisioned concurrency, SDK retry, exponential backoff, retry storm, HTTP client, connect timeout, RDS Proxy, database connection, VPC ENI, hyperplane ENI, EFS mount, Step Functions, API Gateway 504, async 202, OOM before timeout, child process, X-Ray trace, p99 Duration, troubleshooting
  tags: lambda, compute, troubleshooting, timeout, init-phase, cold-start, sdk-retry, http-client, vpc, efs, step-functions, xray
---

# Lambda Timeout Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  Every invocation times out at exactly Timeout with the same last log
  line → TIMEOUT_DOWNSTREAM / TIMEOUT_HTTP_CLIENT; timeout with zero
  application log lines → TIMEOUT_INIT_PHASE; bursty timeouts correlated
  with traffic peaks → TIMEOUT_SDK_RETRY_STORM / TIMEOUT_DB_CONNECTION;
  Step Functions `Task` `States.Timeout` → TIMEOUT_STEP_FUNCTIONS_MISMATCH;
  API Gateway 504 on sync invoke → TIMEOUT_ASYNC_APIGW; first invocation
  of provisioned alias times out → TIMEOUT_PROV_CONCURRENCY_INIT;
  MaxMemoryUsed ≈ MemorySize alongside timeout → TIMEOUT_OOM_BEFORE_TIMEOUT.
- **The init phase has its own timeout budget.** Lambda's init phase
  (cold start) shares the configured Timeout with the invoke phase. A
  Java/Spring function with a 7-second init and a 5-second configured
  Timeout fails on every cold start with `TaskTimeoutException` and zero
  application logs — the handler never ran. SnapStart (Java) eliminates
  this entirely by restoring from a snapshot in 50-200 ms.
- **SDK retries multiply the worst-case wall clock.** AWS SDK v3 default
  is 3 retries with exponential backoff. A Lambda with Timeout:30s
  calling a downstream that hangs 9s per attempt sees 9+0.1+9+0.2+9+0.4
  ≈ 28s before the final attempt even starts — the SDK burns the budget
  while the function appears "stuck on one call." Set SDK `maxAttempts: 0`
  and let Lambda-level retries handle failure recovery.
- **HTTP clients ship with no connect timeout by default.** `axios`,
  Node `fetch`, Python `requests` default to no connect timeout — a dead
  host consumes the entire Lambda Timeout on a single TCP SYN. Always
  pass an explicit `{ timeout: 3000 }` (axios) or `Timeout(connect=0.5,
  read=3)` (requests) config.
- **VPC cold-start ENI latency was eliminated in 2019.** Hyperplane ENIs
  are pre-provisioned shared resources; a VPC-attached Lambda no longer
  pays per-function ENI creation on cold start. If a 2019 blog post or
  legacy runbook claims "VPC attachment adds 10s cold start for ENI
  creation," it is outdated — do NOT declare TIMEOUT_VPC_ENI without
  positive evidence.
- **OOM masquerades as timeout.** A function that hits MemorySize near
  the Timeout boundary may be killed by the OOM killer before the
  service's timeout SIGKILL fires — CloudWatch shows Duration ≈ Timeout
  AND MaxMemoryUsed ≈ MemorySize. Always cross-check both metrics before
  declaring TIMEOUT_CONFIG.

## Mindset

A `TaskTimeoutException` is the Lambda service telling you the function
exceeded its wall-clock budget. The configured `Timeout` is rarely the
fix — it is the boundary. The actual root cause is what consumed the
budget: init phase, downstream call, retry multiplier, HTTP client
default, DB handshake, or another layer. Senior serverless engineers
raise the timeout only as a stopgap; they identify the budget consumer.

## Philosophy

Five behaviours separate a senior Lambda engineer from a generalist on
timeout incidents:

- **The init phase has its own wall clock, separate from the handler's.**
  Lambda measures init (runtime startup, module load, static
  initialisers) and invoke (handler execution) against the same Timeout
  budget. On a cold start the service kills the function at the
  configured Timeout even if the kill happens during init — the handler
  never runs, no application logs appear, and operators chase "function
  returns no logs" instead of "init exceeded the budget."

- **The SDK retry multiplier is the most under-diagnosed timeout cause.**
  AWS SDK v3 (Node) and boto3 (Python) ship with `maxRetries: 3` and
  exponential backoff. A transiently slow downstream (throttled DynamoDB,
  rate-limited API) consumes 3x the per-call latency before the function
  gives up. Operators who "raise the timeout" without checking SDK
  `maxRetries` keep paying the multiplier on every invocation.

- **Hyperplane ENIs eliminated VPC cold-start latency in 2019.** The
  AWS re:Invent 2019 announcement moved VPC-attached Lambda to shared
  Hyperplane ENIs. Pre-2019 runbooks ("VPC attachment adds 10s cold
  start") are wrong; VPC-attached cold starts now add 100-500 ms.

- **Step Functions has its own timeout that fires BEFORE Lambda's.** A
  `Task` state with `TimeoutSeconds: 30` fails the execution at 30 s
  with `States.Timeout` even if the Lambda function's configured Timeout
  is 60 s. The Lambda keeps running and may succeed, leaving the Step
  Functions execution failed with no Lambda-side error.

- **API Gateway returns 504 before Lambda's timeout on sync invokes.**
  REST APIs and HTTP APIs cap at 29 s — both hard caps, not configurable.
  A Lambda with Timeout:60s invoked synchronously via API Gateway
  receives a 504 at 29s from the caller while the function continues
  for another 31 s and may succeed.

## Quick reference — timeout triage table

| Symptom pattern | Most likely layer | First probe |
|---|---|---|
| Every invocation times out at exactly Timeout; same last log line | TIMEOUT_DOWNSTREAM | CloudWatch Duration p99 vs Timeout; downstream service metrics |
| Timeout with ZERO application log lines | TIMEOUT_INIT_PHASE | CloudWatch `InitDuration`; SnapStart / Runtime; MemorySize |
| Bursty timeouts correlated with traffic peaks | TIMEOUT_SDK_RETRY_STORM | Log lines "retrying (attempt N of M)"; SDK `maxRetries` config |
| "await axios.get(...)" then nothing | TIMEOUT_HTTP_CLIENT | axios/fetch/requests config for connect & read timeouts |
| "Connection acquired" / "Connecting to DB" then nothing | TIMEOUT_DB_CONNECTION | DB max_connections, RDS Proxy presence, TLS handshake time |
| Step Functions `States.Timeout` on Lambda Task | TIMEOUT_STEP_FUNCTIONS_MISMATCH | Step Functions `TimeoutSeconds` vs Lambda `Timeout` |
| API Gateway 504 on sync invoke; Lambda continues | TIMEOUT_ASYNC_APIGW | API Gateway 29s cap vs Lambda Timeout |
| First invocation of provisioned alias times out | TIMEOUT_PROV_CONCURRENCY_INIT | `ProvisionedConcurrencySpilloverInvocations`; SnapStart on Java |
| MaxMemoryUsed ≈ MemorySize alongside timeout | TIMEOUT_OOM_BEFORE_TIMEOUT | CloudWatch MemoryUtilization; raise memory first |
| "spawning child process" then nothing | TIMEOUT_CHILD_PROCESS | fork/exec overhead; `child_process.exec` timeout |
| EFS mount then nothing | TIMEOUT_EFS_MOUNT | FileSystemConfigs; EFS `MountStatus`; cross-AZ mount |
| None of the above, regional Lambda event | INSUFFICIENT_DATA → escalate | AWS Health `describe-events` |

## Pre-flight: function state and gather-info gate

### Pre-flight commands

```bash
# 1. Function configuration
aws lambda get-function-configuration \
  --function-name <name-or-arn> --qualifier <alias-or-version> --output json

# 2. Duration and InitDuration metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Average,p99,p99.9,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# 3. Recent timeouts with surrounding context
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Task timed out"' --output json

# 4. X-Ray trace for the slowest invocations
aws xray get-trace-summaries \
  --service-name <name> --start-time $(date -d '-30 minutes' +%s) \
  --end-time $(date +%s) --response-time --output json
```

If the input is malformed (missing FunctionName, absent symptom, no
REPORT log line or Duration metric), emit INSUFFICIENT_DATA with the
missing pieces (qualifier, Timeout, Duration p99/Maximum, last log
line before each `Task timed out` entry).

## Process — Timeout diagnostic decision tree

The tree is symptom-driven. Pick the entry point based on the observed
pattern, then walk the probes in order. **Never emit ROOT_CAUSE_IDENTIFIED
without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change timeout diagnosis

- **The configured `Timeout` covers init AND invoke.** On a cold start
  the init phase counts against the same budget. A Java function with
  `InitDuration: 4500 ms` and `Timeout: 5000 ms` has only 500 ms of
  invoke budget.

- **SnapStart eliminates the init phase wall-clock cost.** With SnapStart
  enabled (Java 11/17/21), init runs once at version-publish time; cold
  starts restore from snapshot in 50-200 ms. SnapStart is the FIRST fix
  for any Java init-phase timeout.

- **The SDK retry multiplier is invisible without log inspection.** AWS
  SDK v3 logs retries at `INFO` as `"Retrying request ... attempt N of
  M"`. Without SDK logging enabled, the function appears to hang on a
  single call; in reality, it made 3 attempts with backoff.

- **`requestTimeout` and `connectTimeout` are different knobs.** In
  AWS SDK v3, `requestTimeout` is per HTTP attempt; `connectTimeout` is
  the TCP handshake budget. In axios, `timeout` is the entire request
  budget but `connect` is separate.

- **Provisioned concurrency init has its own failure mode.** When
  provisioned concurrency can't initialise N environments, spillover
  invocations fall through to on-demand — every spillover is a cold
  start. Watch `ProvisionedConcurrencySpilloverInvocations`.

- **OOM can fire before timeout on memory-proportional workloads.** A
  function near MemorySize when killed shows `Duration ≈ Timeout` AND
  `MemoryUtilization: 100`. The layer is TIMEOUT_OOM_BEFORE_TIMEOUT,
  not TIMEOUT_CONFIG.

- **Step Functions `Task.TimeoutSeconds` defaults to 60 and is
  per-attempt.** A `Task` with `Retry: [{MaxAttempts: 2}]` has the
  TimeoutSeconds budget per attempt, not total.

- **API Gateway's 29 s cap is on the integration, not the method.** The
  Lambda continues to its own Timeout; API Gateway discards the response.

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom | Branch |
|---|---|
| Every invocation times out; `Duration.Maximum == Timeout`; same last log line | Step 2 |
| Timeout with ZERO application log lines; `InitDuration` > 1s | Step 3 |
| Bursty timeouts; "retrying (attempt N of M)" in logs | Step 4 |
| Last log is `axios.get` / `fetch` / `requests.get` | Step 5 |
| Last log is "Connecting to DB" / "Connection acquired" | Step 6 |
| Caller is Step Functions; `States.Timeout` on `Task` | Step 7 |
| Caller is API Gateway; 504 to client | Step 8 |
| Provisioned alias; spillover invocations time out | Step 9 |
| `MaxMemoryUsed` ≈ `MemorySize` alongside timeout | Step 10 |
| VPC / EFS / child process | Step 11 |
| None of the above | Step 12 |

### Step 2: TIMEOUT_CONFIG vs TIMEOUT_DOWNSTREAM

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{Timeout, MemorySize, Runtime}'
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics p99,p99.9,Maximum --output json
```

Decision rule:
- `p99` and `Maximum` both ≈ `Timeout` on every invocation → TIMEOUT_CONFIG
  (timeout too low). Fix: raise Timeout.
- `p99` just above Timeout but `p50` well below → TIMEOUT_DOWNSTREAM
  (intermittent downstream latency). Fix: address the downstream.
- `Maximum == Timeout` but `p99` well below → bursty failure under load →
  check Step 4 (SDK retry) and Step 5 (HTTP client).

### Step 3: TIMEOUT_INIT_PHASE — init exceeds the budget

Symptom: TaskTimeoutException with ZERO application log lines on cold
starts. Warm invocations succeed. `InitDuration` is high.

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --filter-pattern '"Init Duration"' \
  --start-time $(date -d '-1 hour' +%s)000 --output json

aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{SnapStart: .SnapStart, Runtime, MemorySize}'
```

| Function profile | Verdict / fix |
|---|---|
| Java 11/17/21, SnapStart not enabled | ROOT_CAUSE_IDENTIFIED, `TIMEOUT_INIT_PHASE`. Fix: enable SnapStart (`--snap-start ApplyOn=PublishedVersion`) and publish a new version. |
| Non-Java with heavy init | ROOT_CAUSE_IDENTIFIED, `TIMEOUT_INIT_PHASE`. Fix: raise MemorySize; defer heavy module loads to first invoke. |
| Container function with > 500 MB image | ROOT_CAUSE_IDENTIFIED, `TIMEOUT_INIT_PHASE`. Fix: reduce image size. |

### Step 4: TIMEOUT_SDK_RETRY_STORM — exponential backoff multiplier

Symptom: bursty timeouts correlated with traffic peaks. Logs contain
"Retrying request ... attempt N of M" before the kill.

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern '"Retrying request"' --output json
```

AWS SDK v3 default is `maxRetries: 3`. With exponential backoff, worst-
case wall clock is `(maxRetries + 1) × requestTimeout + sum(backoff)`.
For `requestTimeout: 9000`, this is ~28s on a Lambda with `Timeout: 30`.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TIMEOUT_SDK_RETRY_STORM`.

Fixes:
- Set SDK `maxAttempts: 0` and let Lambda / Step Functions handle retries.
- Or set `requestTimeout: <Timeout / (maxRetries + 1) - headroom>`.
- Or move to async invocation so attempt failures don't consume wall clock.

### Step 5: TIMEOUT_HTTP_CLIENT — missing connect/read timeouts

Symptom: last log line is an outbound HTTP call (`axios.get`, `fetch`,
`requests.get`) then nothing. Function hangs on a dead or slow host.

| Client | Default connect timeout | Default request timeout |
|---|---|---|
| Node `axios` | none (TCP default ~75s on Linux) | none |
| Node `fetch` (undici) | none | none |
| Python `requests` | none (system default) | none |
| Python `httpx` | 5s | none |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TIMEOUT_HTTP_CLIENT`.

```javascript
// axios — Node: pass explicit timeout
await axios.get(url, { timeout: 3000, proxy: false });
```
```python
# requests — Python: pass (connect, read) tuple
requests.get(url, timeout=(0.5, 3.0))
```

### Step 6: TIMEOUT_DB_CONNECTION — handshake overhead without RDS Proxy

Symptom: last log line is "Connecting to DB" / "Connection acquired"
then nothing. DB itself is healthy (low CPU, low load).

```bash
aws rds describe-db-proxies --output json
```

If no RDS Proxy exists and the function opens a new connection per
invocation (outside module scope), each invocation pays 200-1500 ms for
TCP + TLS + auth. Under concurrency, this compounds.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TIMEOUT_DB_CONNECTION`.

Fixes: add RDS Proxy; move connection to module scope; use Aurora
Serverless v2 with pooling.

### Step 7: TIMEOUT_STEP_FUNCTIONS_MISMATCH — Task timeout < Lambda timeout

Symptom: Step Functions execution fails with `States.Timeout` on a
`Task` invoking Lambda. The Lambda's own CloudWatch shows Duration <
Timeout (it completed) OR Duration ≈ Step Functions TimeoutSeconds.

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn <arn> --output json | jq '.definition'
```

`Task.TimeoutSeconds` (default 60) fires at the configured value
regardless of the Lambda function's own `Timeout`.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TIMEOUT_STEP_FUNCTIONS_MISMATCH`.

Fix: align `Task.TimeoutSeconds ≥ Lambda Timeout + 5s`, OR use
`.waitForTaskToken` integration for long-running async work.

### Step 8: TIMEOUT_ASYNC_APIGW — API Gateway 29s cap

Symptom: client receives 504 from API Gateway; Lambda's own logs show
the function completed successfully at, e.g., 35 s.

| Caller | Hard cap | Tunable? |
|---|---|---|
| API Gateway REST API | 29 s | No |
| API Gateway HTTP API | 29 s | No |
| ALB | 60 s default | Yes (1-4000 s) |
| Step Functions | per `Task.TimeoutSeconds` | Yes |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TIMEOUT_ASYNC_APIGW`.

Fix: redesign as async (Event invocation type) so client receives 202
immediately; OR break work into smaller Step Functions tasks under 29 s.

### Step 9: TIMEOUT_PROV_CONCURRENCY_INIT — provisioned alias spillover

Symptom: invocations to a provisioned-concurrency alias intermittently
time out at init. `ProvisionedConcurrencySpilloverInvocations` > 0.

```bash
aws lambda list-provisioned-concurrency-configs \
  --function-name <name> --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ProvisionedConcurrencySpilloverInvocations \
  --dimensions Name=FunctionName,Value=<name>,Name=Resource,Value=<alias> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TIMEOUT_PROV_CONCURRENCY_INIT`.

Fixes: raise provisioned concurrency allocation; enable SnapStart (Java);
reduce image size (container).

### Step 10: TIMEOUT_OOM_BEFORE_TIMEOUT — OOM masquerades as timeout

Symptom: `Duration ≈ Timeout` AND `MaxMemoryUsed ≈ MemorySize` on the
same invocations. The OOM killer fires before the timeout SIGKILL.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

If `MemoryUtilization: 100` correlates with timeouts, the layer is
`TIMEOUT_OOM_BEFORE_TIMEOUT`. Fix: raise `MemorySize` first (also
raises CPU proportion — 1 vCPU at 1769 MB, 6 vCPU at 10240 MB).

### Step 11: TIMEOUT_VPC_ENI, TIMEOUT_EFS_MOUNT, TIMEOUT_CHILD_PROCESS

- **TIMEOUT_VPC_ENI** — VPC cold-start ENI latency is eliminated by
  Hyperplane ENIs (2019+). Only diagnose with positive evidence (service
  event, no hyperplane ENI, route-table misconfiguration). Do NOT
  diagnose from pre-2019 runbooks.

- **TIMEOUT_EFS_MOUNT** — `FileSystemConfigs` populated; first
  invocation times out at EFS mount. Cross-AZ EFS mounts add 1-3 s;
  same-AZ is < 500 ms. Verify EFS access point and mount target AZ.

- **TIMEOUT_CHILD_PROCESS** — `child_process.exec` / `subprocess.run`
  without explicit `timeout` inherits the Lambda Timeout. Fork+exec on
  128 MB environments can be 500-1000 ms per spawn. Pass explicit
  `{ timeout: <ms> }`.

### Step 12: INSUFFICIENT_DATA / escalate

If no probe produced a positive match, emit INSUFFICIENT_DATA with the
specific missing pieces, OR escalate to AWS Support if a regional Lambda
event is present in `aws health describe-events`.

## Output format

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
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <name> in <region>. Proceed?
  (yes/no)"
```

### Worked example — SDK retry storm

```text
TARGET: fn-prod-order-handler (alias: prod, version 18)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: AWS SDK v3 default maxRetries: 3 with exponential backoff on a
  DynamoDB call where the table is throttled (200 WCU on 5000 WCU
  demand). Each of the 3 attempts takes ~9s; total wall clock per
  invocation is ~28s against a 30s Lambda Timeout. Logs show "Retrying
  request ... attempt 2 of 3" and "attempt 3 of 3" before each kill.
LAYER: TIMEOUT_SDK_RETRY_STORM
EVIDENCE:
  - Symptom: 60% of invocations time out at exactly 30s during the 09:00
    traffic peak; off-peak invocations complete in 2-4s.
  - Probe: aws logs filter-log-events returns "Retrying request ...
    attempt 2 of 3" preceding 87% of "Task timed out" entries.
  - Probe: aws cloudwatch WriteThrottleEvents for orders-table shows
    sustained throttling during the same window.
  - Passing: MemoryUtilization Maximum = 28% (not OOM); SnapStart n/a
    (Node.js); no VPC attachment; no HTTP client call.
REMEDIATION:
  1. Set SDK maxAttempts: 0 in the DynamoDB client constructor:
     const ddb = new DynamoDBClient({ maxAttempts: 0 });
  2. Switch the table to on-demand billing:
     aws dynamodb update-table --table-name orders-table \
       --billing-mode PAY_PER_REQUEST --profile <p>
  3. Optionally raise Lambda Timeout to 60s as defence-in-depth.
CONFIRM: Before updating the table or function, emit and await:
  "CONFIRM: About to switch orders-table to PAY_PER_REQUEST and update
   fn-prod-order-handler SDK maxAttempts. Proceed? (yes/no)"
```

Additional worked examples (init-phase SnapStart, Step Functions
mismatch) appear in `examples/README.md`.

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom.

- NEVER recommend raising the timeout without checking memory first.
  CPU scales with memory; CPU-bound timeouts resolve with a memory bump.

- NEVER diagnose TIMEOUT_VPC_ENI based on legacy runbooks. Hyperplane
  ENIs (2019+) eliminated per-function ENI creation. Only diagnose with
  positive evidence.

- NEVER conflate Step Functions `Task.TimeoutSeconds` with Lambda
  `Timeout`. Step Functions fires `States.Timeout` at the Task-level
  value regardless of the Lambda's own budget.

- NEVER assume an HTTP client has a default connect timeout. axios,
  Node fetch, Python requests, and urllib3 all default to NO connect
  timeout — a dead host consumes the entire Lambda budget on one SYN.

- NEVER ignore the SDK retry multiplier. AWS SDK v3 defaults to 3
  retries with exponential backoff; a slow downstream consumes 3x the
  per-call latency. Set `maxAttempts: 0` on hot paths.

- NEVER conclude "function has no logs, must be a Lambda bug" without
  checking `InitDuration`. Init-phase timeout produces zero application
  logs because the handler never ran.

- NEVER enable SnapStart on a non-Java function. SnapStart is Java-only
  on supported managed runtimes (Corretto 11/17/21).

- NEVER treat API Gateway 504 as a Lambda failure. API Gateway fires
  504 at 29 s while the Lambda continues to its own Timeout.

- NEVER assume OOM can't masquerade as timeout. Always cross-check
  `MemoryUtilization` AND `Duration` before declaring TIMEOUT_CONFIG.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-function-configuration`, `publish-version`, `update-alias`,
  `update-state-machine`), emit and await operator approval.

- **Read-only first.** Every probe is read-only. Do not perform
  state-changing operations as diagnostic probes.

- **Raising Timeout** is safe; lowering can cause new failures.

- **Raising MemorySize** is safe; CPU proportion increases with memory.

- **Enabling SnapStart** requires a new version publish; only newly
  published versions benefit.

- **Provisioned concurrency** is billed per-second. Start small and
  scale based on spillover metrics.

- **Step Functions state-machine update** triggers a new revision;
  in-flight executions continue on the prior revision.

## Remediation guidance

### For TIMEOUT_CONFIG — timeout too low

```bash
aws lambda update-function-configuration --function-name <name> \
  --timeout <new> --profile <p>
```
Range: 1-900 seconds. For operations > 29 s, consider async invocation.

### For TIMEOUT_DOWNSTREAM — downstream slow

- DynamoDB: switch to on-demand or raise WriteCapacityUnits.
- S3: multipart upload for large objects; check bucket region.
- RDS: add RDS Proxy; check max_connections; slow queries.
- External HTTP: client-side retry with explicit connect/read timeouts.

### For TIMEOUT_INIT_PHASE

- Java 11/17/21: enable SnapStart and publish a new version.
- Non-Java: raise MemorySize; defer heavy module loads to first invoke.
- Container: reduce image size below 500 MB compressed.

### For TIMEOUT_SDK_RETRY_STORM

```javascript
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const client = new DynamoDBClient({ maxAttempts: 0 });
```
```python
from botocore.config import Config
config = Config(retries={'max_attempts': 0})
client = boto3.client('dynamodb', config=config)
```

### For TIMEOUT_HTTP_CLIENT

```javascript
await axios.get(url, { timeout: 3000 });
```
```python
requests.get(url, timeout=(0.5, 3.0))
```

### For TIMEOUT_DB_CONNECTION

Add RDS Proxy; move connection to module scope; use Aurora Serverless v2.

### For TIMEOUT_STEP_FUNCTIONS_MISMATCH

Align `Task.TimeoutSeconds ≥ Lambda Timeout + 5s`. Or use
`.waitForTaskToken` for long-running async work.

### For TIMEOUT_ASYNC_APIGW

Move to async invocation (Event type); break work into smaller tasks.

### For TIMEOUT_PROV_CONCURRENCY_INIT

Raise provisioned concurrency; enable SnapStart (Java); reduce image size.

### For TIMEOUT_OOM_BEFORE_TIMEOUT

```bash
aws lambda update-function-configuration --function-name <name> \
  --memory-size <new> --profile <p>
```
Target ≥ 20% headroom over observed `MaxMemoryUsed`.

## Domain

AWS CloudOps / Lambda Serverless Compute, Timeout Diagnostics, SDK Retry
Behaviour, Step Functions Integration, and API Gateway Integration.

## AWS documentation

- **AWS Lambda Developer Guide — Configuring function timeout** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html
- **Lambda execution environment and runtime** — https://docs.aws.amazon.com/lambda/latest/dg/runtimes-context.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html
- **Provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html
- **AWS SDK for JavaScript v3 — Retries** — https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/Package/-aws-sdk-util-retry/
- **boto3 retries** — https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html
- **Step Functions Task timeouts** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
- **API Gateway limits** — https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html
- **RDS Proxy** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html
- **AWS X-Ray** — https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html
