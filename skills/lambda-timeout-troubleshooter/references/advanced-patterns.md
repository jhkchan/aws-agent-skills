# Advanced patterns — lambda-timeout-troubleshooter

Philosophy, Step-0 expert-knowledge behaviours, and per-layer remediation guidance, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Philosophy — five senior behaviours (moved from SKILL.md)

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

## Step 0: Non-obvious behaviours that change timeout diagnosis (moved from SKILL.md)

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

## Remediation guidance (moved from SKILL.md)

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
