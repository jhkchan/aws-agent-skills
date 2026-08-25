---
name: lambda-function-deployer
description: 'Deploys AWS Lambda functions with production-grade configuration: least-privilege execution IAM role, supported runtime selection, right-sized memory and timeout, KMS-encrypted environment variables, VPC configuration with NAT Gateway for internet access, dead-letter queues and on-failure destinations, provisioned vs on-demand concurrency, Lambda Layers, code signing with Signer, ECR image vs zip packaging, CloudWatch logging with retention, X-Ray tracing, and latest features (SnapStart, Web Adapter, response streaming). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new Lambda function, deploying a function to production, validating a function configuration, or generating deployment commands and IaC templates. Triggers: create Lambda, deploy function, serverless, IAM role, VPC config, provisioned concurrency, layers, SnapStart, container image.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with lambda, iam, kms, ec2, sqs, sns, ecr, logs, and signer access. Works with Terraform aws_lambda_function resources, CloudFormation AWS::Lambda::Function, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, lambda, cloudops, deploy, serverless, compute, iam-role, vpc, concurrency, layers, code-signing, x-ray
  dependencies: aws-orchestrator
  keywords: aws, lambda, cloudops, deploy, provisioning, serverless, compute, iam-role, runtime, vpc, concurrency, layers, code-signing, x-ray, snapstart
  when_to_use: Invoke when the user wants to create a new Lambda function, deploy a function to production, validate a function configuration against best practices, generate deployment CLI commands or IaC templates, or troubleshoot a deployment failure caused by missing prerequisites (IAM role, VPC, ECR image, KMS key). Do NOT invoke for ECS/Fargate deployments (use ecs-task-definition-auditor) or for Lambda runtime deprecation audits (use lambda-runtime-deprecation-auditor).
---

# Lambda Function Deployer

An AWS CloudOps agent skill that deploys AWS Lambda functions with
correct production defaults. The skill walks the operator through a
13-step deployment procedure, explains why each default matters, and
emits a READY_TO_DEPLOY checklist verifying every configuration item.

## Activation keywords

create Lambda function, deploy Lambda, Lambda configuration, Lambda IAM
role, execution role, AWSLambdaBasicExecutionRole, Lambda runtime,
nodejs20.x, python3.12, java21, Lambda memory, Lambda timeout, Lambda
VPC, NAT Gateway, Lambda DLQ, dead-letter queue, on-failure destination,
provisioned concurrency, on-demand concurrency, Lambda layers, code
signing, Lambda ECR, container image Lambda, CloudWatch Logs retention,
X-Ray tracing, Lambda SnapStart, Lambda Web Adapter, response streaming.

## Invocation contract (hard requirement)

When this skill is invoked with a Lambda deployment request (function
name, runtime, handler, workload type, or a partial existing
configuration), the agent MUST respond with the READY_TO_DEPLOY checklist
defined in §"Output format" using the literal all-caps labels `FUNCTION:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream deployment pipelines rely on; deviating from the
literal labels breaks automation silently.

## Reasoning framework (why the deployment order matters)

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

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Function name** | Must be unique within the account/region. 64-char max, alphanumeric + hyphens/underscores. | `aws lambda list-functions --query 'Functions[].FunctionName'` |
| **Runtime** | Must be a currently-supported runtime. Deprecated runtimes are force-upgraded or deactivated. | Check AWS Lambda runtimes documentation |
| **Handler** | Entry point format depends on runtime: `file.function` (Node/Python), `class::method` (Java/C#). | Verify against the deployment package |
| **Deployment package** | Either a zip file (<= 50 MB) or an ECR image URI. | `ls -la <zip>` or `aws ecr describe-images` |
| **Execution IAM role** | Must exist with a trust policy allowing `lambda.amazonaws.com` to assume it. | `aws iam get-role --role-name <role>` |
| **KMS key (if env var encryption)** | Customer-managed CMK with key policy granting the execution role `kms:Decrypt`. | `aws kms describe-key --key-id <alias>` |
| **VPC subnets + security group (if VPC)** | Private subnets in at least 2 AZs + a security group allowing outbound to resources. NAT Gateway in a public subnet for internet access. | `aws ec2 describe-subnets` |
| **SQS/SNS ARN (if DLQ/destination)** | DLQ must exist before referencing it. The execution role needs `sqs:SendMessage` or `sns:Publish` on the ARN. | `aws sqs get-queue-url` / `aws sns get-topic-attributes` |
| **Layer ARNs (if layers)** | Layers must exist in the same region (or be referenced by their full ARN with compatible architecture). | `aws lambda list-layers` |
| **ECR image (if container deployment)** | Image must be pushed to ECR, and the execution role needs `ecr:BatchGetImage` + `ecr:GetDownloadUrlForLayer`. | `aws ecr describe-images --repository-name <repo>` |
| **Signing profile (if code signing)** | A signing profile in Signer + a code signing config in Lambda. | `aws signer list-signing-profiles` |
| **IAM permissions** | The caller needs `lambda:CreateFunction`, `iam:PassRole` on the execution role, and VPC/KMS/ECR permissions as applicable. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Execution IAM role (least-privilege)

The execution role is the most critical configuration — it determines
what the function can do. Create it BEFORE the function.

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

### Step 2: Runtime selection

Choose a currently-supported runtime. AWS deprecates runtimes on a
schedule — deprecated runtimes receive no security patches and are
eventually force-upgraded or deactivated.

**Currently supported runtimes (as of 2026):**

| Runtime | Identifier | Notes |
|---|---|---|
| Node.js 20.x | `nodejs20.x` | LTS, recommended for new JS/TS functions |
| Node.js 22.x | `nodejs22.x` | Newer LTS |
| Python 3.12 | `python3.12` | Recommended for new Python functions |
| Python 3.13 | `python3.13` | Latest Python |
| Java 21 | `java21` | LTS, supports SnapStart |
| Java 17 | `java17` | LTS, supports SnapStart |
| .NET 8 | `dotnet8` | Current .NET LTS |
| Go 1.x | `provided.al2023` | Custom runtime with Go wrapper |
| Ruby 3.3 | `ruby3.3` | |
| provided.al2023 | `provided.al2023` | Custom runtime (Amazon Linux 2023) |

**DEPRECATED runtimes to avoid:** `nodejs14.x`, `nodejs16.x`,
`nodejs18.x`, `python3.7`, `python3.8`, `python3.9`, `python3.10`,
`java8`, `java11`, `dotnet6`, `ruby2.7`, `go1.x` (legacy). Deploying a
deprecated runtime is a deployment BLOCKER — flag as
PREREQUISITES_MISSING.

### Step 3: Memory + timeout

Memory allocation ranges from 128 MB to 10,240 MB (10 GB). Lambda
allocates CPU power proportionally: at 1,769 MB, the function gets
1 vCPU; at 3,538 MB, 2 vCPU. Memory is the primary performance lever.

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

### Step 4: Environment variables + KMS encryption

Lambda encrypts environment variables at rest using AES-256 (AWS-managed
key) by default. For sensitive variables (API keys, database credentials,
tokens), use a customer-managed KMS key:

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

### Step 5: VPC configuration

Attach the function to a VPC when it needs to access private resources
(RDS, ElastiCache, internal APIs, VPC-only services). **VPC-attached
functions CANNOT access the internet directly** — they route through the
VPC, which requires a NAT Gateway for internet access.

```bash
aws lambda create-function \
  --function-name <name> \
  ...
  --vpc-config SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-xxx
```

**VPC configuration rules:**

1. **Use PRIVATE subnets** (not public). Lambda creates Hyperplane ENIs
   in the specified subnets to route traffic to VPC resources. Public
   subnets cause deployment failures or routing issues.
2. **Use at least 2 subnets in different AZs** for high availability.
   Lambda distributes ENIs across subnets.
3. **Security group:** define inbound rules for resources the function
   accesses (e.g., the RDS security group allows inbound from the
   function's security group). Define outbound rules for the function's
   egress needs.
4. **NAT Gateway for internet access:** if the VPC-attached function
   needs internet access (API calls, package downloads, external
   services), configure:
   - A NAT Gateway in a PUBLIC subnet with an Elastic IP.
   - A route table entry in the PRIVATE subnet routing `0.0.0.0/0` to
     the NAT Gateway.
   - Without this, the function can reach VPC resources but NOT the
     internet — this is the #1 Lambda VPC deployment issue.

5. **VPC endpoints for AWS services:** for VPC-attached functions that
   access AWS services (S3, DynamoDB, Secrets Manager, Systems Manager),
   use VPC endpoints (Gateway or Interface) to avoid routing through the
   NAT Gateway (saving NAT data processing costs).

**Lambda execution role VPC permissions:** since 2023, Lambda manages
Hyperplane ENIs automatically — the execution role no longer needs
explicit EC2 network interface permissions (`ec2:CreateNetworkInterface`
etc.). These are handled by the Lambda service-linked role.

### Step 6: Dead-letter queue + destinations

**Asynchronous invocations** (EventBridge, S3 events, SNS, direct
`Invoke` with `InvocationType=Event`) are retried on failure. Without a
DLQ or destination, failed events are silently discarded after the retry
limit.

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

### Step 7: Concurrency

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

**Concurrency scaling guidance:**

| Workload | Concurrency model | Rationale |
|---|---|---|
| Event-driven (S3, EventBridge) | On-demand | Burst-tolerant, latency-insensitive |
| API backend (API Gateway) | Provisioned | Cold-start-sensitive, user-facing |
| Stream consumer (Kinesis, SQS) | Reserved (cap) | Prevent the function from consuming the entire account limit |
| Scheduled (EventBridge cron) | On-demand | Predictable, low-volume |
| High-throughput async pipeline | Reserved (minimum) + On-demand | Guarantee baseline, allow burst |

### Step 8: Layers

Layers are shared archives containing dependencies, custom runtimes, or
configuration. A function can reference up to 5 layers; the total
unzipped deployment (function code + all layers) cannot exceed 250 MB.

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

### Step 9: Code signing

For regulated environments (financial services, healthcare, government),
code signing with AWS Signer ensures only trusted deployment packages
are accepted.

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

### Step 10: Packaging — zip vs ECR

**Zip package (for functions <= 50 MB compressed / 250 MB uncompressed):**

```bash
# Package the function
zip -r function.zip index.js node_modules/

# Deploy
aws lambda create-function \
  --function-name <name> \
  --runtime nodejs20.x \
  --handler index.handler \
  --role arn:aws:iam::<account-id>:role/<execution-role> \
  --zip-file fileb://function.zip
```

**ECR container image (for functions > 50 MB or custom runtime):**

```dockerfile
FROM public.ecr.aws/lambda/nodejs:20
COPY app.js package*.json ./
RUN npm ci --production
CMD [ "app.handler" ]
```

```bash
# Build and push
docker build -t <name> .
docker tag <name>:latest <account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest

# Deploy
aws lambda create-function \
  --function-name <name> \
  --package-type Image \
  --code ImageUri=<account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest \
  --role arn:aws:iam::<account-id>:role/<execution-role>
```

The execution role needs `ecr:BatchGetImage` and
`ecr:GetDownloadUrlForLayer` on the ECR repository, OR you can use a
resource-based ECR policy.

### Step 11: Logging (CloudWatch Logs retention)

Lambda automatically creates a log group `/aws/lambda/<function-name>`
on first invocation. **There is NO default retention — logs accumulate
indefinitely.** Always pre-create the log group with a retention policy:

```bash
aws logs create-log-group \
  --log-group-name /aws/lambda/<name> \
  --retention-in-days 30
```

If the log group already exists, update retention:

```bash
aws logs put-retention-policy \
  --log-group-name /aws/lambda/<name> \
  --retention-in-days 30
```

**Retention guidance:**

| Workload | Retention | Rationale |
|---|---|---|
| Production API | 30-90 days | Debugging + compliance window |
| Compliance (HIPAA, PCI) | 365+ days | Regulatory retention |
| Event-driven pipeline | 14-30 days | Operational debugging |
| Development / staging | 7-14 days | Cost control |

### Step 12: Tracing (X-Ray)

Enable X-Ray tracing for end-to-end request visibility:

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --tracing-config Mode=Active
```

Attach the `AWSXRayDaemonWriteAccess` managed policy to the execution
role. X-Ray adds a daemon sidecar (~32 MB) to the execution environment;
for memory-constrained functions (< 256 MB), X-Ray overhead can cause
OOM errors.

### Step 13: Verification

```bash
# Function configuration
aws lambda get-function-configuration --function-name <name>

# Execution role policy
aws iam list-attached-role-policies --role-name <role>
aws iam list-inline-role-policies --role-name <role>

# VPC config (if applicable)
aws lambda get-function-configuration --function-name <name> --query 'VpcConfig'

# Event invoke config (destinations)
aws lambda get-function-event-invoke-config --function-name <name>

# Concurrency
aws lambda get-function-concurrency --function-name <name>
aws lambda get-provisioned-concurrency-config --function-name <name> --qualifier <alias>

# Layers
aws lambda get-function-configuration --function-name <name> --query 'Layers'

# Code signing config
aws lambda get-function-code-signing-config --function-name <name>

# Log group retention
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<name>

# Test invocation
aws lambda invoke --function-name <name> --payload '{}' /tmp/response.json
cat /tmp/response.json
```

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

## Workload-specific deployment matrix

| Workload | Runtime | Memory | Timeout | VPC | Concurrency | DLQ/Dest | Tracing |
|---|---|---|---|---|---|---|---|
| **API backend** (API Gateway) | nodejs20.x / python3.12 | 512-1024 MB | 10-30s | If accessing private resources | Provisioned | On-failure destination | Active |
| **Async event processor** (S3/SQS/EventBridge) | python3.12 / java21 | 512-2048 MB | 60-300s | If accessing private resources | On-demand | On-failure destination | Active |
| **Stream consumer** (Kinesis/DynamoDB Streams) | nodejs20.x / python3.12 | 512-2048 MB | 60-300s | If accessing private resources | Reserved (cap) | N/A (stream handles retries) | Active |
| **ML inference** | python3.12 / provided.al2023 | 4096-10240 MB | 60-900s | No (GPU not supported) | Provisioned | On-failure destination | Active |
| **Scheduled job** (EventBridge cron) | nodejs20.x / python3.12 | 256-1024 MB | 60-900s | If accessing private resources | On-demand | On-failure destination | Optional |
| **Java enterprise** (Spring Boot) | java21 | 1024-2048 MB | 30-60s | If accessing private resources | Provisioned + SnapStart | On-failure destination | Active |
| **Container function** (> 50 MB) | provided.al2023 (ECR image) | 1024-4096 MB | 60-300s | If accessing private resources | Provisioned | On-failure destination | Active |

## NEVER (anti-patterns)

- NEVER deploy a function with `AdministratorAccess` or `*` permissions
  on the execution role. The execution role is the function's identity —
  a compromised function with broad permissions can access every resource
  in the account. Scope permissions to the minimum required actions on
  the minimum required resources.

- NEVER deploy a deprecated runtime (`nodejs14.x`, `python3.7`, `java8`,
  `dotnet6`, etc.). Deprecated runtimes receive no security patches and
  are force-upgraded or deactivated by AWS on the deprecation date,
  causing an outage. This is a deployment BLOCKER.

- NEVER attach a VPC-attached function to a PUBLIC subnet. Lambda creates
  Hyperplane ENIs in the specified subnets; public subnets cause routing
  issues. Always use PRIVATE subnets.

- NEVER assume a VPC-attached function can access the internet. VPC
  routing applies — without a NAT Gateway (or VPC endpoint for AWS
  services), the function can reach VPC resources but NOT the internet.
  This is the #1 Lambda VPC deployment issue.

- NEVER store secrets in plaintext environment variables. Environment
  variables are visible in the Lambda console, CloudTrail
  (`CreateFunction` / `UpdateFunctionConfiguration` events), and the
  function configuration API. Use Secrets Manager or SSM Parameter Store
  (SecureString) and retrieve at runtime via the execution role.

- NEVER omit CloudWatch Logs retention. Lambda creates the log group
  automatically but does NOT set a retention policy. Without retention,
  logs accumulate indefinitely, incurring unbounded cost. Always
  pre-create the log group with retention or set it post-deployment.

- NEVER set provisioned concurrency on `$LATEST`. Provisioned concurrency
  requires a published version or alias. Deploying provisioned
  concurrency on `$LATEST` is a silent no-op — the API accepts it but
  no environments are provisioned.

- NEVER set reserved concurrency to 0 unless you intentionally want to
  disable the function (emergency circuit-breaking). A reserved
  concurrency of 0 throttles ALL invocations.

- NEVER mix layer architectures. Layers must match the function's
  architecture (`x86_64` or `arm64`). An architecture mismatch causes
  deployment failure or runtime `exec format error`.

- NEVER use `AWSLambdaBasicExecutionRole`'s `logs:CreateLogGroup` on
  `arn:aws:logs:*:*:*` in production. This allows the function to create
  ANY log group in ANY region. Pre-create the log group and scope the
  role to just that group.

- NEVER skip X-Ray tracing for production microservice architectures.
  Without tracing, you cannot diagnose latency across service call chains.
  X-Ray is cheap (free tier + $5 per million traces) and the overhead is
  negligible for functions with >= 256 MB memory.

- NEVER deploy an ECR-based function without verifying the execution role
  has ECR pull permissions. The function will fail at cold start with
  `ECRAccessDeniedException`. Add `ecr:BatchGetImage` and
  `ecr:GetDownloadUrlForLayer` to the execution role or use a
  resource-based ECR policy.

- NEVER set a timeout longer than the workload needs. Lambda bills by
  execution duration (rounded up to the nearest 1ms). A function with a
  900-second timeout that hangs will run (and bill) for 15 minutes per
  invocation. Set the timeout to P99 + 20% buffer.

- NEVER use both a DLQ and an on-failure destination on the same
  function. Destinations supersede DLQs — having both is confusing and
  the DLQ will never receive messages. Use destinations for new
  deployments.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal `VERDICT:`
  label silently breaks downstream deployment pipelines and
  assertion-based evals.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm the function name is available:**
  `aws lambda get-function-configuration --function-name <name>` — if it
  returns 200, confirm whether you intend to update an existing function
  vs create new.

- **Confirm the execution role exists and has the correct trust policy:**
  ```bash
  aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'
  ```
  The trust policy MUST include `"Service": "lambda.amazonaws.com"` with
  `"Action": "sts:AssumeRole"`. Without this, the function creation
  fails with `InvalidParameterValueException`.

- **Confirm the caller has `iam:PassRole` on the execution role.**
  `CreateFunction` requires `iam:PassRole` to attach the role. A missing
  `iam:PassRole` permission causes `AccessDeniedException`.

- **For VPC functions, confirm subnets are private and span multiple AZs:**
  ```bash
  aws ec2 describe-subnets --subnet-ids subnet-aaa subnet-bbb \
    --query 'Subnets[].{AZ:AvailabilityZone,Public:MapPublicIpOnLaunch}'
  ```
  All subnets should be private (`MapPublicIpOnLaunch: false`) and span
  at least 2 AZs.

- **For ECR functions, confirm the image exists:**
  ```bash
  aws ecr describe-images --repository-name <repo> --image-ids imageTag=latest
  ```

- **For code-signed functions, confirm the signing profile is active:**
  ```bash
  aws signer get-signing-profile --profile-name <profile>
  ```

- **Pre-create the CloudWatch log group with retention BEFORE the first
  invocation** to avoid unbounded log accumulation:
  ```bash
  aws logs create-log-group --log-group-name /aws/lambda/<name>
  aws logs put-retention-policy --log-group-name /aws/lambda/<name> --retention-in-days 30
  ```

- **For existing functions, capture current configuration for rollback:**
  ```bash
  aws lambda get-function-configuration --function-name <name> --output json > /tmp/<name>-config-backup.json
  aws lambda get-function-code-signing-config --function-name <name> --output json > /tmp/<name>-signing-backup.json
  ```

## Output format — MANDATORY literal labels

When invoked with a function deployment request, your ENTIRE response
MUST be the checklist block below. The labels are **case-sensitive
all-caps keywords** — write them EXACTLY as shown. Do NOT substitute
`Verdict`, `**VERDICT**`, `### Verdict`, or any markdown variant. Do
NOT write a preamble ("Here is your deployment checklist…"). Start with
`FUNCTION:` and stop after the `VERIFICATION_COMMANDS:` block.

```text
FUNCTION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Execution IAM role — least-privilege (scoped to function resources)
  [✓]      Runtime — nodejs20.x (supported, not deprecated)
  [✓]      Memory — 512 MB (right-sized for workload)
  [✓]      Timeout — 15s (P99 + 20% buffer)
  [✓]      Environment variables — KMS-encrypted (customer-managed CMK)
  [OPTIONAL] VPC — Private subnets (2 AZs) + security group + NAT Gateway
  [✓]      Dead-letter / destination — On-failure SQS destination
  [OPTIONAL] Concurrency — On-demand (no provisioned needed)
  [OPTIONAL] Layers — Powertools for Python (v3)
  [OPTIONAL] Code signing — Not configured
  [✓]      Packaging — Zip (12 MB compressed)
  [✓]      Logging — CloudWatch log group /aws/lambda/<name>, retention 30 days
  [✓]      Tracing — X-Ray Active mode
VERIFICATION_COMMANDS:
  aws lambda get-function-configuration --function-name <name>
  aws iam list-attached-role-policies --role-name <execution-role>
  aws lambda get-function-event-invoke-config --function-name <name>
  aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<name>
  aws lambda invoke --function-name <name> --payload '{}' /tmp/response.json
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing (execution role ARN,
  KMS key ARN, VPC subnet IDs) and the operator must provide it before
  deployment can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (execution role, non-deprecated runtime, deployment package),
the verdict is `PREREQUISITES_MISSING` with each gap listed. The
checklist shows the target configuration with `[INPUT NEEDED]` or `[✗]`
for unmet prerequisites.

**Worked example (copy the shape exactly):**

```text
FUNCTION: order-processor-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Execution IAM role — order-processor-exec (scoped to DynamoDB + SQS)
  [✓]      Runtime — python3.12
  [✓]      Memory — 1024 MB
  [✓]      Timeout — 30s
  [✓]      Environment variables — KMS-encrypted (alias/lambda-env-key)
  [✓]      VPC — Private subnets (subnet-aaa, subnet-bbb) + sg-order-processor + NAT Gateway
  [✓]      Destination — On-failure SQS (order-processing-dlq)
  [✓]      Concurrency — Reserved (50 concurrent executions)
  [✓]      Layers — Powertools for Python v3, AWS Parameters and Secrets
  [OPTIONAL] Code signing — Not configured
  [✓]      Packaging — Zip (8 MB compressed)
  [✓]      Logging — /aws/lambda/order-processor-prod, retention 30 days
  [✓]      Tracing — X-Ray Active mode
VERIFICATION_COMMANDS:
  aws lambda get-function-configuration --function-name order-processor-prod
  aws iam list-attached-role-policies --role-name order-processor-exec
  aws lambda get-function-event-invoke-config --function-name order-processor-prod
  aws lambda get-function-concurrency --function-name order-processor-prod
  aws logs describe-log-groups --log-group-name-prefix /aws/lambda/order-processor-prod
  aws lambda invoke --function-name order-processor-prod --payload '{"test": true}' /tmp/response.json
```

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

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 13 deployment steps, including execution role
  creation, VPC setup, ECR build/push, code signing, and Terraform
  `aws_lambda_function` resource equivalents.

- `references/runtime-and-vpc-guide.md` — deep reference on runtime
  support timelines (deprecation dates), VPC networking for Lambda
  (NAT Gateway vs VPC endpoints, Hyperplane ENI internals), SnapStart
  internals, and concurrency scaling limits.

## Section taxonomy (CloudOps deployer pattern)

1. **Frontmatter** — name, description, version, when-to-use.
2. **Activation keywords** — discoverability terms.
3. **Invocation contract** — the mandatory output format.
4. **Reasoning framework** — the *why* behind the deployment order.
5. **Prerequisites** — what must be verified before deployment.
6. **Deployment procedure** — the ordered 13-step deployment sequence.
7. **Latest Lambda features** — 2024-2026 feature changes.
8. **Workload-specific deployment matrix** — per-workload configuration.
9. **NEVER** — anti-patterns with explicit *why* each is wrong.
10. **Pre-flight safety checks** — non-destructive deployment guards.
11. **Output format** — the fixed checklist report shape.
12. **Edge-case handling** — cross-account, SnapStart, VPC SDK calls.
13. **References** — pointer to deeper references.

## Domain

AWS CloudOps / Lambda Serverless Compute Provisioning.

## AWS documentation

- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **Lambda Configuration** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-console.html
- **Lambda Execution Role** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html
- **Lambda VPC** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html
- **Lambda Runtimes** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html
- **Lambda Destinations** — https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html
- **Lambda Layers** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html
- **Lambda Code Signing** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html
- **Lambda CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/lambda/
