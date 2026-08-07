# Runtime and VPC Guide — Lambda Function Deployer

Deep reference on runtime support timelines (deprecation dates), VPC
networking for Lambda (NAT Gateway vs VPC endpoints, Hyperplane ENI
internals), SnapStart internals, and concurrency scaling limits.

## Runtime support and deprecation timeline

AWS Lambda deprecates runtimes on a published schedule. The lifecycle
has phases:

1. **Supported** — fully maintained, receives security patches.
2. **Deprecation announced** — AWS announces the deprecation date
   (typically 60+ days notice). New functions can still be created with
   the runtime during this phase.
3. **Deprecated** — the runtime enters deprecation. Existing functions
   continue to run but cannot be created with this runtime. AWS may
   auto-upgrade the runtime.
4. **Blocked** — the runtime is blocked for create/update operations.
   Existing functions are force-upgraded to the next supported runtime
   on the next update, or deactivated entirely.

### Runtime deprecation reference (2024-2026)

| Runtime | Deprecated | Blocked | Recommended migration target |
|---|---|---|---|
| `nodejs14.x` | 2023-11 | 2024-12 | `nodejs20.x` or `nodejs22.x` |
| `nodejs16.x` | 2024-06 | 2025-06 | `nodejs20.x` or `nodejs22.x` |
| `nodejs18.x` | 2025-03 | 2026-04 | `nodejs20.x` or `nodejs22.x` |
| `python3.7` | 2023-12 | 2024-12 | `python3.12` or `python3.13` |
| `python3.8` | 2024-10 | 2025-10 | `python3.12` or `python3.13` |
| `python3.9` | 2025-07 | 2026-07 | `python3.12` or `python3.13` |
| `python3.10` | 2026-03 | 2027-03 | `python3.12` or `python3.13` |
| `java8` | 2024-01 | 2025-01 | `java21` |
| `java11` | 2025-09 | 2026-09 | `java21` |
| `dotnet6` | 2024-07 | 2025-07 | `dotnet8` |
| `ruby2.7` | 2024-04 | 2025-04 | `ruby3.3` |
| `go1.x` | 2023-12 | 2025-01 | `provided.al2023` (custom runtime) |

**Deployment rule:** if the requested runtime is in the "Deprecated" or
"Blocked" column, the deployment verdict is PREREQUISITES_MISSING with a
recommendation to use the migration target runtime.

## VPC networking for Lambda

### How VPC-attached Lambda works (Hyperplane ENI)

When a Lambda function is attached to a VPC, AWS creates Hyperplane ENIs
(elastic network interfaces) in the specified subnets. These ENIs are
managed by the Lambda service (not the user's account) and are shared
across execution environments for the same function + subnet
combination.

**Before Hyperplane (pre-2019):** each concurrent execution got its own
ENI. A function with 1,000 concurrent executions needed 1,000 ENIs,
exhausting subnet IP addresses. This caused `EC2ThrottledException` and
subnet IP exhaustion.

**With Hyperplane (2019+):** ENIs are shared across execution
environments via NAT. The number of ENIs is proportional to the
function's memory (CPU), not concurrency. A 1,769 MB (1 vCPU) function
with 1,000 concurrent executions uses ~1-2 ENIs per subnet.

**Implications:**
- You no longer need to provision large subnets for high-concurrency
  functions. A /28 (16 IPs) is sufficient for most functions.
- The execution role no longer needs `ec2:CreateNetworkInterface`,
  `ec2:DeleteNetworkInterface`, or `ec2:DescribeNetworkInterfaces`
  permissions — these are handled by the Lambda service-linked role.

### Internet access for VPC-attached functions

A VPC-attached function can reach:
- **VPC resources** (RDS, ElastiCache, internal ALBs, private EC2) via
  the Hyperplane ENI — always available.
- **AWS private endpoints** (VPC Gateway endpoints for S3/DynamoDB,
  Interface endpoints for other services) — no internet needed.
- **The internet** — ONLY via a NAT Gateway or NAT Instance. Without a
  NAT, VPC-attached functions CANNOT reach the internet, including AWS
  public API endpoints (S3, DynamoDB, STS, Secrets Manager public
  endpoints).

**NAT Gateway vs VPC endpoints — choose based on traffic:**

| Traffic type | Recommended path | Why |
|---|---|---|
| S3 / DynamoDB | VPC Gateway endpoint | Free, no NAT data processing cost |
| Other AWS services (SQS, SNS, Secrets Manager, STS) | VPC Interface endpoint | Avoids NAT data processing ($0.045/GB) |
| Third-party APIs (Stripe, Twilio, etc.) | NAT Gateway | Cannot use VPC endpoints for non-AWS services |
| High-volume AWS API calls | VPC endpoint (cost savings) | NAT charges $0.045/GB processed |

**NAT Gateway cost warning:** NAT Gateway charges $0.045/hour (~$32/month)
per NAT + $0.045/GB of data processed. For high-traffic VPC functions,
this can exceed the Lambda compute cost. Use VPC endpoints to minimize
NAT data processing.

### VPC security group rules

The function's security group defines:
- **Outbound:** allow traffic to the resource's port (e.g., port 5432
  for RDS PostgreSQL). Default: allow all outbound.
- **Inbound:** Lambda does not need inbound rules — it initiates
  connections outbound. Do NOT open inbound ports on the function's
  security group.

The RESOURCE's security group must allow inbound from the function's
security group. For example, the RDS security group inbound rule:
`Allow TCP 5432 from sg-lambda-function`.

## SnapStart internals

SnapStart captures the initialized runtime state as a Firecracker
snapshot and restores it for new execution environments. This skips the
runtime initialization phase (JVM startup, class loading, SDK client
initialization) on cold starts.

### How SnapStart works

1. **Init phase:** the function's first invocation initializes the JVM,
   loads classes, creates SDK clients, opens database connection pools.
   This takes 1-10 seconds for Java functions.
2. **Snapshot:** after init, Firecracker takes a memory snapshot of the
   execution environment. The snapshot is stored in S3 (managed by AWS).
3. **Restore:** for subsequent cold starts, Firecracker restores the
   snapshot instead of re-initializing. This reduces cold start from
   seconds to ~200ms (the snapshot restore time).
4. **BeforeHook:** after restore, a `beforeHook` function runs to
   re-establish connections that may have gone stale (database TCP
   connections, DNS cache, random state). This is the only code that
   runs post-snapshot.

### SnapStart limitations

- **Only for published versions:** SnapStart does not work on `$LATEST`.
  You must publish a version and invoke through the version ARN or an
  alias.
- **Network connections in snapshot:** open TCP connections in the
  snapshot may be stale after restore. Initialize network-dependent
  resources in a `beforeHook`, not in the static initializer.
- **Unique values per invocation:** if the static initializer generates
  a UUID or random value, all restored environments share the same
  value. Generate unique values in the handler, not in init.
- **Cryptography:** some cryptographic operations (e.g., `SecureRandom`)
   produce identical output across restored environments. Use
   `SecureRandom.getInstanceStrong()` or regenerate seeds in the
   `beforeHook`.

### SnapStart for Python

SnapStart expanded to Python (2024-2025). The same snapshot/restore
mechanism applies. For Python functions with heavy module imports
(numpy, pandas, boto3), SnapStart reduces cold start from 1-3 seconds
to sub-100ms.

## Concurrency scaling limits

### Account-level concurrency limits

| Limit | Default | Adjustable |
|---|---|---|
| Account concurrent executions | 1,000 | Yes (AWS support) |
| Burst concurrency (sudden traffic spike) | 1,000 (us-east-1, us-west-2, eu-west-1) / 500 (other regions) | Yes (AWS support) |
| Storage (deployment packages + layers per account) | 75 GB | Yes (AWS support) |

### Burst concurrency scaling

Lambda scales concurrency in bursts for sudden traffic spikes:
- First burst: up to the account burst limit (500-1,000 concurrent).
- After the burst: linear scaling of +1,000 concurrent executions per
  10 seconds until the account limit is reached.
- If the burst + linear scaling cannot meet demand, invocations are
  throttled (`TooManyRequestsException` / HTTP 429).

**Reserved concurrency** creates a guaranteed pool that is separate from
the account limit. A function with 50 reserved concurrency always has 50
slots available, even if other functions are consuming the entire
account limit.

**Provisioned concurrency** pre-initializes environments and does not
count against burst scaling. It is the most predictable for latency-
sensitive workloads.

### Concurrency and downstream resources

High Lambda concurrency can overwhelm downstream resources:
- **RDS connections:** each concurrent execution opens a DB connection.
  A function with 1,000 concurrent executions can exhaust RDS
  connection limits (default max_connections for RDS PostgreSQL is ~80
  on db.t3.micro). Use Amazon RDS Proxy or a connection pooler
  (PgBouncer) to multiplex connections.
- **API rate limits:** downstream AWS APIs (e.g., `dynamodb:Query`) have
  per-account rate limits. High Lambda concurrency can trigger
  throttling (`ThrottlingException`). Use reserved concurrency to cap
  the function below the downstream limit.

## Packaging limits

| Limit | Value |
|---|---|
| Compressed zip size | 50 MB |
| Uncompressed deployment (function + layers) | 250 MB |
| ECR image size | 10 GB |
| Environment variables total size | 32 KB |
| Layers per function | 5 |
| `/tmp` ephemeral storage | 512 MB - 10 GB |
| Memory | 128 MB - 10,240 MB |
| Timeout | 1 - 900 seconds |
