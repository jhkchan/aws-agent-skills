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

Full 13-item rationale moved to `references/advanced-patterns.md` —
see "Reasoning framework".

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

Trust/inline policy JSON, scoping note, service-specific permission table,
and least-privilege rule moved to `references/advanced-patterns.md`.

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

Workload-based memory/timeout table, timeout rule, and CPU architecture
note moved to `references/advanced-patterns.md` (Step 3 deep dive).

### Step 4: Environment variables + KMS encryption

Lambda encrypts environment variables at rest using AES-256 (AWS-managed
key) by default. For sensitive variables (API keys, database credentials,
tokens), use a customer-managed KMS key:

create-function CLI, KMS key-policy requirement, and secrets rule moved
to `references/advanced-patterns.md` (Step 4 deep dive).


### Step 5: VPC configuration

Attach the function to a VPC when it needs to access private resources
(RDS, ElastiCache, internal APIs, VPC-only services). **VPC-attached
functions CANNOT access the internet directly** — they route through the
VPC, which requires a NAT Gateway for internet access.

vpc-config CLI, subnet/SG/NAT rules, VPC endpoints, and ENI permission
notes moved to `references/runtime-and-vpc-guide.md`.

### Step 6: Dead-letter queue + destinations

**Asynchronous invocations** (EventBridge, S3 events, SNS, direct
`Invoke` with `InvocationType=Event`) are retried on failure. Without a
DLQ or destination, failed events are silently discarded after the retry
limit.

DLQ/destination CLI, preference rationale, DLQ-vs-destination rule, and
sync-invocation note moved to `references/advanced-patterns.md`.

### Step 7: Concurrency

On-demand/reserved/provisioned CLI and workflow moved to
`references/advanced-patterns.md` (Step 7 deep dive).

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

Layers CLI, ordering rule, AWS-managed layers, and architecture match
moved to `references/advanced-patterns.md` (Step 8 deep dive).

### Step 9: Code signing

For regulated environments (financial services, healthcare, government),
code signing with AWS Signer ensures only trusted deployment packages
are accepted.

Signing profile/config CLI and policy modes moved to
`references/advanced-patterns.md` (Step 9 deep dive).

### Step 10: Packaging — zip vs ECR

Zip/Dockerfile/ECR CLI sequences and ECR pull permissions moved to
`references/deployment-cli-commands.md` (Step 10 deep dive).

### Step 11: Logging (CloudWatch Logs retention)

Lambda automatically creates a log group `/aws/lambda/<function-name>`
on first invocation. **There is NO default retention — logs accumulate
indefinitely.** Always pre-create the log group with a retention policy:

Log-group creation and retention CLI moved to
`references/deployment-cli-commands.md` (Step 11 deep dive).

**Retention guidance:**

| Workload | Retention | Rationale |
|---|---|---|
| Production API | 30-90 days | Debugging + compliance window |
| Compliance (HIPAA, PCI) | 365+ days | Regulatory retention |
| Event-driven pipeline | 14-30 days | Operational debugging |
| Development / staging | 7-14 days | Cost control |

### Step 12: Tracing (X-Ray)

Enable X-Ray tracing for end-to-end request visibility:

X-Ray CLI and daemon overhead note moved to
`references/advanced-patterns.md` (Step 12 deep dive).

### Step 13: Verification

Full verification command listing moved to
`references/diagnostic-commands.md` (Step 13).

## Latest Lambda features (2024-2026)

Feature list moved to `references/advanced-patterns.md` —
see "Latest Lambda features (2024-2026)".

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

Full pre-flight check listing (with CLI) moved to
`references/diagnostic-commands.md`.

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

Edge-case catalog moved to `references/advanced-patterns.md` —
see "Edge-case handling".

## Recent AWS features (2024-2026)

Feature list moved to `references/advanced-patterns.md` —
see "Recent AWS features (2024-2026)".

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

## References (load on demand)

- [advanced-patterns.md](references/advanced-patterns.md) — reasoning
  framework, per-step deep dives (IAM, memory, KMS, DLQ, concurrency,
  layers, code signing, tracing), edge cases, recent AWS features.
- [diagnostic-commands.md](references/diagnostic-commands.md) — Step 13
  verification commands, pre-flight safety checks.
- [deployment-cli-commands.md](references/deployment-cli-commands.md) —
  packaging (zip/ECR) and logging CLI sequences.
- [runtime-and-vpc-guide.md](references/runtime-and-vpc-guide.md) — VPC
  configuration rules and ENI permissions.

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
