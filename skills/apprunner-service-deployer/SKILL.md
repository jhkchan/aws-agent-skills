---
name: apprunner-service-deployer
description: 'Deploys AWS App Runner services with production-grade configuration: source selection (ECR image vs source code repository), right-sized compute (CPU/memory combos), instance config (port, env vars, secrets via Secrets Manager / SSM), auto-scaling (min/max instances, concurrency), VPC connector for private resources (RDS, ElastiCache), custom domain with managed TLS, observability (CloudWatch Logs, X-Ray tracing), deployment control (automatic vs manual), health check policy, and latest features (VPC ingress, ALB integration, ARM64/Graviton). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new App Runner service, deploying a container web app or API, validating an App Runner configuration, or generating deployment CLI and IaC templates. Triggers: App Runner, ECR source, source code repository, auto-scaling, VPC connector, custom domain, App Runner deploy.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with apprunner, ecr, iam, ec2, servicediscovery, secretsmanager, ssm, logs, and route53 access. Works with Terraform aws_apprunner_* resources, CloudFormation AWS::AppRunner::* resources, and the AWS Console App Runner wizard.'
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
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, app-runner, apprunner, cloudops, deploy, containers, ecr, auto-scaling, vpc-connector
  dependencies: aws-orchestrator
  keywords: aws, app-runner, apprunner, cloudops, deploy, provisioning, containers, ecr, source-code, auto-scaling, vpc-connector, custom-domain, health-check, observability, xray
  when_to_use: Invoke when the user wants to create a new App Runner service, deploy a containerized web app or API to App Runner, validate an existing App Runner configuration against best practices, generate deployment CLI commands or IaC templates, or troubleshoot an App Runner deployment failure caused by missing prerequisites (ECR access role, VPC connector, instance role, encryption KMS key). Do NOT invoke for ECS Fargate (use ecs-fargate-deployer), Lambda (use lambda-function-deployer), or EC2-based deployments.
---

# App Runner Service Deployer

An AWS CloudOps agent skill that deploys Amazon App Runner services with
correct production defaults. Emits a READY_TO_DEPLOY checklist verifying
every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the deployment order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Source-type decision matrix | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/cli-commands-and-iac.md` |
| VPC, scaling, observability, full NEVER | `references/source-and-config-guide.md` |

## STRICT output contract

When this skill is invoked with an App Runner deployment request, the
agent MUST respond with the READY_TO_DEPLOY checklist defined in "Output
format" using the literal all-caps labels `SERVICE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines.

### Required output structure

1. `SERVICE: <service-name>` — the App Runner service being deployed.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws apprunner ...`
   commands.

### FORBIDDEN output patterns

- **No prose preamble before `SERVICE:`** — first non-empty line MUST be
  `SERVICE:`.
- **No markdown variants of labels** — write `VERDICT:`, not `**VERDICT:**`,
  `### Verdict`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the checklist
  block is the entire response.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`.

### Perfect example (copy the shape exactly)

```text
SERVICE: checkout-api-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Source — ECR image 123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0
  [✓]      Source type — ECR (image), access role arn:aws:iam::123456789012:role/AppRunnerECRAccess
  [✓]      Instance configuration — 1 vCPU / 2048 MB, port 8080
  [✓]      Environment variables — LOG_LEVEL=info, ENV=production (plaintext)
  [✓]      Secrets — DB_PASSWORD from secretsmanager:checkout/db, STRIPE_KEY from ssm:/checkout/stripe
  [✓]      Instance role — checkout-instance (DynamoDB + S3 scoped)
  [✓]      Auto-scaling — min 2 / max 10, concurrency 100
  [✓]      VPC connector — arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc (3 subnets, 2 SGs)
  [✓]      Health check — GET /healthz (HTTP 200), healthy threshold 3, interval 10s
  [✓]      Deployment trigger — automatic (push to ECR)
  [✓]      Observability — CloudWatch Logs /aws/apprunner/checkout-api-prod, retention 30 days, X-Ray tracing enabled
  [OPTIONAL] Custom domain — checkout.example.com (managed TLS)
VERIFICATION_COMMANDS:
  aws apprunner describe-service --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc
  aws apprunner describe-vpc-connector --vpc-connector-arn arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc
  aws iam get-role --role-name AppRunnerECRAccess
  aws logs describe-log-groups --log-group-name-prefix /aws/apprunner/checkout-api-prod
```

## Reasoning framework (why the deployment order matters)

1. **Source FIRST** — App Runner needs either an ECR image or a source
   code repository. Without a valid source the create-service call fails
   with `ServiceQuotaExceededException` or `InvalidRequestException`.
2. **Access role for ECR (separate from instance role)** — the App Runner
   service assumes an access role to pull ECR images. This is NOT the
   same as the instance role the application uses at runtime. Conflating
   them is the #1 IAM mistake on App Runner.
3. **Instance configuration (CPU/memory)** — App Runner enforces specific
   CPU/memory combinations. The memory MUST be a multiple of the vCPU.
4. **VPC connector for private resources** — if the app talks to RDS,
   ElastiCache, or internal ALBs in private subnets, a VPC connector is
   REQUIRED. Without it, DNS resolves but connections time out silently.
5. **Health check** — App Runner probes the service on the configured
   port and path. A mismatched path causes the service to stay in
   `CreateFailed` or cycle through `OperationInProgress` indefinitely.
6. **Auto-scaling** — provisioned concurrency is the ONLY latency
   guarantee. Scale-to-zero saves cost but adds cold-start latency.
7. **Observability** — App Runner streams logs to CloudWatch by default,
   but the log group name is derived from the service name and is NOT
   configurable. X-Ray tracing must be explicitly enabled.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **ECR image (if ECR source)** | Must exist with valid tag. NEVER `:latest`. | `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` |
| **ECR access role (if ECR source)** | Trust `tasks.apprunner.amazonaws.com`. ECR pull perms. | `aws iam get-role --role-name <access-role>` |
| **Source repo + connection (if code source)** | CodeConnection ARN for GitHub/GitLab/Bitbucket. | `aws codeconnections list-connections` |
| **Build runtime (if code source)** | Python 3 / Node.js / Java / Go / PHP / .NET supported. | Check `apprunner:BuildConfiguration Runtime` in the create call. |
| **Instance role (if app calls AWS services)** | Trust `tasks.apprunner.amazonaws.com`. Scope to resources. | `aws iam get-role --role-name <instance-role>` |
| **VPC connector (if private resources)** | Subnets + security groups for private VPC access. | `aws apprunner describe-vpc-connector --vpc-connector-arn <arn>` |
| **VPC ingress (if private endpoint)** | Optional: restrict service to private VPC clients only. | `aws apprunner describe-vpc-ingress-connection` |
| **Secrets ARNs (if secrets)** | Secrets Manager or SSM Parameter exists. | `aws secretsmanager describe-secret --secret-id <id>` |
| **KMS key (if encryption)** | App Runner uses AWS-owned key by default. CMK needs grant. | `aws kms describe-key --key-id <alias>` |
| **Custom domain (optional)** | Owned / verified in Route 53 or via certificate. | `aws apprunner describe-custom-domains --service-arn <arn>` |
| **App Runner service quota** | Default 25 services per region per account. | `aws service-quotas get-service-quota --service-code apprunner --quota-code L-DBB8PPEX` |

## Deployment procedure (apply in order)

### Step 1: ECR access role (for ECR source — separate from instance role)

**Two distinct roles. Never combine them.**

The ECR access role is assumed by the App Runner service to pull the
container image. The instance role is assumed by the application at
runtime. They are NEVER the same role.

```bash
aws iam create-role \
  --role-name AppRunnerECRAccess \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name AppRunnerECRAccess \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

`AWSAppRunnerServicePolicyForECRAccess` grants `ecr:GetDownloadUrlForLayer`,
`ecr:BatchGetImage`, `ecr:GetAuthorizationToken`. It is the managed policy
purpose-built for this role. Do NOT write a custom inline policy for ECR
pull — the managed policy is scoped and maintained by AWS.

### Step 2: Instance role (application runtime identity)

The instance role is assumed by the application at runtime for AWS SDK
calls (DynamoDB, S3, Secrets Manager, etc.).

```bash
aws iam create-role \
  --role-name <service>-instance \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name <service>-instance \
  --policy-name <service>-app-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:<region>:<acct>:table/<table>"
      },
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:<region>:<acct>:secret:<service>/*"
      }
    ]
  }'
```

| Workload | Instance role permissions |
|---|---|
| API backend (DynamoDB) | `dynamodb:GetItem`, `PutItem`, `Query` on table ARN |
| API backend (RDS via VPC connector) | No IAM — RDS auth is via secrets. Instance role fetches the secret. |
| S3 processor | `s3:GetObject`, `PutObject` on bucket ARN |
| SQS consumer | `sqs:ReceiveMessage`, `DeleteMessage` on queue ARN |

**NEVER use `AdministratorAccess` on either role.**

### Step 3: Instance configuration (CPU/memory combos)

App Runner enforces **specific CPU/memory combinations**. Any other combo
fails at create-service time.

| CPU (vCPU) | Memory options (GB) |
|---|---|
| 1 (1024) | 2, 3, 4 |
| 2 (2048) | 4, 5, 6, 7, 8 |
| 4 (4096) | 8, 9, 10, ..., 16 |

CPU units: 1024 = 1 vCPU. Memory: 2048 = 2 GB. Memory MUST be >= 2x CPU.

| Workload | CPU | Memory | Rationale |
|---|---|---|---|
| Lightweight API | 1 vCPU | 2 GB | Low traffic, fast startup |
| Standard API | 2 vCPU | 4 GB | Typical Node/Python API |
| Heavy API (ML inference) | 4 vCPU | 8-16 GB | Parallel processing |
| Worker (queue consumer) | 1 vCPU | 2 GB | I/O-bound |
| Java/JVM (Spring Boot) | 2 vCPU | 6-8 GB | JVM heap; always >= 4 GB |

### Step 4: VPC connector (private resources)

**This is the #1 App Runner networking pitfall.** If your app connects
to RDS, ElastiCache, internal ALBs, or any VPC-only resource, you MUST
attach a VPC connector. Without it, DNS resolves but the TCP connection
hangs silently until timeout.

```bash
aws apprunner create-vpc-connector \
  --vpc-connector-name <service>-vpc \
  --subnets subnet-aaa subnet-bbb subnet-ccc \
  --security-groups sg-priv-app
```

Rules:
- **Use PRIVATE subnets.** App Runner instances do not need public IPs.
- **Span >= 2 AZs** (3 for production HA).
- **Security group outbound** must allow the database port (e.g., 5432
  for Postgres, 3306 for MySQL, 6379 for Redis).
- **NAT Gateway NOT required** — the VPC connector uses AWS PrivateLink
  internally. The connector itself does not need internet access.
- **VPC connector is a separate resource** — create it before the service.

### Step 5: Health check policy

App Runner probes the service on the configured path and port. A
mismatched path or port causes the service to stay in `CreateFailed`.

```json
{
  "Type": "APP",
  "Protocol": "HTTP",
  "Path": "/healthz",
  "IntervalInSeconds": 10,
  "TimeoutInSeconds": 5,
  "HealthyThreshold": 3,
  "UnhealthyThreshold": 5
}
```

- **Path MUST return HTTP 200** for the service to be considered healthy.
- **Interval 10s, healthy threshold 3** means a service is marked healthy
  after ~30s of successful probes.
- **Unhealthy threshold 5** means a service is marked unhealthy after
  ~50s of consecutive failures. NEVER set below 3 — transient blips
  cause spurious rollbacks.
- **If no health check is configured**, App Runner uses TCP probe on the
  service port. This catches the port being closed but NOT app-level
  unhealthiness (e.g., DB pool exhausted).

### Step 6: Auto-scaling configuration

```bash
aws apprunner update-service \
  --service-arn <arn> \
  --auto-scaling-configuration-arn arn:aws:apprunner:<region>:<acct>:autoscalingconfiguration/DefaultConfiguration/1
```

Custom auto-scaling:

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name <service>-autoscale \
  --min-size 2 \
  --max-size 10 \
  --max-concurrency 100
```

| Parameter | Default | Production | Why |
|---|---|---|---|
| `min-size` | 1 | 2 (HA) | 1 = single point of failure during AZ outage |
| `max-size` | 25 | 10-20 | Cap cost; tune to traffic profile |
| `max-concurrency` | 100 | 50-200 | Requests per instance. Lower for CPU-heavy. |

- **Scale-to-zero**: `min-size=0` saves cost but adds cold-start latency
  (30-60s). ONLY for dev/staging or non-user-facing batch endpoints.
- **Provisioned concurrency** = `min-size >= 1`. This is the ONLY latency
  guarantee. At least one instance is always warm.
- **Scaling metric**: App Runner uses concurrent requests per instance
  (not CPU). An instance scales when `max-concurrency` is exceeded.

### Step 7: Secrets (Secrets Manager / SSM Parameter Store)

Secrets are injected as environment variables at runtime via ARN
reference in `ConfigurationSources`. NOT visible in plaintext.

```json
{
  "RuntimeEnvironmentSecrets": [
    {"DB_PASSWORD": "arn:aws:secretsmanager:us-east-1:123456789012:secret:checkout/db-XXXXXX"},
    {"STRIPE_KEY": "arn:aws:ssm:us-east-1:123456789012:parameter/checkout/stripe-key"}
  ]
}
```

Instance role needs `secretsmanager:GetSecretValue` or
`ssm:GetParameters` plus `kms:Decrypt` if a customer-managed KMS key is
used.

### Step 8: Observability (CloudWatch Logs, X-Ray, Application Signals)

**CloudWatch Logs:** App Runner streams to
`/aws/apprunner/<service-name>/<service-id>`. The log group name is NOT
configurable — it is derived from the service name. Pre-create a log
group with the right retention BEFORE creating the service, or App Runner
creates one with `Never Expire`.

```bash
aws logs create-log-group --log-group-name /aws/apprunner/<service-name>
aws logs put-retention-policy \
  --log-group-name /aws/apprunner/<service-name> \
  --retention-in-days 30
```

**X-Ray tracing:** set `TracingConfiguration Vendor=AWSXRay`. The instance
role needs `xray:PutTraceSegments` and `xray:PutTelemetryRecords`.

**Application Signals:** auto-instrumented for Java, Python, Node.js when
tracing is enabled. No code changes required.

### Step 9: Custom domain (optional)

```bash
aws apprunner associate-custom-domain \
  --service-arn <arn> \
  --domain-name checkout.example.com \
  --enable-www-subdomain
```

App Runner provisions and manages the TLS certificate via AWS Certificate
Manager. For non-Route 53 domains, you must add CNAME records manually
to verify ownership.

### Step 10: Create the service

```bash
aws apprunner create-service \
  --service-name checkout-api-prod \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080",
        "RuntimeEnvironmentVariables": [
          {"LOG_LEVEL": "info"},
          {"ENV": "production"}
        ],
        "RuntimeEnvironmentSecrets": [
          {"DB_PASSWORD": "arn:aws:secretsmanager:us-east-1:123456789012:secret:checkout/db-XXXXXX"}
        ],
        "StartCommand": "node server.js"
      }
    },
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::123456789012:role/AppRunnerECRAccess"
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "2048",
    "Memory": "4096",
    "InstanceRoleArn": "arn:aws:iam::123456789012:role/checkout-instance"
  }' \
  --health-check-configuration '{
    "Type": "APP",
    "Protocol": "HTTP",
    "Path": "/healthz",
    "IntervalInSeconds": 10,
    "TimeoutInSeconds": 5,
    "HealthyThreshold": 3,
    "UnhealthyThreshold": 5
  }' \
  --network-configuration '{
    "EgressConfiguration": {
      "EgressType": "VPC",
      "VpcConnectorArn": "arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc"
    }
  }' \
  --observability-enabled \
  --observability-configuration-configuration-source AWS_XRAY \
  --tags Environment=production Application=checkout-api
```

### Step 11: Verification

```bash
aws apprunner describe-service --service-arn <arn>
aws apprunner describe-vpc-connector --vpc-connector-arn <vc-arn>
aws apprunner describe-observability-configuration --observability-configuration-arn <arn>
aws apprunner describe-auto-scaling-configuration --auto-scaling-configuration-arn <arn>
aws logs describe-log-groups --log-group-name-prefix /aws/apprunner/<service>
aws apprunner list-operations --service-arn <arn>
```

## Latest App Runner features (2024-2026)

- **VPC ingress connection (2024-2025):** allows clients in a private VPC
  to reach an App Runner service via AWS PrivateLink WITHOUT traversing
  the public internet. Configure with
  `aws apprunner create-vpc-ingress-connection`. This is the long-awaited
  "private endpoint" feature for App Runner.
- **Application Load Balancer integration (2024-2025):** App Runner
  services can now front an ALB for advanced routing (weighted target
  groups, path-based routing, sticky sessions). Previously only the
  managed App Runner endpoint was available.
- **ARM64 / Graviton support (2024-2025):** set `CpuArchitecture=ARM64`
  for up to 20% price-performance. The ECR image MUST be ARM64.
- **Manual deployments with pause/resume (2024-2025):** set
  `AutoDeploymentsEnabled=false` to pause automatic deployments. Trigger
  a manual deployment with `aws apprunner start-deployment`. Useful for
  controlled rollout windows and change-management compliance.
- **Observability configuration (2024-2025):** dedicated
  `ObservabilityConfiguration` resource for X-Ray tracing toggle without
  embedding it in the service definition.
- **Private worker mode (2024-2025):** services with no public endpoint,
  reachable only via VPC ingress. Eliminates the need for a "deny all"
  security group workaround.
- **Deployment priority queues (2024-2025):** concurrent deployments in
  the same account are queued. The service displays `OperationInProgress`
  status. Use `list-operations` to track progress.
- **Enhanced health checks (2024-2025):** TCP probe type for non-HTTP
  services. Previously only APP (HTTP) probe was available.

## Workload matrix

| Workload | CPU / Memory | VPC connector | Health check | Auto-scale | Custom domain |
|---|---|---|---|---|---|
| **Public API** | 2 vCPU / 4 GB | No | GET /healthz | min 2 / max 10 | Yes |
| **Internal API (private)** | 1 vCPU / 2 GB | Yes (RDS) | GET /healthz | min 2 / max 6 | No (VPC ingress) |
| **API with RDS** | 2 vCPU / 4 GB | Yes (REQUIRED) | GET /healthz | min 2 / max 10 | Yes |
| **Worker (queue consumer)** | 1 vCPU / 2 GB | Yes (SQS optional) | TCP probe | min 1 / max 4 | No |
| **ML inference** | 4 vCPU / 16 GB | No | GET /healthz | min 2 / max 6 | Yes |
| **Java/Spring Boot** | 2 vCPU / 8 GB | Yes (if RDS) | GET /actuator/health | min 2 / max 10 | Yes |
| **Private worker** | 1 vCPU / 2 GB | Yes (VPC ingress) | TCP probe | min 1 / max 3 | No |

## NEVER (top 5 — full list of 12 in references)

- NEVER use `:latest` image tag in production. It is mutable — a new push
  silently changes what runs. Pin to a version tag or SHA digest. #1
  rollback-breaker. The App Runner service auto-deploys the new `:latest`
  without warning if `AutoDeploymentsEnabled=true`.
- NEVER conflate the ECR access role and the instance role. The access
  role pulls images (managed policy `AWSAppRunnerServicePolicyForECRAccess`);
  the instance role is the app's runtime identity. Combining produces
  pull failures or least-privilege violations.
- NEVER deploy an App Runner service that connects to private VPC
  resources (RDS, ElastiCache, internal ALBs) without a VPC connector.
  The DNS resolves but the TCP connection hangs silently until timeout.
  This is the #1 silent-failure pitfall.
- NEVER set `unhealthyThreshold < 3` on the health check. Transient
  network blips cause spurious rollbacks. Production minimum is 3; the
  default of 5 is safer.
- NEVER rely on the default auto-scaling configuration for production
  user-facing services. The default `min-size=1` is a single point of
  failure during an AZ outage. Set `min-size >= 2` for HA.

## Expert heuristic — choosing source type, sizing, and scaling

- **Source type decision:** ECR image for pre-built containers (fast
  deploy, full control over build pipeline). Source code repository for
  rapid prototyping and teams without a container build pipeline (App
  Runner builds the image for you, but you give up build-time control).
- **60/70 rule:** App Runner scales on concurrency, not CPU. Target
  `max-concurrency=100` for standard APIs, `50` for CPU-heavy. Monitor
  p99 latency and adjust.
- **Memory: 2x the working set.** JVM app with 2 GB heap needs >= 4 GB.
  Set `-XX:MaxRAMPercentage=75`.
- **VPC connector sizing:** the connector uses a pool of ENIs. For
  high-throughput services (thousands of concurrent DB connections),
  create a dedicated connector rather than sharing one across services.
- **Scale-to-zero:** ONLY for dev/staging or non-user-facing batch. Cold
  start is 30-60s. User-facing endpoints MUST have `min-size >= 1`.
- **Deployment trigger:** automatic (`AutoDeploymentsEnabled=true`) for
  dev/staging. Manual (`false` + `start-deployment`) for production with
  change-management compliance.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm ECR image exists** — missing image causes `CreateFailed`.
- **Confirm access role exists and trusts `tasks.apprunner.amazonaws.com`.**
- **Confirm instance role exists (if app calls AWS services).**
- **Confirm VPC connector exists (if private resources are involved).**
- **Confirm secrets ARNs resolve** — missing secret causes `CreateFailed`.
- **Pre-create CloudWatch log group with retention** (App Runner does NOT
  auto-set retention; defaults to `Never Expire`).
- **For existing services, capture current config for rollback.**

Full CLI sequences for all checks in `references/source-and-config-guide.md`.

## Output format — MANDATORY literal labels

When invoked with a service deployment request, your ENTIRE response MUST
be the checklist block below. The labels are **case-sensitive all-caps
keywords**. Do NOT write a preamble. Start with `SERVICE:` and stop after
the `VERIFICATION_COMMANDS:` block.

```text
SERVICE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Source — ECR image <uri> | source code repo <url>
  [✓]      Source type — ECR (image) | CODE (source repo), access role <role-arn>
  [✓]      Instance configuration — <cpu> vCPU / <memory> MB, port <port>
  [✓]      Environment variables — <plaintext vars>
  [✓]      Secrets — <secret-names> from secretsmanager / ssm
  [✓]      Instance role — <instance-role> (<app-permissions>)
  [✓]      Auto-scaling — min <x> / max <y>, concurrency <n>
  [✓]      VPC connector — <vc-arn> (<subnet-count> subnets, <sg-count> SGs)
  [✓]      Health check — GET <path> (HTTP 200), healthy threshold <n>, interval <s>
  [✓]      Deployment trigger — automatic | manual
  [✓]      Observability — CloudWatch Logs /aws/apprunner/<name>, retention <days>, X-Ray tracing <enabled|disabled>
  [OPTIONAL] Custom domain — <domain> (managed TLS)
VERIFICATION_COMMANDS:
  aws apprunner describe-service --service-arn <arn>
  aws apprunner describe-vpc-connector --vpc-connector-arn <vc-arn>
  aws iam get-role --role-name <access-role>
  aws logs describe-log-groups --log-group-name-prefix /aws/apprunner/<name>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is missing
(ECR access role, ECR image, VPC connector for private-resource workloads,
instance role for AWS-SDK-calling apps, secrets ARN for named secrets),
the verdict is `PREREQUISITES_MISSING`.

## Domain

AWS CloudOps / App Runner Managed Container Compute Provisioning.

## Edge-case handling

- **Cross-account ECR pull:** the access role needs
  `ecr:BatchGetImage` on the cross-account repo AND the repo policy in
  the other account must grant your root. The managed
  `AWSAppRunnerServicePolicyForECRAccess` does NOT cover cross-account —
  add an inline policy.
- **VPC connector sharing:** a VPC connector can be attached to multiple
  services, but the ENI pool is shared. For high-throughput workloads,
  create a dedicated connector per service.
- **Private endpoint mode:** set the network egress type to `VPC` and
  create a VPC ingress connection in the consumer VPC. The service has
  no public URL — only the PrivateLink endpoint.
- **Slow-start JVM tasks:** set `unhealthyThreshold=5` and
  `interval=10s` to give the JVM 50s to start before being marked
  unhealthy. For very slow starts, consider `StartCommand` with a
  readiness probe wrapper.
- **Source code repository build failures:** App Runner builds the image
  from source if `ImageRepositoryType=ECR` is not set. Build failures
  show up in `list-operations` as `OperationType=CREATE_SERVICE` with
  `Status=FAILED`. Check the build logs in CloudWatch under
  `/aws/apprunner/<service>/build`.
- **Auto-deployment surprises:** `AutoDeploymentsEnabled=true` means
  every push to the source branch triggers a deployment. For production,
  use `false` and trigger `start-deployment` after review.
- **Log group naming:** the log group is `/aws/apprunner/<service-name>`
  (NOT the service ARN). If you rename the service, the log group does
  NOT follow — old logs stay under the old name.

## AWS documentation

- **AWS App Runner Developer Guide** — https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html
- **App Runner CreateService API** — https://docs.aws.amazon.com/apprunner/latest/api/API_CreateService.html
- **App Runner VPC Connector** — https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html
- **App Runner VPC Ingress** — https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc-ingress.html
- **App Runner Auto Scaling** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-autoscaling.html
- **App Runner Custom Domains** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-custom-domains.html
- **App Runner Observability** — https://docs.aws.amazon.com/apprunner/latest/dg/observability.html
- **App Runner Deployment Methods** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-deploy.html
- **App Runner CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/apprunner/

## References

- `references/cli-commands-and-iac.md` — full copy-pasteable CLI command
  sequence for all 11 deployment steps, including access role and
  instance role creation, VPC connector creation, auto-scaling
  configuration, service creation with health check and observability,
  and Terraform / CloudFormation equivalents.

- `references/source-and-config-guide.md` — deep reference on source
  type selection (ECR vs code repository), VPC connector networking,
  auto-scaling tuning, health check policy, observability configuration,
  custom domain, full NEVER list, edge-case handling, and pre-flight
  safety CLI.
