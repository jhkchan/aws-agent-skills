# Advanced patterns — lambda-function-deployer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Reasoning framework — why the deployment order matters

Lambda deployment has **dependency and ordering constraints** that make
the deployment sequence non-trivial. Applying configurations in the wrong
order causes deployment failures or silent runtime issues:

1. **Execution IAM role FIRST** — the function cannot be created without
   a valid `role` ARN. The execution role is the foundation: it grants
   the Lambda service permission to assume the role (`sts:AssumeRole`
   with the `lambda.amazonaws.com` principal), and grants the function
   permission to write logs, access resources, and decrypt secrets.
   Creating the function before the role exists returns
   `InvalidParameterValueException`.

2. **Runtime selection** — determines the execution environment, the
   handler signature, and the available SDK version. Selecting a
   deprecated runtime (e.g., `nodejs14.x`, `python3.7`) means the
   function will be force-upgraded or deactivated by AWS on the
   deprecation date, causing an outage.

3. **Memory + timeout** — memory allocation determines CPU power (Lambda
   allocates CPU proportionally to memory: 1769 MB = 1 vCPU). Timeout
   must be set to the maximum expected execution time; too short causes
   `TaskTimeoutError`, too long means you pay for hung invocations.

4. **Environment variables + KMS** — Lambda encrypts environment
   variables at rest with AES-256 by default. For sensitive variables,
   specify a customer-managed KMS key via the
   `aws:lambda:EncryptionKmsKeyArn` field. The function's execution role
   must have `kms:Decrypt` on the key, or the function fails at cold
   start with `KMSAccessDeniedException`.

5. **VPC configuration** — when the function needs to access private
   resources (RDS, ElastiCache, internal APIs), attach it to a VPC with
   private subnets and a security group. **VPC-attached functions CANNOT
   access the internet directly** — they need a NAT Gateway in a public
   subnet with proper route table configuration. This is the #1 cause of
   Lambda VPC deployment issues.

6. **Dead-letter queue + destinations** — async invocations that fail
   are retried (default: 2 retries with exponential backoff). Without a
   DLQ or on-failure destination, failed events are silently discarded
   after the retry limit. This causes data loss for event-driven
   pipelines.

7. **Concurrency** — provisioned concurrency eliminates cold starts for
   latency-sensitive workloads but incurs a per-hour charge. Reserved
   concurrency guarantees a minimum number of concurrent executions but
   caps the function's total concurrency. Set these based on the
   workload's latency and throughput requirements.

8. **Layers** — shared dependencies (SDKs, custom libraries, config
   files) packaged separately from the function code. A function can
   reference up to 5 layers, and the total unzipped deployment package
   (function code + all layers) cannot exceed 250 MB.

9. **Code signing** — for regulated environments, code signing with AWS
   Signer ensures only signed deployment packages are accepted. The
   function's `CodeSigningConfigArn` references a signing configuration
   that specifies trusted publisher profiles.

10. **Packaging (zip vs ECR)** — zip packages are limited to 50 MB
    (compressed) / 250 MB (uncompressed). For larger packages, use ECR
    container images (up to 10 GB). ECR packaging requires building a
    Docker image, pushing to ECR, and referencing the image URI.

11. **Logging** — Lambda automatically creates a CloudWatch log group
    named `/aws/lambda/<function-name>` on first invocation. There is NO
    default retention — logs accumulate indefinitely. Always set a log
    retention policy (e.g., 30/60/90 days) to control cost.

12. **Tracing** — X-Ray tracing provides end-to-end request visibility.
    Set `TracingConfig: { Mode: Active }` and add
    `AWSXRayDaemonWriteAccess` to the execution role.

13. **Verification** — after deployment, verify each setting via
    `get-function-configuration` and test with a synchronous invocation.

## Step 1 deep dive: execution IAM role policies and permissions

**Trust policy (allows Lambda to assume the role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

**Minimum required permissions (CloudWatch Logs):**

Attach the AWS-managed policy `AWSLambdaBasicExecutionRole` OR create a
custom inline policy scoped to the specific log group:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/lambda/<function-name>:*"
    },
    {
      "Effect": "Allow",
      "Action": "logs:CreateLogGroup",
      "Resource": "arn:aws:logs:<region>:<account-id>:*"
    }
  ]
}
```

**IMPORTANT — pre-create the log group and scope the role:** the managed
`AWSLambdaBasicExecutionRole` policy grants `logs:CreateLogGroup` on
`arn:aws:logs:*:*:*` — any log group in any region. This is broader than
needed. For production, pre-create the log group with a retention policy
and scope the execution role to just that group (remove
`logs:CreateLogGroup` entirely).

**Service-specific permissions (add based on workload):**

| Workload | Additional permissions |
|---|---|
| S3 processing | `s3:GetObject`, `s3:PutObject` on the specific bucket |
| DynamoDB | `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query` on the table ARN |
| API proxy | `execute-api:Invoke` if calling other APIs |
| VPC resources | Network interfaces are managed automatically by Lambda's service role |
| Secrets Manager | `secretsmanager:GetSecretValue` on the secret ARN |
| SSM Parameter Store | `ssm:GetParameter` + `kms:Decrypt` (for SecureString) |
| KMS decryption | `kms:Decrypt` on the CMK used for env var encryption |
| X-Ray tracing | Attach `AWSXRayDaemonWriteAccess` managed policy |

**NEVER use `*` as the action or resource** unless the function genuinely
needs cross-service access (e.g., a generic utility function). Scope
permissions to the minimum required actions on the minimum required
resources.

## Step 3 deep dive: memory + timeout guidance

**Workload-based memory guidance:**

| Workload type | Recommended memory | Recommended timeout | Rationale |
|---|---|---|---|
| Lightweight API (Node/Python) | 256-512 MB | 3-5s | Fast startup, low CPU needs |
| Medium API / data processing | 512-1024 MB | 10-30s | More CPU for JSON parsing, DB queries |
| Heavy compute (ML inference, image processing) | 2048-10240 MB | 60-900s | Full CPU cores for parallel processing |
| Java (without SnapStart) | 1024-2048 MB | 10-30s | JVM cold start needs memory; SnapStart reduces this |
| Java (with SnapStart) | 512-1024 MB | 10-30s | SnapStart eliminates cold-start JVM init |
| Stream processing / ETL | 1024-4096 MB | 60-300s | Sustained processing needs CPU + memory |
| VPC function (DB access) | 512-1024 MB | 10-60s | ENI creation adds cold start latency |

**Timeout:** default is 3 seconds. Maximum is 900 seconds (15 minutes).
Set the timeout to the P99 execution time + 20% buffer. A timeout that
is too short causes `TaskTimeoutError`; too long means you pay for hung
invocations.

**CPU architecture:** Lambda supports `x86_64` (default) and `arm64`
(Graviton2). ARM64 provides up to 20% price-performance improvement for
compatible workloads. Verify the deployment package is compiled for the
target architecture.

## Step 4 deep dive: environment variables + KMS encryption

```bash
aws lambda create-function \
  --function-name <name> \
  ...
  --environment "Variables={DB_HOST=prod-db.cluster.example.rds.amazonaws.com,DB_PORT=5432}" \
  --kms-key-arn "arn:aws:kms:<region>:<account-id>:key/<key-id>"
```

**Key policy requirement:** the KMS key policy must grant the execution
role `kms:Decrypt` for the key. Without this, the function fails at cold
start with `KMSAccessDeniedException` when trying to decrypt the
environment variables.

**NEVER store secrets in plaintext environment variables.** Use Secrets
Manager or SSM Parameter Store (SecureString) and reference them via the
`aws:lambda:EncryptionKmsKeyArn`-encrypted environment variable holding
the secret ARN. The function code retrieves the secret at runtime using
the execution role's permissions.

## Step 6 deep dive: DLQ + destinations

**Dead-letter queue (older pattern, still supported):**

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --dead-letter-config TargetArn=arn:aws:sqs:<region>:<account-id>:<dlq-name>
```

The execution role needs `sqs:SendMessage` (for SQS DLQ) or
`sns:Publish` (for SNS DLQ) on the TargetArn.

**On-failure / on-success destinations (newer, recommended):**

```bash
aws lambda put-function-event-invoke-config \
  --function-name <name> \
  --maximum retry-attempts=2 \
  --maximum-event-age-in-seconds=21600 \
  --destination-config '{"OnFailure":{"Destination":"arn:aws:sqs:<region>:<account-id>:<failure-queue>"}}'
```

Destinations are preferred over DLQs because:
- They support BOTH SQS and EventBridge bus targets.
- They include the full invocation context (request payload, response,
  error) in a structured JSON envelope.
- They separate success and failure routing.

**IMPORTANT:** a function can have EITHER a DLQ OR a destination, not
both. If both are configured, the destination takes precedence. Use
destinations for new deployments.

**Synchronous invocations** (API Gateway, ALB, direct `Invoke` with
`InvocationType=RequestResponse`) do NOT support DLQs or destinations —
the caller receives the error response directly.

## Step 7 deep dive: concurrency configuration

**On-demand concurrency (default):** the function scales automatically
based on incoming requests, up to the account-level concurrency limit
(default: 1,000 concurrent executions). No configuration needed.

**Reserved concurrency:** guarantees a pool of concurrent executions for
the function AND caps the function's maximum concurrency:

```bash
aws lambda put-function-concurrency \
  --function-name <name> \
  --reserved-concurrent-executions 50
```

Setting reserved concurrency to 0 effectively disables the function
(throttles all invocations) — useful for emergency circuit-breaking.

**Provisioned concurrency:** pre-initializes execution environments to
eliminate cold starts. Incurrs a per-hour charge based on the provisioned
amount. Use for latency-sensitive workloads (API Gateway backends,
real-time processing):

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name <name> \
  --qualifier <alias-or-version> \
  --provisioned-concurrent-executions 10
```

Provisioned concurrency requires a published version or alias (it does
not work on `$LATEST`). The typical workflow is: deploy the function,
publish a version, create an alias pointing to the version, then set
provisioned concurrency on the alias.

## Step 8 deep dive: layers

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --layers \
    arn:aws:lambda:<region>:<account-id>:layer:<layer1>:1 \
    arn:aws:lambda:<region>:<account-id>:layer:<layer2>:1
```

**Layer ordering matters:** if multiple layers contain the same file,
the LATER layer in the list takes precedence. Lambda merges layers in
order.

**AWS-managed layers:** AWS publishes layers for common utilities
(e.g., AWS Parameters and Secrets Hub layer, Powertools for Python/Java/
TypeScript, AWS X-Ray SDK). Reference these by their AWS account ARN.

**Layer architecture:** layers must match the function's architecture
(`x86_64` or `arm64`). A mismatch causes deployment failure.

## Step 9 deep dive: code signing

```bash
# Create a signing profile
aws signer put-signing-profile \
  --profile-name <profile> \
  --platform AWSLambda-SHA384-ECDSA

# Create a code signing config
aws lambda create-code-signing-config \
  --code-signing-config-name <config-name> \
  --allowed-publishers SigningProfileVersionArns=arn:aws:signer:<region>:<account-id>:/signing-profiles/<profile>/VERSION \
  --code-signing-policies UntrustedArtifactOnDeployment=Enforce

# Attach to the function
aws lambda update-function-code-signing-config \
  --function-name <name> \
  --code-signing-config-arn arn:aws:lambda:<region>:<account-id>:code-signing-config:<config-name>
```

**Policy modes:**
- `Enforce` — blocks deployment of unsigned or untrusted packages.
- `Warn` — allows deployment but logs a warning (for migration periods).

## Step 12 deep dive: tracing (X-Ray)

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --tracing-config Mode=Active
```

Attach the `AWSXRayDaemonWriteAccess` managed policy to the execution
role. X-Ray adds a daemon sidecar (~32 MB) to the execution environment;
for memory-constrained functions (< 256 MB), X-Ray overhead can cause
OOM errors.

## Latest Lambda features (2024-2026)

- **SnapStart (Java + Python, expanded):** SnapStart captures the
  initialized JVM (or Python interpreter) state as a snapshot and reuses
  it for new execution environments, reducing cold start from seconds to
  sub-100ms. Originally Java-only, expanded to Python. Enable via
  `--snap-start ApplyOn=PublishedVersions`. Requires publishing a version
  (does not work on `$LATEST`).

- **Lambda Web Adapter:** a Lambda extension (Rust-based proxy) that lets
  you run web applications (Express, Flask, FastAPI, Spring Boot) on
  Lambda without changing the handler signature. The adapter translates
  Lambda invoke events into HTTP requests for the web framework and
  translates HTTP responses back to Lambda invoke responses. Package as
  a layer: `awslabs/aws-lambda-web-adapter`.

- **Response streaming:** for LLM/chatbot workloads, Lambda supports
  streaming responses via `ResponseStream` in the invoke API. The
  function uses `awslambdaric` (Lambda Runtime Interface Client) to
  stream partial responses to the caller. This reduces time-to-first-byte
  for streaming workloads from the full execution time to sub-second.

- **Lambda MicroVM / Firecracker improvements:** Lambda's underlying
  Firecracker microVM has been optimized for faster initialization. Cold
  starts are ~30% faster on the latest platform versions. The function
  automatically benefits — no configuration needed.

- **EFS for Lambda:** VPC-attached functions can mount EFS for shared
  storage (up to the EFS capacity). Useful for large ML models,
  shared state across invocations, or heavy dependencies loaded from EFS.

- **Lambda Amazon Linux 2023 runtime:** `provided.al2023` is the
  recommended custom runtime base (replacing `provided.al2`). It includes
  newer glibc, better performance, and longer support window.

- **Improved environment variable limits:** the total environment
  variable payload (keys + values) is now 32 KB (up from 4 KB).

- **Lambda Powertools (GA for all runtimes):** Powertools for Python,
  Java, TypeScript, and .NET provide structured logging, tracing,
  metrics, and idempotency utilities. Install as a layer or dependency.

## Edge-case handling

- **Cross-account Lambda invocation.** The target function's
  resource-based policy must grant the calling account
  `lambda:InvokeFunction`. For cross-account EventBridge triggers, the
  event bus rule in the source account targets the function ARN, and the
  function's resource policy must allow `events.amazonaws.com` from the
  source account.

- **Lambda + API Gateway proxy integration.** The API Gateway execution
  role needs `lambda:InvokeFunction` on the function. The function does
  not need any additional configuration, but the handler must return a
  properly formatted proxy response (`statusCode`, `body`, `headers`).

- **Lambda + custom domain (API Gateway).** The custom domain uses an
  API mapping to route to a stage + API. The Lambda function itself does
  not know about the custom domain — API Gateway strips the domain prefix
  before invoking the function.

- **SnapStart + database connection pools.** SnapStart restores the
  initialized JVM state, including open database connections. This can
  cause stale connection errors if the snapshot is restored after the
  database TCP keepalive has expired. Initialize database connections in
  a `beforeHook` that runs after snapshot restore, not in the static
  initializer.

- **VPC function + STS/AWS SDK calls.** VPC-attached functions that call
  AWS services (STS, S3, DynamoDB) need either a NAT Gateway or VPC
  endpoints. Without these, AWS SDK calls fail with connection timeout
  because the function cannot reach the AWS public endpoint.

- **Layer version pinning.** When referencing a layer, always specify the
  version number (`:1`, `:2`, etc.), not just the layer ARN. The
  unversioned ARN resolves to `$LATEST`, which can change when a new
  version is published — potentially breaking the function.

- **Ephemeral storage.** Lambda provides 512 MB of ephemeral storage
  (`/tmp`) by default, up to 10 GB. For functions that write temporary
  files (ML model loading, file processing), increase
  `--ephemeral-storage Size=1024`.

## Recent AWS features (2024-2026)

- **SnapStart for Python (2024-2025):** SnapStart expanded beyond Java
  to Python, capturing the initialized Python interpreter state. Reduces
  cold start for Python functions from 1-3 seconds to sub-100ms.

- **Lambda Web Adapter (2024):** GA release of the Lambda Web Adapter
  extension, enabling web frameworks (Express, Flask, FastAPI, Spring
  Boot) to run on Lambda without code changes.

- **Response streaming (2024-2025):** `ResponseStream` in the invoke
  API enables streaming partial responses. Used for LLM/chatbot
  workloads where time-to-first-byte matters.

- **Lambda Amazon Linux 2023 (2024):** `provided.al2023` replaces
  `provided.al2` with newer glibc and better performance. All managed
  runtimes are being migrated to AL2023 underneath.

- **Improved cold start performance (2024-2025):** Firecracker microVM
  optimizations reduce cold starts by ~30% on the latest platform
  versions. No configuration needed — functions benefit automatically.

- **EFS mount improvements (2024):** Faster EFS mount times for
  VPC-attached functions, reducing cold start latency for EFS-dependent
  workloads.

- **Lambda Powertools GA (2024-2025):** Powertools for Python, Java,
  TypeScript, and .NET are GA. Provides structured logging, tracing,
  metrics, idempotency, and batch processing utilities.

