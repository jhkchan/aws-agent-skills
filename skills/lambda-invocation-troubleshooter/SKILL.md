---
name: lambda-invocation-troubleshooter
description: 'Diagnoses AWS Lambda invocation failures through an eight-category diagnostic tree: TaskTimeoutException (timeout config vs slow downstream), Runtime.ExitError out-of-memory (MaxMemoryUsed vs MemorySize; CPU scales with memory), cold-start init latency (SnapStart, provisioned concurrency), AccessDenied from execution role (CloudTrail, simulate-principal-policy), VPC connectivity (NAT Gateway, VPC endpoint, SG), environment variable KMS decrypt errors and unset variables, invocation-type mismatch (sync caller timeout vs async retry / DLQ / destination), and ECR container image pull errors (image URI, repo policy, size). Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_FOUND, NEED_MORE_INFO, or ESCALATE.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and function configuration. Live-account diagnosis uses aws lambda get-function-configuration, aws logs get-log-events / filter- log-events, aws lambda get-policy, aws ec2 describe-security-groups, aws lambda get-event-source-mapping, aws lambda get-function-url, aws kms describe-key, aws ecr describe-repositories / get-repository-policy, aws...
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
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing a Lambda function invocation failure (timeout, OOM, AccessDenied, cold-start latency, network error, env var decrypt error, async retry storm, container image pull failure), walking a symptom to the failed layer with verify and fix commands, validating why an application's invocation returns an error, or triaging a "the Lambda is broken" page where the root cause may be config, execution role, network, runtime, or container registry — not necessarily the function code itself.
  when_not_to_use: Code-level debugging of the function handler (use the application logs and a debugger), CloudFront/Lambda@Edge origin issues (use the CloudFront distribution logs), Step Functions orchestration debugging (use the Step Functions execution history), IAM policy authoring for the execution role (use iam-least-privilege-advisor), or VPC route table / NACL posture audits (use ec2-security-group-auditor). This skill diagnoses invocation-time failures; it does not tune handler code or audit steady-state configuration posture.
  activation_triggers: Lambda TaskTimeoutException, Task timed out, Lambda out of memory, Runtime.ExitError, Lambda cold start, init duration, Lambda AccessDenied, execution role denied, Lambda cannot reach internet, Lambda cannot reach S3, Lambda VPC timeout, Lambda environment variable KMS, Lambda decrypt error, Lambda async retry storm, EventSourceMapping retry, Lambda container image pull, ECR image pull error, Lambda Provisioned concurrency, troubleshoot Lambda invocation
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "function returns 502", "async invocations are retried forever"), optionally paired with the function configuration (get-function-configuration output) and recent CloudWatch logs, OR (b) a FunctionName plus caller context (invocation type, source ARN, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER ∈ {TIMEOUT_CONFIG, TIMEOUT_DOWNSTREAM, MEMORY_CONFIG, COLD_START, PERMISSION_EXECUTION_ROLE, PERMISSION_RESOURCE_POLICY, VPC_CONNECTIVITY, VPC_ENDPOINT, ENV_VAR_KMS, ENV_VAR_MISSING, INVOCATION_ASYNC, INVOCATION_SYNC, ECR_IMAGE, ECR_POLICY, RUNTIME_UNSUPPORTED, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Lambda function fn-prod-processor was invoked 200 times\nin the last hour; 30 returned TaskTimeoutException after 30s; the\nrest succeeded.\"\nFunctionName: fn-prod-processor\nRuntime: nodejs20.x\nTimeout: 30\nMemorySize: 256\nHandler: index.handler\nLastLogEvents: 1 timeout at \"await dynamodb.put(...).promise()\"\n  followed by \"Task timed out after 30.00 seconds\"\nInvocation type: RequestResponse (sync), called from API Gateway"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, TaskTimeoutException, Runtime.ExitError, out of memory, cold start, init duration, SnapStart, provisioned concurrency, AccessDenied, execution role, simulate-principal-policy, VPC, NAT Gateway, VPC endpoint, environment variable, KMS decrypt, invocation type, EventSourceMapping, DLQ, destination, container image, ECR, image pull, troubleshooting
  tags: lambda, compute, troubleshooting, invocation, timeout, oom, cold-start, iam-role, vpc, kms, ecr
---

# Lambda Invocation Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  TaskTimeoutException → TIMEOUT_CONFIG / TIMEOUT_DOWNSTREAM / VPC_CONNECTIVITY;
  Runtime.ExitError / OOM → MEMORY_CONFIG; high p99 init duration on first
  invocation → COLD_START; AccessDenied → PERMISSION_EXECUTION_ROLE /
  PERMISSION_RESOURCE_POLICY; function cannot reach internet / AWS service →
  VPC_CONNECTIVITY / VPC_ENDPOINT; "Could not decrypt KMS" / decrypt error →
  ENV_VAR_KMS; "variable is not defined" → ENV_VAR_MISSING; async retries
  forever / DLQ fills → INVOCATION_ASYNC; sync caller times out →
  INVOCATION_SYNC; ECR image pull / ImagePullFailure → ECR_IMAGE / ECR_POLICY.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_FOUND verdict requires
  positive evidence — a failing probe that matches the symptom — not a
  process of elimination that "must be the timeout."
- **Memory on Lambda is not just RAM — it is also CPU.** Lambda allocates
  CPU proportional to memory (linear up to 6 vCPUs at 10 GB). A function
  that times out at 128 MB often succeeds at 512 MB with no code change,
  because the CPU proportion doubles and the bottlenecked compute-bound
  step runs faster. Always cross-check Duration against MemorySize before
  recommending a higher timeout.
- **Sync (RequestResponse) and async (Event) invocations fail in very
  different ways.** Sync fails with whatever the function throws back to
  the caller (timeout, 502, error payload). Async retries twice (by
  default), routes failures to a DLQ or OnFailure destination, and never
  surfaces the error to the caller. Operators debugging async with sync
  tooling miss the retry storm entirely.
- **ESCALATE for AWS-side incidents.** A regional Lambda or ECR outage,
  KMS key inaccessible because the key material was deleted, or a service
  event in AWS Health is not customer-fixable — escalate to AWS Support
  and surface the event ARN.

## Mindset

A failing Lambda invocation is usually a configuration or runtime
environment incident wearing a code costume. The handler is fine in the
majority of cases; the broken thing is timeout, memory, role, network
egress, environment decryption, invocation semantics, or image
distribution. Treat the function code as innocent until the config, role,
network, and runtime layers are proven clean. Senior serverless engineers
do not start by reading the handler; they start with
`get-function-configuration` and the most recent log stream, and only
open the handler once config and runtime are confirmed correct.

## Philosophy

Four behaviours separate a senior Lambda engineer from a generalist:

- **The error type drives the diagnostic order.** A `TaskTimeoutException`
  tells you the function was killed by the Lambda service at the configured
  timeout — that is a config or downstream-latency problem, not a code
  bug. An `Runtime.ExitError` with `ErrorType:OutOfMemory` tells you the
  runtime container exceeded its memory allocation — that is a memory
  sizing problem. A `ResourceNotFoundException` from the SDK inside the
  logs tells you the function code ran but the downstream resource was
  unreachable — that is a permissions or network problem. Routing the
  symptom to the wrong layer is the #1 source of wasted cycles in
  Lambda incidents.
- **Lambda VPC connectivity is the inverse of EC2 VPC connectivity.** An
  EC2 instance in a public subnet reaches the internet via the IGW. A
  Lambda function in a public subnet has NO internet access — there is no
  ENA for the function in a public subnet to bind to a public IP. A
  Lambda function reaches the internet ONLY when placed in a private
  subnet with a route to a NAT Gateway. Operators who "just put the
  function in the default VPC" often discover the function cannot reach
  external APIs because the default VPC is public. Always check the
  subnet route table for a NAT route when the symptom is "function
  cannot reach the internet."
- **Cold start is a per-environment, not a per-function, phenomenon.**
  Each unique (code + configuration + execution environment) tuple has
  its own warm pool. A function with two alias versions (PROD, STAGE)
  has two warm pools. SnapStart (Java only) pre-initialises the runtime
  against a snapshot; provisioned concurrency pre-Initialises N execution
  environments. A function with provisioned concurrency on one alias but
  not another shows cold starts only on the un-provisioned alias.
  Operators measuring "the function has a 3s cold start" without
  qualifying which alias, version, and traffic class see noisy
  measurements and chase ghosts.
- **Async retries are silent and exponential.** Lambda async invokes
  (Event invocation type) retry twice after the first failure: immediate,
  then +1 minute, then +2 minutes (default). The caller has already
  received a 202 and moved on — the retries happen entirely server-side.
  Without a DLQ or OnFailure destination configured, the failed events
  vanish. Operators who "don't see the retries" are looking at the caller
  logs; they need to look at the function's own `Errors` metric and the
  throttling / DLQ metrics.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Task timed out after X seconds`, `TaskTimeoutException` | TIMEOUT_CONFIG / TIMEOUT_DOWNSTREAM | `get-function-configuration` (Timeout), CloudWatch Duration vs Timeout, log the last line before kill |
| `Runtime.ExitError`, `ErrorType: OutOfMemory`, `MemorySize` exceeded | MEMORY_CONFIG | CloudWatch `MaxMemoryUsed` vs `MemorySize` |
| First-invocation p99 latency spike; init duration > 1s | COLD_START | CloudWatch `InitDuration`, SnapStart / ProvisionedConcurrency config |
| `AccessDenied`, `is not authorized to perform`, `User: arn:... is not authorized` | PERMISSION_EXECUTION_ROLE | `cloudtrail lookup-events` for the denied API; `iam simulate-principal-policy` on the execution role |
| `Resource: ... is not authorized`, cross-account caller denied | PERMISSION_RESOURCE_POLICY | `lambda get-policy` (resource-based) |
| `connect ETIMEDOUT`, `ECONNREFUSED`, function cannot reach external host | VPC_CONNECTIVITY / VPC_ENDPOINT | `get-function-configuration` (VpcConfig), `describe-route-tables` for the subnet |
| `Could not decrypt KMS`, `KMS.AccessDeniedException`, decrypt error on env var | ENV_VAR_KMS | `get-function-configuration` (KMSKeyArn), `kms describe-key`, execution role `kms:Decrypt` check |
| `ReferenceError: X is not defined`, "environment variable is missing" | ENV_VAR_MISSING | `get-function-configuration` (Environment.Variables) |
| Async invocation: caller sees 202 but downstream state never updates;DLQ fills | INVOCATION_ASYNC | `get-event-source-mapping`, DLQ / destination config, `Errors` metric |
| Sync (API Gateway → Lambda) returns 504 / 502 after X seconds | INVOCATION_SYNC | Caller (API Gateway) timeout vs Lambda Timeout |
| `ImagePullFailure`, `ECR image ... not found`, container Lambda fails to initialise | ECR_IMAGE / ECR_POLICY | `get-function-configuration` (PackageType: Image, Code.ImageUri), `ecr describe-images`, `ecr get-repository-policy` |
| None of the above, weird runtime error, region-wide event | ESCALATE | `aws health describe-events` + AWS Service Health Dashboard |

## Pre-flight: function state and gather-info gate

Before running symptom-specific probes, gather the canonical function
configuration and short-circuit on function states that mimic invocation
failures. Misclassifying these produces hours of timeout debugging for a
problem that is not a timeout problem.

### Account-wide pre-flight commands

```bash
# 1. Function configuration (Runtime, Handler, Timeout, MemorySize,
#    Role, VpcConfig, Environment, KMSKeyArn, PackageType, ImageConfig,
#    State, LastUpdateStatus, Layers)
aws lambda get-function-configuration \
  --function-name <name-or-arn> --qualifier <alias-or-version> --output json

# 2. Recent CloudWatch log events (the function's own log group)
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Task timed out" OR "OutOfMemory" OR "AccessDenied" OR "ECONNREFUSED"' \
  --output json

# 3. Resource-based policy (who can invoke this function)
aws lambda get-policy --function-name <name> --output json 2>/dev/null || \
  echo "No resource-based policy"

# 4. CloudWatch invocation metrics (Errors, Throttles, Duration, ConcurrentExecutions)
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 5. AWS Health (regional events, scheduled runtime deprecations)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Function-state short-circuit

| `State` / `LastUpdateStatus` | Effect on diagnosis |
|---|---|
| `Active` + `LastUpdateStatus: Successful` | Proceed with symptom-driven diagnosis. |
| `Pending` / `InProgress` | A function update is in flight. New invocations may use old or new code; some configurations cannot be re-applied mid-update. Note in REMEDIATION; wait for `Active` before drawing conclusions. |
| `Failed` + `LastUpdateStatus: Failed` | The last update failed; the function runs the previous revision. The `LastUpdateStatusReason` field names the failure (often a permission error on the role, an invalid layer ARN, or an unreachable ECR image). Treat as root-cause evidence for any symptom that began at the LastModified timestamp. |
| `Inactive` | The function has been idle long enough that Lambda has freed its execution environments. The next invocation is a cold start. Do NOT declare an outage. |
| Runtime deprecated (Node 16, Python 3.7, etc.) | AWS has deprecated the runtime; the function still runs but will be force-decommissioned on the published date. Plan a runtime upgrade; do not debug as an outage. |

### Alias / version pre-flight

| Field | Effect |
|---|---|
| `Qualifier: <alias>` resolves to a different version than `Qualifier: $LATEST` | Caller invokes one version; operator debugs another. Always include the qualifier when reading config. |
| Provisioned concurrency configured on `<alias>` but not on `$LATEST` | Cold-start symptoms appear only on traffic to `$LATEST` or to an un-provisioned alias. |
| Routing config (weighted alias) splits traffic 90/10 between two versions | A "small percentage of invocations fail" pattern is one version broken; check both. |

If the input is malformed (missing FunctionName, absent symptom
description, no caller context for live diagnosis), emit:

```text
TARGET: <function-name or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum a symptom
  description (the error string or observed behaviour) and the
  FunctionName (with qualifier if the function uses aliases).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed symptom, (2) the FunctionName and qualifier (alias or
  version), and (3) for live diagnosis, the invocation type (sync
  RequestResponse vs async Event) and the caller context (source ARN,
  source service).
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior Lambda engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **Lambda CPU scales with memory, linearly.** At 128 MB the function
  receives ~0.083 vCPU; at 1,769 MB it receives 1 full vCPU; at 10,240 MB
  it receives 6 vCPUs. A compute-bound function (JSON parsing, crypto,
  image processing) that times out at 256 MB frequently succeeds at 1 GB
  with NO code change — the CPU proportion quadrupled and the
  bottlenecked step ran in a quarter of the time. Operators who "raise
  the timeout" instead of the memory are paying for longer wall-clock
  execution without addressing the bottleneck.

- **`TaskTimeoutException` is emitted by the Lambda service, not the
  function.** The service sends SIGKILL to the container at the configured
  timeout; the function gets no chance to clean up. The last log line
  before the kill is the best evidence of where time was spent. A timeout
  with no preceding log line means the cold-start init itself exceeded
  the timeout — a Java function with a 5-second timeout and a 7-second
  init fails on every cold start with `TaskTimeoutException` and zero
  application logs.

- **Cold-start init duration is NOT application latency.** A function
  with `InitDuration: 4500 ms` and `Duration: 50 ms` has a 50 ms
  application cost; the 4500 ms is one-time per execution environment.
  Operators who add the two together and report "the function takes 4.5
  seconds" overstate p99 latency by orders of magnitude. Always read
  `InitDuration` and `Duration` as separate metrics.

- **SnapStart is Java-only and requires a code-deploy cycle to enable.**
  SnapStart takes a memory snapshot of the initialised runtime and
  restores it for each new execution environment, reducing init duration
  from seconds to milliseconds. It is only available for Java 11+ on
  supported managed runtimes. Python and Node do not benefit (their init
  is already fast). Operators enabling SnapStart on a Node function see
  zero benefit and assume SnapStart is broken.

- **Provisioned concurrency costs money per-second regardless of
  invocations.** It pre-initialises N execution environments and bills
  them as `ProvisionedConcurrencySpilloverInvocations` once traffic
  exceeds N. It is the right tool for cold-start-sensitive workloads
  (sync API-facing functions); it is the wrong tool for async batch
  processing where a 2-second cold start is acceptable.

- **Cross-account Lambda invocation requires BOTH the caller's
  identity-based `lambda:InvokeFunction` AND the function's
  resource-based policy listing the caller.** Same-account requires only
  one. Operators who "added the IAM permission to the caller" but still
  see AccessDenied from a cross-account caller miss the resource-based
  policy side.

- **A Lambda function in a VPC has NO internet access unless a NAT
  Gateway exists in the route table.** This is the inverse of EC2 and
  surprises every operator the first time. The function in a public
  subnet also has no internet — public subnets route to the IGW, but
  Lambda functions do not get a public IP, so traffic to the IGW has
  no return path. Always place Lambda in a private subnet when VPC
  attachment is needed.

- **VPC-attached Lambda functions reach AWS services (S3, DynamoDB,
  SQS, etc.) over the public service endpoint by default — which means
  they need a NAT Gateway to reach them.** The cheaper, more secure
  alternative is a VPC endpoint (Gateway or Interface) for the service.
  A function that can reach DynamoDB but not S3 is a classic pattern:
  DynamoDB has a Gateway endpoint (free, automatic), S3 also does, but
  many other services require an Interface endpoint (hourly charge).

- **KMS-encrypted environment variables require `kms:Decrypt` on the
  execution role for the CUSTOMER MANAGED key only.** If the function
  uses the default Lambda service key (`aws/lambda`), no `kms:Decrypt`
  permission is required — Lambda decrypts transparently. Operators who
  add `kms:Decrypt` permissions for the service-managed key are chasing
  a non-issue; operators who rotate to a customer-managed key without
  adding `kms:Decrypt` to the role break every invocation.

- **Container-image Lambda functions pull the image at init time, not at
  invocation time.** A 5 GB image takes 30-60 seconds to pull on a cold
  start, dwarfing the application's compute time. Image pull happens
  once per execution environment lifecycle; warm invocations do not
  re-pull. Operators who report "function is slow" with a large image
  are paying the pull cost on every cold start.

- **`PackageType: Image` functions have a 10 GB compressed image size
  cap.** Above the cap, the function cannot be created or updated. The
  practical performance ceiling is much lower — images above 500 MB
  introduce visible init latency on every cold start.

- **Event-source mapping (SQS, Kafka, DynamoDB Streams, Kinesis) has
  its own retry semantics that differ from async invokes.** A failed
  batch is retried in full up to `MaximumRetryAttempts`; on exhaustion,
  the partial-item failure is sent to an `OnFailure` destination
  (if configured) or discarded. `BisectBatchOnFunctionError` and
  `MaximumBatchingWindowInSeconds` further shape the retry behaviour.
  Operators who debug event-source failures as if they were async
  retries miss the batch-level semantics.

- **Lambda Layers are versioned and immutable, but a function references
  a specific Layer version by ARN.** Deleting a Layer version does not
  affect existing functions that reference it, but a function update
  that re-resolves the ARN fails if the version was deleted. Operators
  who "deleted the old Layer to clean up" break the next deploy.

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the eight categories, route to Step 9 (ESCALATE
or NEED_MORE_INFO).

| Symptom | Branch |
|---|---|
| `Task timed out after X seconds` (sync or async); CloudWatch shows Duration == Timeout | Step 2 — Timeout |
| `Runtime.ExitError` / `ErrorType: OutOfMemory` / "MemorySize exceeded" | Step 3 — OOM |
| First invocation(s) of an execution environment slow; `InitDuration` > 1s | Step 4 — Cold start |
| `AccessDenied`, `is not authorized`, "execution role denied" | Step 5 — Permissions |
| `connect ETIMEDOUT`, `ECONNREFUSED`, "cannot reach S3/internet/DB" | Step 6 — VPC connectivity |
| `Could not decrypt KMS`, `decrypt error`, `ReferenceError: X is not defined` | Step 7 — Environment variables |
| Async invocations retried forever / DLQ fills; sync caller returns 5xx after X seconds | Step 8 — Invocation type |
| `ImagePullFailure`, container Lambda fails to initialise | Step 8b — Container image |
| None of the above | Step 9 — Escalate / NEED_MORE_INFO |

### Step 2: TaskTimeoutException — timeout diagnostic tree

Symptom: the Lambda service killed the function at the configured
timeout. CloudWatch invocation record shows `Duration` approximately
equal to `Timeout`. The last log line before the kill is the best
evidence of where time was spent.

#### 2a: Read the timeout config and the actual duration

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{Timeout, MemorySize, Runtime, Handler, LastUpdateStatus}'
```

The configured `Timeout` is the wall-clock cap. Cross-reference against
CloudWatch `Duration`:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Average,Maximum --output json
```

If `Maximum` Duration consistently hits the configured `Timeout` exactly
(e.g., both at 30000 ms), the function is being killed every invocation.
This is timeout-bound. If `Maximum` is below the `Timeout` but
`TaskTimeoutException` appears in logs, the function occasionally exceeds
the timeout — investigate intermittent downstream latency.

#### 2b: Identify the slow operation

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern '"Task timed out"' --output json
```

Read the log stream immediately before each `Task timed out` entry. The
last application log line names the slow operation:

| Last log line | Likely cause |
|---|---|
| `await dynamodb.put(...).promise()` then nothing | DynamoDB PutItem slow — check table capacity (on-demand vs provisioned), WCU throttling, cross-region calls. |
| `await s3.getObject(...).promise()` then nothing | S3 GetObject slow — check object size, bucket region (cross-region), VPC endpoint configuration. |
| `await axios.get('https://...')` then nothing | External HTTP call slow — check if function is VPC-attached without NAT (the call never reaches the host). |
| `Connection acquired from pool` then nothing | Database call slow — check connection pool size, DB instance class, max_connections, Security Group. |
| `console.log('start')` then nothing | Init itself exceeded the timeout — see Step 4 (cold start). Common for Java with low timeout config. |
| No log lines at all | Init exceeded the timeout BEFORE the handler ran. SnapStart disabled (Java), large container image pull, or a heavy static initialiser. |

#### 2c: Distinguish config timeout from downstream timeout

- **Config timeout:** the timeout value is too low for the operation's
  p99 latency. Raising the timeout is the correct fix. Verify with the
  CloudWatch `Duration` p99 — if p99 is just above the timeout, the
  function needs more headroom.
- **Downstream timeout:** the timeout value is reasonable (e.g., 30s)
  but the downstream call genuinely takes that long because of an
  external issue (DB hot, dependency 5xx, missing VPC endpoint causing
  NAT processing latency). The fix is to address the downstream issue,
  not raise the timeout indefinitely.

If raising memory (Step 3 logic) makes the timeout disappear without
addressing the downstream issue, MEMORY_CONFIG is the verdict, not
TIMEOUT_CONFIG — the function was CPU-bound, not waiting on I/O.

#### 2d: VPC-induced timeout (a special downstream case)

A function in a VPC without a route to the destination appears to
"hang" on the first outbound call. Symptoms look identical to a
downstream timeout. Jump to Step 6 to verify VPC config before
declaring TIMEOUT_CONFIG.

**Verdicts:**
- Timeout too low for normal operation: ROOT_CAUSE_FOUND,
  `LAYER: TIMEOUT_CONFIG`. Fix: raise the timeout (1-900 seconds).
- Downstream genuinely slow: ROOT_CAUSE_FOUND,
  `LAYER: TIMEOUT_DOWNSTREAM`. Fix: address the downstream (DB
  capacity, dependency error rate, VPC endpoint).
- CPU-bound (raising memory fixes it): ROOT_CAUSE_FOUND,
  `LAYER: MEMORY_CONFIG`. Fix: raise memory.

### Step 3: Out-of-memory — Runtime.ExitError

Symptom: CloudWatch invocation record shows `MemorySize` exceeded.
Logs contain `Runtime.ExitError`, `ErrorType: OutOfMemory`, or "FATAL
ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript heap out of
memory" (Node).

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.MemorySize'

aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern 'OutOfMemory' --output json
```

Cross-reference against `MaxMemoryUsed`:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

`MemoryUtilization: 100` (per CloudWatch) confirms the function hit its
cap. The fix is to raise `MemorySize`:

```bash
aws lambda update-function-configuration \
  --function-name <name> --memory-size <new> --profile <p>
```

**Memory-size guidance:**
- 128 MB: smallest legal value; ~0.083 vCPU; suitable for tiny I/O-bound
  workloads only.
- 512 MB: ~0.24 vCPU; common for light SDK calls.
- 1769 MB: 1 full vCPU; common for compute-bound workloads.
- 3072 MB: ~1.75 vCPU; a useful spot for Java/JVM functions.
- 10240 MB: 6 vCPU; the practical max for heavily parallel compute.

A note on leaks: if `MaxMemoryUsed` grows linearly across invocations
within the same execution environment (visible in CloudWatch logs as
`REPORT RequestId: X ... Max Memory Used: 90MB` increasing per request),
the function has a memory leak in module-scoped state. Raising memory
delays the OOM but does not fix the leak. Recommend a code review for
module-level caches that grow unbounded.

**Verdict:** ROOT_CAUSE_FOUND, `LAYER: MEMORY_CONFIG`. Fix: raise
memory to a value with ≥20% headroom over observed `MaxMemoryUsed`.

### Step 4: Cold start — high init duration

Symptom: p99 latency on the first invocation of each new execution
environment is elevated; subsequent invocations on the same environment
are fast. CloudWatch invocation logs show `Init Duration` > 1 second
(Node/Python) or > 5 seconds (Java/.NET).

```bash
# Confirm the init duration is the cost
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --filter-pattern '"Init Duration"' \
  --start-time $(date -d '-1 hour' +%s)000 --output json | \
  jq '.events[].message' | tail -10
```

Cross-check mitigation config:

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{SnapStart: .SnapStart, Runtime, MemorySize, Layers}'

aws lambda list-provisioned-concurrency-configs --function-name <name> --output json
```

**Mitigation decision tree:**

| Function profile | Recommended mitigation |
|---|---|
| Java 11+ on a supported runtime | **SnapStart** — reduces init from seconds to milliseconds. Must be enabled and a new version published; existing versions do not retroactively benefit. |
| Any runtime, sync-facing, cold-start-sensitive | **Provisioned Concurrency** on the alias — pre-initialises N execution environments. Billed per-second regardless of invocations. |
| Cold start acceptable (async batch, background jobs) | None — accept the one-time cost. Raising memory shrinks init linearly for CPU-bound init paths (heavy DI frameworks, large module loading). |
| Container-image function with large image | Reduce image size. Use multi-stage builds, slim base images, exclude dev dependencies. |
| Heavy Layer stack | Audit Layer sizes; a 50 MB Layer adds measurable init cost on every cold start. |

**SnapStart caveat.** SnapStart restores the same memory snapshot to
every new execution environment. Code that captures unique-per-instance
state at init time (random UUIDs, network connections, cached timestamps)
behaves identically across all "fresh" environments — operators see the
same UUID generated for every invocation. Use `afterRestore` hook (AWS
SDK) to re-initialise unique state per environment.

**Verdict:**
- Cold start is the cost, no mitigation configured, function is sync /
  latency-sensitive: ROOT_CAUSE_FOUND, `LAYER: COLD_START`. Fix: enable
  SnapStart (Java) or provisioned concurrency (any runtime).
- Cold start is the cost, mitigation IS configured but qualifier is
  wrong (e.g., provisioned concurrency on $LATEST while traffic goes to
  a version): ROOT_CAUSE_FOUND, `LAYER: COLD_START`. Fix: align the
  provisioned concurrency with the invoked qualifier.

### Step 5: AccessDenied — execution role and resource policy

Symptom: function logs show an AWS SDK call returned AccessDenied.
Common strings: `AccessDenied`, `User: arn:aws:sts::... is not
authorized to perform: <service>:<action>`, `Client.UnauthorizedOperation`,
`KMS.AccessDeniedException`.

#### 5a: CloudTrail lookup for the exact denied API

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=<api-call> \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --profile <p> --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("<execution-role-arn>"))'
```

The CloudTrail event identifies:
- The exact denied action (e.g., `s3:GetObject`, `dynamodb:PutItem`).
- The exact denied resource ARN (including path).
- Whether the deny was explicit (`errorMessage` mentions "explicit deny")
  or implicit.
- The source IP (for VPC endpoint policy or IP-conditional issues).

#### 5b: Execution-role policy check

```bash
# Get the execution role ARN
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Role'

# List the role's managed and inline policies
ROLE_NAME=$(echo <role-arn> | cut -d/ -f2)
aws iam list-attached-role-policies --role-name <role-name> --output json
aws iam list-role-policies --role-name <role-name> --output json
```

Cross-reference against the denied action. If the role's policies do
not include the action on the resource ARN, **ROOT_CAUSE_FOUND** with
`LAYER: PERMISSION_EXECUTION_ROLE`.

For high-confidence verification:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <execution-role-arn> \
  --action-names <service>:<action> \
  --resource-arns <resource-arn> \
  --output json --profile <p>
```

`implicitDeny` = the role policy lacks the action.
`explicitDeny` = a Deny statement in SCP, role policy, permissions
boundary, or session policy matches.

#### 5c: Cross-account / cross-service resource policy check

If the function calls a resource in another account OR another service
calls the function cross-account, both sides of the policy must allow.

```bash
# Function's resource-based policy (who can invoke this function)
aws lambda get-policy --function-name <name> --output json 2>/dev/null
```

If a cross-account caller is denied and the resource-based policy does
not list the caller, **ROOT_CAUSE_FOUND** with
`LAYER: PERMISSION_RESOURCE_POLICY`. Add a statement allowing
`lambda:InvokeFunction` (or `lambda:InvokeAsync`) to the cross-account
caller's principal.

#### 5d: Common permission failure patterns

| Pattern | Cause |
|---|---|
| Function fails after a secrets rotation to a new CMK | Execution role missing `kms:Decrypt` on the new key. |
| Cross-account caller denied | Resource-based policy on the function does not list the caller's account/ARN. |
| Function can read but not write to S3 | Identity-based policy has `s3:GetObject` but not `s3:PutObject`. |
| Function fails after VPC endpoint added | VPC endpoint policy restricts the action; bypass the endpoint to verify. |
| Function fails only when assumed via a session policy | The session policy narrows effective permissions. Inspect `userIdentity.sessionContext` in CloudTrail. |
| Service-linked role missing (e.g., `lambda.amazonaws.com` cannot create ENI) | Function needs `AWSLambdaVPCAccessExecutionRole` managed policy for VPC attachment. |

### Step 6: VPC connectivity — function cannot reach network target

Symptom: function logs show `connect ETIMEDOUT`, `ECONNREFUSED`,
`ENOTFOUND`, or "cannot reach X" for any external host or AWS service.

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.VpcConfig'
```

`VpcConfig` populated → the function is VPC-attached. `VpcConfig` empty
or null → the function is NOT in a VPC and has direct internet access
(over the Lambda-managed network).

#### 6a: If function is VPC-attached, check the route table

```bash
# Subnet IDs from VpcConfig
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<subnet-id-1> <subnet-id-2> --output json | \
  jq '.RouteTables[].Routes'
```

- For internet-bound traffic (external APIs): must have a route to a
  NAT Gateway (`nat-...`) or NAT Instance. A route to `igw-...` does
  NOT work for Lambda (the function has no public IP).
- For private service endpoints (S3, DynamoDB): must have a route to
  a VPC Gateway endpoint (`vpce-...` for S3/DynamoDB Gateway) or an
  Interface endpoint ENI for other services.

If no route exists for the destination, **ROOT_CAUSE_FOUND** with
`LAYER: VPC_CONNECTIVITY`. Fix: add a NAT Gateway route for internet,
or a VPC endpoint route for AWS services.

#### 6b: Security group egress check

```bash
aws ec2 describe-security-groups --group-ids <sg-from-vpc-config> --output json | \
  jq '.SecurityGroups[].IpPermissionsEgress'
```

The function's SG must allow outbound to the destination. The default
egress is allow-all (0.0.0.0/0 on all ports); a locked-down SG can
silently drop traffic.

#### 6c: VPC endpoint policy check (for AWS service calls)

For Interface endpoints:

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> --output json | \
  jq '.VpcEndpoints[] | {ServiceName, Policy, State}'
```

A VPC endpoint policy can deny specific actions even when IAM allows
them. Bypass the endpoint (route over the NAT or internet) to verify.

#### 6d: Service-specific VPC endpoint guidance

| Service | Endpoint type | Cost | Notes |
|---|---|---|---|
| S3 | Gateway (free) | Free | Route table entry, automatic |
| DynamoDB | Gateway (free) | Free | Route table entry, automatic |
| SQS, SNS, KMS, Secrets Manager, STS, etc. | Interface (hourly + per-GB) | Paid | Creates ENIs in the subnet; SG rules apply |
| PrivateLink (custom services) | Interface | Paid | NLB-backed; consumer side needs endpoint SG allow |

For an Interface endpoint, the function's SG must allow outbound to the
endpoint's ENI (typically the endpoint's own SG allows the function's SG).

**Verdicts:**
- Function in public subnet (route to IGW, no NAT): ROOT_CAUSE_FOUND,
  `LAYER: VPC_CONNECTIVITY`. Fix: move to a private subnet with a NAT
  Gateway route.
- Function in private subnet but no NAT and no VPC endpoint:
  ROOT_CAUSE_FOUND, `LAYER: VPC_CONNECTIVITY`. Fix: add a NAT Gateway
  OR add a VPC endpoint.
- VPC endpoint policy denies the action: ROOT_CAUSE_FOUND,
  `LAYER: VPC_ENDPOINT`. Fix: scope the endpoint policy to allow the
  action.

### Step 7: Environment variable — KMS and missing variables

Symptom: function fails to start, or fails at the line that reads
`process.env.X`. Common strings: `Could not decrypt KMS`, `KMS.AccessDeniedException`,
`decrypt error`, `ReferenceError: X is not defined`.

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{Environment, KMSKeyArn}'
```

#### 7a: KMS decrypt failure

If `KMSKeyArn` points at a customer-managed key:

```bash
aws kms describe-key --key-id <key-arn> --output json | \
  jq '.KeyMetadata.{KeyState, KeyManager, Enabled}'

# Execution role has kms:Decrypt on the key?
aws iam simulate-principal-policy \
  --policy-source-arn <execution-role-arn> \
  --action-names kms:Decrypt \
  --resource-arns <key-arn> \
  --output json --profile <p>
```

If the role lacks `kms:Decrypt` on the customer-managed key,
**ROOT_CAUSE_FOUND** with `LAYER: ENV_VAR_KMS`. Fix: add
`kms:Decrypt` on the key ARN to the execution role.

If the key state is `Disabled` or `PendingDeletion`, the function
cannot decrypt any encrypted env var. **ROOT_CAUSE_FOUND** with
`LAYER: ENV_VAR_KMS`. Fix: re-enable the key or migrate env vars to
a new key.

If `KMSKeyArn` is the default (`aws/lambda` AWS-managed key), no
`kms:Decrypt` permission is required — Lambda decrypts transparently.
Look elsewhere.

#### 7b: Missing environment variable

If the function logs `ReferenceError: X is not defined` (Node) or
`KeyError: 'X'` (Python) on `process.env.X` / `os.environ['X']`:

- Cross-reference the variable name against `Environment.Variables` in
  the config.
- If the variable is missing from config, **ROOT_CAUSE_FOUND** with
  `LAYER: ENV_VAR_MISSING`. Fix: add the variable via
    `update-function-configuration --environment Variables={X=value}`.
- If the variable is present in config but the function still fails,
  the deployment environment differs from local — check the qualifier
  ($LATEST vs published version vs alias) and confirm the config the
  caller invoked matches.

#### 7c: Stage / alias environment differences

Aliases can override environment variables per alias. The function
invoked with `qualifier: prod` may have different env vars than the same
function invoked with `qualifier: stage`. Always read config with the
qualifier the caller used.

### Step 8: Invocation type mismatch — async vs sync

#### 8a: Async retry storm

Symptom: caller receives 202 immediately, but downstream state never
updates. CloudWatch `Errors` metric spikes; DLQ (if any) fills.

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{DeadLetterConfig, DestinationConfig, RevisionId}'

aws lambda get-event-source-mapping --function-name <name> --output json 2>/dev/null
```

For async-invoked functions, check:

| Config field | Effect |
|---|---|
| `DeadLetterConfig.TargetArn` | The ARN (SNS or SQS) where failed events land after retries exhaust. Empty = events vanish on exhaustion. |
| `DestinationConfig.OnFailure.Destination` | The ARN where each failed event is sent. Empty = no destination. |
| `DestinationConfig.OnSuccess.Destination` | Optional; rarely configured. |
| EventSourceMapping (for SQS/Kafka/Streams) | The mapping has its own retry config (`MaximumRetryAttempts`, `BisectBatchOnFunctionError`). |

Async retry sequence (default):
1. Immediate retry on failure.
2. Wait 1 minute, retry.
3. Wait 2 minutes, retry.
4. If all fail and DLQ configured, event goes to DLQ.
5. If all fail and OnFailure destination configured, event goes to
   destination.
6. If neither, event vanishes.

Common async failure patterns:

| Pattern | Cause |
|---|---|
| DLQ fills with the same payload hundreds of times | A specific payload shape causes the function to throw deterministically. Inspect a DLQ message for the failure reason. |
| `Errors` spikes 3x for each failed invocation | Three retries all failing; expected behaviour. |
| DLQ empty, no destination, downstream state missing | Events are vanishing. Add a DLQ immediately for visibility. |
| EventSourceMapping retries forever | `MaximumRetryAttempts` is unset or very high; partial batch keeps failing. Configure `BisectBatchOnFunctionError` to isolate the bad record. |

**Verdict:** ROOT_CAUSE_FOUND, `LAYER: INVOCATION_ASYNC`. Fix:
- If no DLQ/destination: add one (SQS or SNS).
- If a specific payload causes deterministic failure: fix the function
  code OR add defensive error handling.
- If EventSourceMapping retries forever: tune `MaximumRetryAttempts` and
  `BisectBatchOnFunctionError`.

#### 8b: Sync caller timeout (API Gateway → Lambda)

Symptom: API Gateway returns 504 Gateway Timeout or 502 Bad Gateway.
Lambda function completes within its timeout, but the caller has already
given up.

```bash
# Lambda timeout
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Timeout'

# API Gateway timeout is fixed at 30 seconds (REST API) or 29 seconds
# (HTTP API). Verify the integration:
aws apigateway get-method --rest-api-id <id> --resource-id <id> \
  --http-method ANY --output json 2>/dev/null
```

Common patterns:

| Pattern | Cause |
|---|---|
| Lambda Timeout = 60s, API Gateway returns 504 at 30s | Caller (API Gateway) gives up before Lambda does. Lower Lambda Timeout to ≤ 29s, or redesign as async. |
| Lambda Duration p99 = 5s but occasional 504s | API Gateway integration timeout or downstream of API Gateway (ALB, CloudFront) timing out. |
| Lambda returns 502 (internal lambda error) | Function throws an unhandled exception; the error response shape does not match API Gateway's expected format. |

**Verdict:** ROOT_CAUSE_FOUND, `LAYER: INVOCATION_SYNC`. Fix: align
timeouts (Lambda Timeout ≤ API Gateway's cap), or move the workload
to async if the operation legitimately exceeds 29s.

### Step 8b: Container image — ECR pull failures

Symptom: function fails to initialise. Logs show `ImagePullFailure`,
`ECR image ... not found`, `ImagePullBackOff`, or
`Runtime.ExitError`.

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{PackageType, Code: .Code, ImageConfig}'
```

`PackageType: Image` indicates a container-image function. The image
URI is in `Code.ImageUri`.

#### 8b.1: Verify the image exists in ECR

```bash
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag> \
  --output json --profile <p>
```

If `ImageNotFoundException`, **ROOT_CAUSE_FOUND** with `LAYER: ECR_IMAGE`.
Fix: re-push the image to ECR with the correct tag, or update the
function's ImageUri to match an existing tag.

#### 8b.2: Verify the image size

```bash
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag> \
  --output json | jq '.imageDetails[].imageSizeInBytes'
```

Lambda caps compressed image size at 10 GB. Above 500 MB compressed,
init duration suffers noticeably. Above the cap, the function fails to
create/update.

**Verdict:** ROOT_CAUSE_FOUND, `LAYER: ECR_IMAGE`. Fix: reduce image
size (multi-stage build, slimmer base image, exclude dev dependencies).

#### 8b.3: Verify ECR repository policy grants Lambda access

For cross-account functions (function in account A, image in account B):

```bash
aws ecr get-repository-policy --repository-name <repo> --output json --profile <p>
```

The policy must grant `ecr:BatchGetImage` and `ecr:GetDownloadUrlForLayer`
to the Lambda service principal in account A. If the policy is missing
or scoped to the wrong account, **ROOT_CAUSE_FOUND** with
`LAYER: ECR_POLICY`. Fix: add a statement to the ECR repo policy
granting the function's account access.

Same-account functions get automatic ECR access via the Lambda service
principal — no policy needed.

#### 8b.4: Verify the entry point / command

For container functions, `ImageConfig.Command` (the entry point args)
must match the image's expected runtime. A mismatch produces
`Runtime.ExitError` immediately at init.

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.ImageConfig'
```

If the image's `ENTRYPOINT` expects `app.handler` but `ImageConfig.Command`
points at `index.handler`, **ROOT_CAUSE_FOUND** with `LAYER: ECR_IMAGE`.
Fix: update `ImageConfig.Command` to match the image.

### Step 9: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the symptom
clearly indicates an AWS-side incident (region event, ECR outage, KMS
outage, runtime deprecation forcing shutdown), emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN,
  the function's State and LastUpdateStatus, and the relevant
  CloudTrail error. Recommend opening a Support case. Do NOT continue
  diagnosing; the cause is outside the customer's control.
- **NEED_MORE_INFO** — A specific probe requires operator input. List
  the missing pieces (qualifier / alias, invocation type, caller
  context, recent deploy timestamps) and the next probe to run once the
  info is available.

## Output format

```text
TARGET: <function-name with qualifier>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <TIMEOUT_CONFIG | TIMEOUT_DOWNSTREAM | MEMORY_CONFIG |
        COLD_START | PERMISSION_EXECUTION_ROLE |
        PERMISSION_RESOURCE_POLICY | VPC_CONNECTIVITY | VPC_ENDPOINT |
        ENV_VAR_KMS | ENV_VAR_MISSING | INVOCATION_ASYNC |
        INVOCATION_SYNC | ECR_IMAGE | ECR_POLICY |
        RUNTIME_UNSUPPORTED | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <name> in <region>. Proceed?
  (yes/no)"
```

### Worked example — TaskTimeoutException, downstream DB slow

```text
TARGET: fn-prod-processor (alias: prod, version 42)
VERDICT: ROOT_CAUSE_FOUND
REASON: Function's Timeout is 30s; CloudWatch Duration p99 is 28.5s and
  Maximum is 30s (function is killed at the cap). The last log line
  before each kill is "await dynamodb.put(...)" — the DynamoDB PutItem
  is the slow operation. The table's WriteCapacityUnits is set to 100
  on a provisioned table sustaining 5000 WCU of demand; requests are
  being throttled (Step 2b/2c).
LAYER: TIMEOUT_DOWNSTREAM
EVIDENCE:
  - Symptom: 30% of invocations return TaskTimeoutException after
    exactly 30.00 seconds; the remaining 70% succeed in 1-3s.
  - Probe: aws logs filter-log-events returns "Task timed out after
    30.00 seconds" 47 times in the last hour; the preceding log line
    in every case is "Putting item to orders-table".
  - Probe: aws cloudwatch get-metric-statistics on
    aws/dynamodb WriteThrottleEvents for orders-table shows sustained
    throttling in the same hour.
  - Passing: function Memory is 512 MB; MemoryUtilization Maximum is
    65% (memory is not the issue); function is not VPC-attached
    (network is not the issue); function role has dynamodb:PutItem
    on the table (permissions are not the issue).
REMEDIATION:
  1. Switch the table to on-demand (pay-per-request) billing mode to
     absorb the burst, OR raise WriteCapacityUnits to match observed
     demand:
     aws dynamodb update-table --table-name orders-table \
       --billing-mode PAY_PER_REQUEST --profile <p>
  2. Optionally raise the Lambda Timeout to 60s as defence-in-depth
     against transient spikes:
     aws lambda update-function-configuration --function-name \
       fn-prod-processor --timeout 60 --profile <p>
  3. Verify by re-invoking and watching CloudWatch Duration over the
     next 30 minutes.
CONFIRM: Before updating the table or function, emit and await:
  "CONFIRM: About to switch orders-table to PAY_PER_REQUEST and raise
   fn-prod-processor Timeout to 60s. Proceed? (yes/no)"
```

### Worked example — OutOfMemory, memory raised

```text
TARGET: fn-image-resizer (alias: prod, version 7)
VERDICT: ROOT_CAUSE_FOUND
REASON: Function MemorySize is 256 MB; CloudWatch MemoryUtilization is
  100% on invocations with image payloads > 4 MB. Logs show
  "Runtime.ExitError: ErrorType: OutOfMemory" on the same invocations.
  The function reads the full image into memory for resizing (Step 3).
LAYER: MEMORY_CONFIG
EVIDENCE:
  - Symptom: invocations with image payloads > 4 MB fail; smaller
    payloads succeed.
  - Probe: aws logs filter-log-events returns "ErrorType: OutOfMemory"
    12 times in the last hour; all preceding log lines show
    "Processing image of size <4-8 MB>".
  - Probe: aws cloudwatch get-metric-statistics on AWS/Lambda
    MemoryUtilization Maximum = 100 for the same invocations.
  - Passing: function Timeout is 60s; Duration p99 is 1.2s (timeout is
    not the issue); function is not VPC-attached (network is not the
    issue).
REMEDIATION:
  1. Raise MemorySize to 1024 MB (≥4x the largest payload, with
     headroom for the resize operation):
     aws lambda update-function-configuration --function-name \
       fn-image-resizer --memory-size 1024 --profile <p>
  2. Publish a new version and shift the prod alias:
     aws lambda publish-version --function-name fn-image-resizer
     aws lambda update-alias --name prod --function-version <new>
  3. Verify with a 6 MB image payload; Duration should drop (CPU
     proportion triples) and Max Memory Used should be < 800 MB.
```

### Worked example — ESCALATE, regional Lambda incident

```text
TARGET: fn-prod-processor (alias: prod, version 42)
VERDICT: ESCALATE
REASON: Region-wide Lambda invocation failures in us-east-1; AWS Health
  event reports elevated 5xx rates and increased error rates for
  Lambda invoking functions in the region. Customer-side action cannot
  resolve a regional service degradation.
LAYER: UNKNOWN
EVIDENCE:
  - aws health describe-events returns an OPEN event for
    AWS_LAMBDA_SERVICE in us-east-1 starting 14 minutes ago.
  - Function config and recent deploys are unchanged.
  - Failures began at the AWS Health event start time across multiple
    unrelated functions in the account.
REMEDIATION:
  1. Monitor the AWS Health Dashboard for the event resolution
     announcement.
  2. If the function backs a user-facing API, enable failover to a
     different region if architecture permits.
  3. If impact persists beyond the AWS Health ETA, open a Support case
     quoting the AWS Health event ARN.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
  the symptom. A "process of elimination" diagnosis erodes operator
  trust when the real cause is elsewhere.

- NEVER recommend raising the timeout without checking memory first.
  Lambda CPU scales with memory; many timeouts are CPU-bound and
  resolve with a memory increase. Raising the timeout alone pays for
  longer wall-clock without addressing the bottleneck.

- NEVER place a Lambda function in a public subnet for internet
  access. Lambda functions in public subnets have no internet because
  they receive no public IP. Always use a private subnet with a NAT
  Gateway route, or no VPC attachment at all.

- NEVER assume VPC-attached Lambda functions can reach AWS services
  without configuration. S3 and DynamoDB have free Gateway endpoints;
  most other services require Interface endpoints (paid) or a NAT
  Gateway. A function that "could reach DynamoDB yesterday but not
  today" often had the Gateway endpoint deleted or a route changed.

- NEVER add `kms:Decrypt` for the default `aws/lambda` key. The
  service-managed key decrypts transparently; permission is not
  required. Adding it is harmless but indicates the diagnosis went
  down the wrong path. Only customer-managed CMKs require
  `kms:Decrypt`.

- NEVER assume the function's `$LATEST` configuration matches the
  alias a caller invoked. Aliases pin to versions; the version's
  config can differ from `$LATEST`. Always read config with the
  qualifier the caller used.

- NEVER enable SnapStart on a non-Java function. SnapStart is Java-only
  on supported managed runtimes (Corretto 11+). Python and Node have
  fast init already; SnapStart is a no-op or fails silently.

- NEVER conclude "Lambda is slow" without separating `InitDuration`
  from `Duration`. A function with 4500 ms InitDuration and 50 ms
  Duration has 50 ms application latency; the 4500 ms is one-time per
  execution environment. Reporting the sum overstates latency.

- NEVER treat async invocation failures as caller-side errors. The
  caller received 202 and moved on; the retries are entirely
  server-side. Without a DLQ or OnFailure destination, failed events
  vanish. Always check `DeadLetterConfig` and `DestinationConfig`.

- NEVER delete an ECR image tag that a Lambda function references.
  Lambda caches the image digest at function-update time and continues
  to use the cached digest, but the next function update or cold start
  on a fresh execution environment fails to pull. Tag immutability on
  the ECR repo prevents this footgun.

- NEVER cross-account-invoke a Lambda function without configuring
  BOTH sides. The caller's identity-based `lambda:InvokeFunction` AND
  the function's resource-based policy must both allow. Adding only
  one side produces AccessDenied.

- NEVER recommend a container image > 1 GB without flagging the
  cold-start impact. Each cold start pays the pull cost; a 5 GB image
  adds 30-60 seconds of init duration on every fresh execution
  environment.

- NEVER declare the function failed because `LastUpdateStatus:
  Failed` without reading `LastUpdateStatusReason`. The reason field
  names the actual failure (often a role permission, invalid layer
  ARN, or unreachable ECR image) — the function still runs the prior
  revision and the symptom is the failed update, not a runtime
  failure.

- NEVER conflate EventSourceMapping retry semantics with async invoke
  retry semantics. SQS/Kafka/DynamoDB Streams sources have
  batch-level retries (`MaximumRetryAttempts`); async invokes have
  event-level retries (immediate, +1m, +2m). The diagnostic and
  remediation differ.

- NEVER assume a function without a VPC has no network path issues.
  Internet-bound calls go through the Lambda-managed network; rare
  service events can degrade this path. Always check AWS Health if
  multiple functions fail simultaneously with no config change.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-function-configuration`, `publish-version`, `update-alias`,
  `create-event-source-mapping`, `put-repository-policy`), emit and
  await operator approval. Do NOT execute the CLI until the operator
  confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`get-function-configuration`, `filter-log-events`,
  `get-policy`, `describe-*`, `simulate-principal-policy`,
  `lookup-events`). Do not perform state-changing operations as
  diagnostic probes.

- **`update-function-configuration --memory-size`** is safe and
  non-disruptive for memory-only changes; the function continues
  serving traffic from the prior revision until the update completes.

- **`update-function-configuration --timeout`** is safe; raising the
  timeout does not cause disruption. Lowering it can cause new
  failures if invocations legitimately need the prior value.

- **Publishing a version** is non-disruptive; the new version is
  addressable but does not receive traffic until an alias is shifted.

- **Shifting an alias** is the user-visible cutover. Always confirm
  before `update-alias --function-version`. Use weighted alias
  routing for canary deploys.

- **Enabling SnapStart** requires a new version publish and can only
  be set on a function that is NOT currently SnapStart-enabled.
  Existing versions do not retroactively benefit; only new invocations
  of a freshly-published SnapStart-enabled version see the speedup.

- **Provisioned concurrency** is billed per-second. Enabling on a
  high-traffic alias is expensive; start with a small allocation
  (e.g., 5) and scale based on spillover metrics.

- **VPC attachment change** triggers an ENI creation in the target
  subnets; for high-throughput functions this can take 30-60 seconds
  to propagate. Plan the change outside a traffic peak.

- **ECR repo policy changes** affect every consumer of the repo;
  tighten policy gradually, never deny-by-default without confirming
  no Lambda function depends on the repo.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple functions (e.g., a missing
  `kms:Decrypt` after a key rotation), batch remediation into groups
  of at most 5 functions, emit a single CONFIRM per batch, and verify
  between batches.

## Remediation guidance

### For TIMEOUT_CONFIG — timeout too low

```bash
aws lambda update-function-configuration --function-name <name> \
  --timeout <new> --profile <p>
```
Acceptable range: 1-900 seconds. Consider async invocation if the
operation legitimately exceeds 29s (the API Gateway limit).

### For TIMEOUT_DOWNSTREAM — downstream genuinely slow

Address the downstream service:
- DynamoDB: switch to on-demand or raise WriteCapacityUnits.
- S3: use multipart upload for large objects; check bucket region.
- RDS: add RDS Proxy for connection reuse.
- External HTTP: implement client-side retry with exponential backoff;
  consider caching responses.

### For MEMORY_CONFIG — memory too low

```bash
aws lambda update-function-configuration --function-name <name> \
  --memory-size <new> --profile <p>
```
Target ≥ 20% headroom over observed `MaxMemoryUsed`. Note that CPU
proportion increases with memory — a CPU-bound function may resolve
both OOM and timeout symptoms with one memory bump.

### For COLD_START

- Java: enable SnapStart (`--snap-start ApplyOn=PublishedVersion`).
- Any runtime, sync-facing: enable provisioned concurrency on the
  invoked alias.
- Container: reduce image size.
- Generic: raise memory (linearly shrinks CPU-bound init).

### For PERMISSION_EXECUTION_ROLE

Add the minimum-scope permission to the role's identity-based policy:

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name <name> \
  --policy-document '<JSON with specific Action and Resource>'
```
Prefer a new managed policy version over inline edits for audit
history. Verify with `simulate-principal-policy`.

### For PERMISSION_RESOURCE_POLICY

Add a statement to the function's resource-based policy:

```bash
aws lambda add-permission --function-name <name> \
  --statement-id <sid> --action lambda:InvokeFunction \
  --principal <caller-account-id> --output json --profile <p>
```

### For VPC_CONNECTIVITY

- Move function to a private subnet: `update-function-configuration
  --vpc-config SubnetIds=<private>,SecurityGroupIds=<sg>`.
- Add a NAT Gateway in the private subnet's route table.
- Or add a VPC endpoint for the destination AWS service.

### For VPC_ENDPOINT

Update the endpoint policy to allow the denied action. Test by bypassing
the endpoint (route via NAT) to confirm the endpoint is the cause.

### For ENV_VAR_KMS

Add `kms:Decrypt` on the customer-managed key ARN to the execution
role's identity-based policy. Verify with `simulate-principal-policy`.

### For ENV_VAR_MISSING

Add the variable:

```bash
aws lambda update-function-configuration --function-name <name> \
  --environment "Variables={X=value}" --profile <p>
```

### For INVOCATION_ASYNC

- Add a DLQ:
    `update-function-configuration --dead-letter-config TargetArn=<sqs-or-sns-arn>`.
- Or add an OnFailure destination:
    `put-function-event-invoke-config --destination-config ...`.
- For EventSourceMapping: tune `MaximumRetryAttempts` and
  `BisectBatchOnFunctionError`.

### For INVOCATION_SYNC

Align timeouts: Lambda Timeout ≤ caller's timeout. For operations
exceeding 29s, move to async invocation (caller receives 202, function
processes in the background).

### For ECR_IMAGE

- Re-push the image with the correct tag.
- Reduce image size below 10 GB (target < 500 MB for fast cold starts).
- Update `ImageConfig.Command` to match the image's entry point.

### For ECR_POLICY

Add a statement to the ECR repository policy:

```bash
aws ecr set-repository-policy --repository-name <repo> \
  --policy-text '<JSON granting ecr:BatchGetImage and
    ecr:GetDownloadUrlForLayer to the function account>' --profile <p>
```

## Deep reference: Lambda invocation layer model

### Symptom → layer decision matrix (offline classification)

```
Error string                                  → Layer
TaskTimeoutException                          → TIMEOUT_CONFIG / TIMEOUT_DOWNSTREAM
Runtime.ExitError OutOfMemory                 → MEMORY_CONFIG
InitDuration > 1s on first invocation         → COLD_START
AccessDenied / "not authorized"               → PERMISSION_EXECUTION_ROLE
                                               (or PERMISSION_RESOURCE_POLICY
                                               if cross-account)
connect ETIMEDOUT / ECONNREFUSED              → VPC_CONNECTIVITY / VPC_ENDPOINT
Could not decrypt KMS                         → ENV_VAR_KMS
ReferenceError: X is not defined              → ENV_VAR_MISSING
async 5xx but caller got 202; DLQ fills       → INVOCATION_ASYNC
API Gateway 504 / 502                         → INVOCATION_SYNC
ImagePullFailure                              → ECR_IMAGE / ECR_POLICY
```

### Memory-to-CPU mapping

| Memory (MB) | vCPU (approx) | Typical use |
|---|---|---|
| 128 | 0.083 | Light I/O (S3 trigger copy) |
| 256 | 0.17 | SDK calls |
| 512 | 0.24 | API Gateway handlers |
| 1024 | 0.5 | Small JSON processing |
| 1769 | 1.0 | Compute-bound threshold |
| 3072 | 1.75 | Java/JVM |
| 5120 | 3.0 | Parallel compute |
| 10240 | 6.0 | Maximum CPU; heavy parallel compute |

### Async retry timeline (default)

```
T+0s     : invocation fails
T+0s     : immediate retry (1st)
T+60s    : retry (2nd)
T+180s   : retry (3rd) — final
T+180s   : if all 4 attempts failed:
           - DLQ: send to DeadLetterConfig.TargetArn (if set)
           - OnFailure: send to DestinationConfig.OnFailure (if set)
           - else: discard
```

Tunable via `put-function-event-invoke-config`:
`MaximumRetryAttempts` (0-2), `MaximumEventAgeInSeconds` (60-21600).

### EventSourceMapping (SQS/Kafka/Streams) retry semantics

- A failed batch is retried in full up to `MaximumRetryAttempts`
  (default -1 = infinite for SQS, finite for others).
- `BisectBatchOnFunctionError: true` recurses to find the offending
  record in the batch.
- On exhaustion, partial-item failures route to `DestinationConfig`
  if configured; otherwise the source (e.g., SQS visibility timeout
  expiring) handles it.

### Lambda VPC ENI lifecycle

- Pre-2019: each function got its own ENI per subnet; scaled poorly.
- 2019+: Hyperplane ENI — Lambda uses shared Hyperplane ENIs to reach
  customer VPCs; function-specific ENIs are no longer created.
- Removing VPC attachment (`update-function-configuration --vpc-config
  SubnetIds=[]`) deletes any residual ENIs over minutes.
- Function update does NOT propagate immediately; cold starts on new
  execution environments pick up the new VPC config.

## Recent AWS features (2024-2026)

- **SnapStart for Java 21 and above (2024-2025):** Extended runtime
  support; restore-from-snapshot now covers more JVM frameworks.
  Diagnostically, SnapStart must be enabled on a function BEFORE
  publishing a version; existing versions cannot retroactively benefit.
- **Provisioned concurrency pricing simplification (2024):** Flat
  per-hour pricing by memory size; spillover to on-demand priced
  separately. Diagnostically, `ProvisionedConcurrentExecutions` metric
  should be the steady-state target; sustained spillover indicates
  under-provisioning.
- **Lambda container image 10 GB cap (2024):** Raised from 3 GB; large
  ML inference and game-server-style workloads can fit. Cold-start
  cost scales with image size; always audit size before recommending
  container functions.
- **BisectBatchOnFunctionError default-on for SQS (2024-2025):** New
  event source mappings default to bisect-on-error, accelerating the
  isolation of poison-pill records. Older mappings may still have it
  disabled.
- **Lambda runtime deprecation schedule (2024-2025):** Node 16, Python
  3.7, Java 8 (older variants) decommissioned. Functions on these
  runtimes continue to execute but block updates; AWS forces
  decommission on the published date. Plan runtime upgrades before
  the deprecation date.
- **Lambda Response Streaming (2024-2025):** Functions can stream
  responses via Function URL; changes how "first byte" latency is
  measured. Init duration still applies; first-byte latency is
  separate from end-to-end Duration.

## Domain

AWS CloudOps / Lambda Serverless Compute, Invocation Diagnostics,
Execution Role, VPC Networking, and Container Image Distribution.

## AWS documentation

- **AWS Lambda Developer Guide — Configuring Lambda function options** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html
- **Lambda execution environment and runtime** — https://docs.aws.amazon.com/lambda/latest/dg/runtimes-context.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html
- **Provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html
- **Lambda function VPC configuration** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html
- **Lambda environment variables** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
- **Asynchronous invocation** — https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html
- **Lambda container images** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-images.html
- **Lambda IAM execution role** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
