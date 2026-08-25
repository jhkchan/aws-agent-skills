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


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Mindset


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Philosophy

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.



Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.



Moved verbatim to [references/worked-examples.md](references/worked-examples.md) — load on demand.


## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

**Verdict:** ROOT_CAUSE_FOUND, `LAYER: MEMORY_CONFIG`. Fix: raise
memory to a value with ≥20% headroom over observed `MaxMemoryUsed`.

### Step 4: Cold start — high init duration

Symptom: p99 latency on the first invocation of each new execution
environment is elevated; subsequent invocations on the same environment
are fast. CloudWatch invocation logs show `Init Duration` > 1 second
(Node/Python) or > 5 seconds (Java/.NET).

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

### Step 6: VPC connectivity — function cannot reach network target

Symptom: function logs show `connect ETIMEDOUT`, `ECONNREFUSED`,
`ENOTFOUND`, or "cannot reach X" for any external host or AWS service.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


### Step 8: Invocation type mismatch — async vs sync

#### 8a: Async retry storm

Symptom: caller receives 202 immediately, but downstream state never
updates. CloudWatch `Errors` metric spikes; DLQ (if any) fills.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


#### 8b: Sync caller timeout (API Gateway → Lambda)

Symptom: API Gateway returns 504 Gateway Timeout or 502 Bad Gateway.
Lambda function completes within its timeout, but the caller has already
given up.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) — load on demand.

### Worked example — ESCALATE, regional Lambda incident

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) — load on demand.

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

Moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.

## Deep reference: Lambda invocation layer model

Moved verbatim to [references/invocation-layer-reference.md](references/invocation-layer-reference.md) — load on demand.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — quick-start rules, mindset, philosophy, Step-0 non-obvious behaviours, recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight CLI, function-state / alias gates, per-step probe commands (Steps 2-8b)
- [references/error-handling.md](references/error-handling.md) — per-layer remediation guidance with CLI
- [references/worked-examples.md](references/worked-examples.md) — malformed-input NEED_MORE_INFO template, OutOfMemory and ESCALATE worked examples
- [references/invocation-layer-reference.md](references/invocation-layer-reference.md) — layer model deep reference: decision matrix, memory-to-CPU, retry timelines, ENI lifecycle

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
