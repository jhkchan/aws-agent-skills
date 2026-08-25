# Lambda Invocation Layer Reference Guide

Supplementary reference for the Lambda Invocation Troubleshooter skill.
Loaded on-demand when a diagnostic needs runtime port/semantics,
memory-to-CPU mapping, async retry timelines, VPC endpoint matrix, or
container image sizing rules.

## Memory-to-CPU mapping (Lambda)

Lambda allocates CPU proportionally to memory, linearly up to 6 vCPUs at
10,240 MB. The proportion is approximate — Lambda does not guarantee a
fixed vCPU count, but the following table holds in practice.

| Memory (MB) | vCPU (approx) | Burst credits | Typical use |
|---|---|---|---|
| 128 | 0.083 | n/a | Light I/O (S3 trigger copy, webhook forwarder) |
| 192 | 0.125 | n/a | Minimal SDK calls |
| 256 | 0.17 | n/a | API Gateway thin handlers |
| 512 | 0.33 | n/a | SDK calls + light JSON |
| 1024 | 0.66 | n/a | Mid-size JSON, small image processing |
| 1769 | 1.0 | n/a | Compute-bound threshold (1 full vCPU) |
| 2048 | 1.16 | n/a | Java/JVM without SnapStart |
| 3072 | 1.75 | n/a | JVM with frameworks (Spring) |
| 4096 | 2.34 | Yes | Multi-threaded compute |
| 5120 | 3.0 | Yes | Parallel compute |
| 6144 | 3.5 | Yes | ML inference (small models) |
| 8192 | 4.6 | Yes | Heavy parallel |
| 10240 | 6.0 | Yes | Maximum CPU; heavily parallel compute |

The 1769 MB threshold matters because that is the first memory value
where Lambda grants a full vCPU. Below 1769 MB, the function shares a
vCPU via bursting. Above 1769 MB, the function gets a guaranteed vCPU
allocation.

## Runtime support matrix

| Runtime | SnapStart | Default timeout guidance | Notes |
|---|---|---|---|
| nodejs20.x, nodejs22.x | No | 5-15s typical | Fast init (~100-300 ms) |
| python3.11, python3.12 | No | 5-15s typical | Fast init (~100-300 ms) |
| java21 (Corretto) | Yes | 10-30s typical | Slow init without SnapStart (1-5s) |
| java17 (Corretto) | Yes | 10-30s typical | SnapStart supported |
| java11 (Corretto) | Yes | 10-30s typical | SnapStart supported |
| dotnet8 | No | 5-15s typical | Mid-speed init (~300-800 ms) |
| ruby3.3 | No | 5-15s typical | Fast init |
| provided.al2023 | No | varies | Custom runtime; init depends on implementation |
| container (PackageType: Image) | No | varies | Init includes image pull cost |

## SnapStart requirements

- Runtime: Java 11, 17, or 21 on a managed AWS runtime (Corretto).
- Enable: `update-function-configuration --snap-start
  ApplyOn=PublishedVersion`, then publish a new version.
- Existing versions do NOT retroactively benefit. Only newly published
  versions on a SnapStart-enabled function get snapshots.
- Restore cost: typically 50-200 ms (vs 1-5s without SnapStart).
- Unique-per-instance state must be re-initialised in an `afterRestore`
  runtime hook (AWS SDK hook). Common cases:
  - Network connections (DB, HTTP clients) — re-establish on restore.
  - Random UUIDs generated at init — regenerate on restore.
  - Cached timestamps — refresh on restore.

## Async invocation retry timeline (default)

```
T+0s     : invocation attempt fails
T+0s     : immediate retry (1st retry)
T+60s    : retry (2nd retry)
T+180s   : retry (3rd retry) — final attempt
T+180s   : if all 4 attempts failed:
             - DLQ: send to DeadLetterConfig.TargetArn (if set)
             - OnFailure: send to DestinationConfig.OnFailure (if set)
             - else: discard the event
```

Tunable via `put-function-event-invoke-config`:
- `MaximumRetryAttempts`: 0, 1, or 2 (default 2 → 3 total attempts).
- `MaximumEventAgeInSeconds`: 60 to 21,600 (default 21,600 = 6 hours).

## EventSourceMapping retry semantics (SQS, Kafka, DynamoDB Streams, Kinesis)

| Field | Default | Effect |
|---|---|---|
| `MaximumRetryAttempts` | -1 (SQS) / 10000 (others) | -1 = infinite retry (SQS visibility timeout eventually drops); positive integer = bounded retry count |
| `BisectBatchOnFunctionError` | true (SQS, 2024+) | On batch failure, recurse to isolate the offending record |
| `MaximumBatchingWindowInSeconds` | 0 | Collect records for N seconds before invoking; higher = fewer invocations, more latency |
| `BatchSize` | 10 (SQS) / 100 (Streams) | Records per batch |
| `DestinationConfig.OnFailure` | unset | Where to send records that exhausted retries |
| `FunctionResponseTypes` | `ReportBatchItemFailures` (SQS) | Allows partial-batch failure reporting |

For SQS specifically, partial-batch failure handling requires
`FunctionResponseTypes: [ReportBatchItemFailures]` and the function
returning a `batchItemFailures` list. Without this, a single bad
record poisons the whole batch.

## VPC connectivity matrix

| Destination | VPC-attached Lambda needs |
|---|---|
| Internet (external API) | Private subnet + route to NAT Gateway (or NAT Instance) |
| S3 | S3 Gateway endpoint (free) OR NAT |
| DynamoDB | DynamoDB Gateway endpoint (free) OR NAT |
| SQS, SNS, KMS, Secrets Manager, STS | Interface VPC endpoint (paid, hourly + per-GB) OR NAT |
| RDS / Aurora in same VPC | Route to local subnet (no special config) |
| RDS / Aurora in peered VPC | Active peering + routes both ways + SG allows |
| RDS / Aurora via PrivateLink | Interface endpoint to NLB |
| EC2, ECS, EKS in same VPC | Local routing; SG allows |

### VPC attachment effects

- Pre-2019: each function had its own ENI per subnet; scaling problems.
- 2019+: Hyperplane ENIs — Lambda uses shared Hyperplane ENIs; function-
  specific ENIs are no longer created for VPC attachment.
- Cold start with VPC: typically adds 100-500 ms (Hyperplane ENI lookup);
  negligible compared to Java init.
- Removing VPC attachment: `update-function-configuration --vpc-config
  SubnetIds=[] SecurityGroupIds=[]`. ENIs are cleaned up over minutes.
- A function with NO VpcConfig has direct internet access via the
  Lambda-managed network path (no NAT required).

## KMS key matrix for environment variables

| KMSKeyArn | Execution role needs kms:Decrypt? |
|---|---|
| `aws/lambda` (default, AWS-managed) | No — Lambda decrypts transparently |
| Customer-managed CMK | Yes — `kms:Decrypt` on the key ARN; key policy must also grant the Lambda service principal `lambda:Decrypt` for sts:AssumeRole-style flow |

When migrating from AWS-managed to customer-managed CMK, the role MUST
get `kms:Decrypt` before the KMSKeyArn update. Otherwise every
invocation with an encrypted env var fails immediately.

## Container image limits

| Property | Limit |
|---|---|
| Compressed image size | 10 GB |
| Uncompressed image size | (no hard cap, but watch pull time) |
| ImageConfig.Command (entry point args) | 6 args |
| ImageConfig.EntryPoint (overrides image ENTRYPOINT) | 4 args |
| ImageConfig.WorkingDirectory | path string |
| Pull latency (5 GB compressed) | 30-60 seconds cold start |
| Pull latency (500 MB compressed) | 1-3 seconds cold start |

Recommended image sizes by workload:
- Light API handler: < 200 MB compressed.
- Mid-tier (small framework + SDK): 200-500 MB.
- Heavy (Spring Boot, Java framework): 500 MB-1 GB.
- Very heavy (ML inference bundled): 1-3 GB; cold start cost is real.
- Above 3 GB: consider extracting the heavy bits to a Layer or EFS.

## Sync invocation caller timeout matrix

| Caller | Default timeout | Tunable? |
|---|---|---|
| API Gateway REST API | 29,000 ms | No (hard cap) |
| API Gateway HTTP API | 29,000 ms | No (hard cap) |
| Application Load Balancer | 60,000 ms | Yes (target group: 1-4000s for HTTP, but Lambda caps at function Timeout) |
| Lambda Invoke (direct, sync) | Caller-side only | Caller-side configurable |
| Step Functions (Lambda task) | 60s default | Yes — Step Functions task timeout (1-900s); Lambda Timeout caps |
| CloudWatch Logs subscription | n/a (async) | n/a |
| EventBridge | n/a (async) | n/a |
| S3 event notification | n/a (async) | n/a |

Rule of thumb: Lambda Timeout ≤ caller's timeout, otherwise the caller
gives up before Lambda does. For operations exceeding 29s, design as
async (Event invocation type) and decouple the caller.

## CloudTrail lookup patterns for Lambda AccessDenied

```bash
# Find the denied API called by the execution role
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<function-name> \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("AccessDenied"))'

# Find what API the execution role was denied
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=<execution-role-name> \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json
```

The CloudTrail event contains:
- `eventName`: the denied API (e.g., `GetObject`, `PutItem`).
- `eventSource`: the AWS service (e.g., `s3.amazonaws.com`).
- `requestParameters`: the resource ARN and parameters.
- `errorMessage`: whether the deny was explicit or implicit.
- `sourceIPAddress`: the function's IP at the time of the call (useful
  for `aws:SourceIp` condition mismatches).
- `userIdentity.sessionContext`: the role assumption chain (session
  policies live here).

## Lambda function state transitions

| From | To | Trigger |
|---|---|---|
| (create) | Pending | CreateFunction |
| Pending | Active | Service initialisation complete |
| Active | InProgress | UpdateFunctionConfiguration / Code |
| InProgress | Active | Update completes successfully |
| InProgress | Failed (LastUpdateStatus) | Update fails; function runs prior revision |
| Active | Inactive | Long idle period (Lambda releases execution environments) |
| Inactive | Active | First invocation after idle |

`LastUpdateStatus: Failed` does NOT mean the function is down — it
means the last update failed and the function continues running the
prior revision. The `LastUpdateStatusReason` field explains the update
failure.

## Runtime deprecation timeline (2024-2026)

| Runtime | Deprecation date | Behaviour |
|---|---|---|
| nodejs16.x | 2024-06-12 (disabled) | Functions can no longer be created/updated |
| python3.7 | 2024-12-27 (disabled) | Functions can no longer be created/updated |
| dotnet6 | 2024-12-27 (disabled) | Functions can no longer be created/updated |
| nodejs18.x | 2025-09 (deprecation begins) | Block updates |
| java8.al2 | 2025-12-31 (disabled) | Functions can no longer be created/updated |
| nodejs20.x | Active (current default) | — |
| python3.12 | Active | — |
| java21 | Active | SnapStart supported |

Always check `get-function-configuration` Runtime against the current
deprecation list before declaring a runtime issue.

## AWS Health event categories that affect Lambda

| Category | Likely impact |
|---|---|
| `AWS_LAMBDA_SERVICE` | Region-wide Lambda degradation; multiple functions fail simultaneously |
| `AWS_LAMBDA_RUNTIME_DEPRECATION` | Scheduled runtime decommission; functions on the runtime will be force-stopped |
| `AWS_ECR_SERVICE` | Container Lambda functions fail to pull images |
| `AWS_KMS_ISSUE` | Functions with encrypted env vars fail to decrypt |
| `AWS_REGIONAL_EVENT` | Multiple services affected; broad customer impact |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.

---

### Deep reference: Lambda invocation layer model


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
