# Diagnostic Commands — Lambda Invocation Troubleshooter

Probe and pre-flight command listings moved verbatim from SKILL.md,
organized by diagnostic step. Load on demand.

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

### Function-state short-circuit and alias/version pre-flight

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

### Step 2 — TaskTimeoutException: probes 2a-2d (config, slow op, downstream, VPC)


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

### Step 3 — Out-of-memory: probes, memory-size guidance, leak note


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

### Step 4 — Cold start: probes and mitigation decision table


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

### Step 5 — AccessDenied: probes 5a-5d (CloudTrail, role policy, resource policy, patterns)


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

### Step 6 — VPC connectivity: probes 6a-6d (route table, SG egress, endpoint policy, endpoint guidance)


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

### Step 7 — Environment variables: probes 7a-7c (KMS decrypt, missing vars, alias differences)


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

### Step 8a — Async retry storm: config probes, retry sequence, failure patterns


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

### Step 8b — Sync caller timeout: Lambda vs API Gateway timeout probes


```bash
# Lambda timeout
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Timeout'

# API Gateway timeout is fixed at 30 seconds (REST API) or 29 seconds
# (HTTP API). Verify the integration:
aws apigateway get-method --rest-api-id <id> --resource-id <id> \
  --http-method ANY --output json 2>/dev/null
```

### Step 8b — Container image / ECR pull: probes 8b.1-8b.4 (image exists, size, repo policy, entry point)


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
