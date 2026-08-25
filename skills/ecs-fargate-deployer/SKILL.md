---
name: ecs-fargate-deployer
description: 'Deploys AWS ECS Fargate services with production-grade configuration: right-sized task definition (CPU/memory combos, Fargate sizing), container definitions (image, port mappings, env vars, health checks), service definition (desired count, deployment circuit breaker, minimum healthy percent), awsvpc networking (security groups, subnets), ALB integration (target group, listener rules), target-tracking auto-scaling (CPU/memory/ALB request count), separate task execution role and task role, secrets via Secrets Manager / SSM Parameter Store, FireLens and CloudWatch logging, and latest features (Fargate Spot, EFA, container health check improvements). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new ECS Fargate service, deploying a container to production, validating an ECS service configuration, or generating deployment CLI and IaC templates. Triggers: ECS Fargate, task definition, service, ALB, auto-scaling, container, deployment, ECS deploy.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ecs, ec2, iam, elasticloadbalancingv2, servicediscovery, logs, secretsmanager, and ssm access. Works with Terraform aws_ecs_service / aws_ecs_task_definition resources, CloudFormation AWS::ECS::* resources, and AWS Copilot.'
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
  tags: aws, ecs, fargate, cloudops, deploy, containers, task-definition, awsvpc, alb, auto-scaling
  dependencies: aws-orchestrator
  keywords: aws, ecs, fargate, cloudops, deploy, provisioning, containers, task-definition, awsvpc, alb, target-group, auto-scaling, circuit-breaker, firelens, fargate-spot
  when_to_use: Invoke when the user wants to create a new ECS Fargate service, deploy a container workload to Fargate, validate an existing ECS service configuration against best practices, generate deployment CLI commands or IaC templates, or troubleshoot a Fargate deployment failure caused by missing prerequisites (task definition, subnets, ALB, execution role, secrets). Do NOT invoke for ECS on EC2 deployments (use an EC2-launch-type-specific skill) or for EKS deployments (use an EKS skill).
---

# ECS Fargate Deployer

An AWS CloudOps agent skill that deploys Amazon ECS services on Fargate
with correct production defaults. Emits a READY_TO_DEPLOY checklist
verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the deployment order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Networking, ALB, auto-scaling, full NEVER, edge cases | `references/networking-and-scaling-guide.md` |

## STRICT output contract

When this skill is invoked with an ECS Fargate deployment request, the
agent MUST respond with the READY_TO_DEPLOY checklist defined in "Output
format" using the literal all-caps labels `SERVICE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines.

### Required output structure

1. `SERVICE: <service-name>` — the ECS service being deployed.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws ecs ...` commands.

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
SERVICE: payments-api-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Cluster — payments-prod (Fargate capacity provider)
  [✓]      Task definition — payments-api:5 (0.5 vCPU / 1024 MB)
  [✓]      Container — 123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3
  [✓]      Container health check — GET /healthz (30s interval, 5s timeout, 3 retries)
  [✓]      Networking — awsvpc, subnets subnet-aaa/subnet-bbb, sg-payments-api
  [✓]      Load balancer — ALB tg-payments-api:8080 (target type ip)
  [✓]      Desired count — 3 (across 3 AZs)
  [✓]      Deployment circuit breaker — enabled with rollback
  [✓]      Minimum healthy percent — 100% / Maximum percent — 200%
  [✓]      Execution role — payments-exec (ECR + Secrets Manager + SSM)
  [✓]      Task role — payments-task (DynamoDB + S3 scoped)
  [✓]      Secrets — DB_PASSWORD from secretsmanager:payments/db:arn
  [✓]      Logging — FireLens → CloudWatch /ecs/payments-api, retention 30 days
  [✓]      Auto-scaling — target tracking 60% CPU, min 3 / max 12
VERIFICATION_COMMANDS:
  aws ecs describe-services --cluster payments-prod --services payments-api-prod
  aws ecs describe-task-definition --task-definition payments-api:5
  aws ecs describe-services --cluster payments-prod --services payments-api-prod --query 'services[0].deployments'
  aws ec2 describe-security-groups --group-ids sg-payments-api
  aws elbv2 describe-target-groups --target-group-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-payments-api/abc
  aws logs describe-log-groups --log-group-name-prefix /ecs/payments-api
  aws application-autoscaling describe-scaling-policies --service-namespace ecs --resource-id service/payments-prod/payments-api-prod
```

## Reasoning framework (why the deployment order matters)

1. **Task definition FIRST** — a service cannot be created without a valid
   `taskDefinition` ARN. Creating the service first returns `ClientException`.
2. **Execution role + task role (separate!)** — execution role pulls ECR
   image, retrieves secrets, writes logs. Task role is the app's runtime
   identity. Conflating them is the #1 IAM mistake on Fargate.
3. **Cluster + capacity provider** — Fargate and Fargate Spot are capacity
   providers, not launch types. The launch-type API does not support Spot.
4. **Networking (awsvpc + subnets + SG)** — Fargate REQUIRES
   `networkMode: awsvpc`. Use private subnets across >= 2 AZs. Without a
   NAT Gateway, AWS SDK calls fail silently with timeouts.
5. **Load balancer integration** — ALB target group MUST use
   `target_type=ip` (awsvpc tasks register by ENI private IP).
6. **Container health check + circuit breaker** — without a container-level
   health check, the circuit breaker cannot fire.
7. **Auto-scaling** — apply AFTER the service is stable, not during
   deployment.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Cluster** | Must exist with Fargate capacity provider. | `aws ecs describe-clusters --clusters <name>` |
| **Container image** | ECR image URI with valid tag. | `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` |
| **VPC subnets** | Private subnets in >= 2 AZs. | `aws ec2 describe-subnets --subnet-ids <ids>` |
| **Security group** | Inbound to container ports + outbound for deps. | `aws ec2 describe-security-groups --group-ids <sg>` |
| **ALB target group** (if ALB) | `target_type=ip` required. | `aws elbv2 describe-target-groups --target-group-arns <arn>` |
| **ALB listener** (if ALB) | Listener to attach rules to. | `aws elbv2 describe-listeners --listener-arns <arn>` |
| **Execution role** | Trust `ecs-tasks.amazonaws.com`. ECR + Secrets + logs perms. | `aws iam get-role --role-name <exec-role>` |
| **Task role** | Application permissions (DynamoDB, S3, etc.). | `aws iam get-role --role-name <task-role>` |
| **Secrets ARNs** (if secrets) | Secrets Manager or SSM Parameter exists. | `aws secretsmanager describe-secret --secret-id <id>` |
| **CloudWatch log group** | ECS does NOT auto-create log groups. Pre-create with retention. | `aws logs describe-log-groups --log-group-name-prefix /ecs/<service>` |
| **KMS key** (if encrypted) | Grant execution role `kms:Decrypt`. | `aws kms describe-key --key-id <alias>` |

## Deployment procedure (apply in order)

### Step 1: Task execution role + task role (separate)

**Two distinct roles. Never combine them.**

Trust policy (both roles):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ecs-tasks.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

**Execution role** — ECS agent uses it to pull ECR image, retrieve secrets,
write logs. Attach `AmazonECSTaskExecutionRolePolicy` plus any
secrets/KMS permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], "Resource": "arn:aws:ecr:<region>:<acct>:repository/<repo>"},
    {"Effect": "Allow", "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:<region>:<acct>:log-group:/ecs/<service>:*"},
    {"Effect": "Allow", "Action": ["secretsmanager:GetSecretValue", "ssm:GetParameters"], "Resource": ["arn:aws:secretsmanager:<region>:<acct>:secret:<name>*"]},
    {"Effect": "Allow", "Action": ["kms:Decrypt"], "Resource": "arn:aws:kms:<region>:<acct>:key/<id>"}
  ]
}
```

**Task role** — assumed by application code at runtime. Scope to specific
AWS resources (DynamoDB, S3, SQS). Has nothing to do with image pulls.

| Workload | Task role permissions |
|---|---|
| API backend (DynamoDB) | `dynamodb:GetItem`, `PutItem`, `Query` on table ARN |
| Queue consumer (SQS) | `sqs:ReceiveMessage`, `DeleteMessage` on queue ARN |
| S3 processor | `s3:GetObject`, `PutObject` on bucket ARN |

**NEVER use `AdministratorAccess` on either role.**

### Step 2: Task definition (CPU/memory combos)

Fargate enforces **specific CPU/memory combinations**. Any other combo
fails with `ClientException`.

| CPU (vCPU) | Memory options (GB) |
|---|---|
| 0.25 | 0.5, 1, 2 |
| 0.5 | 1, 2, 3, 4 |
| 1 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 4, 5, 6, ..., 16 |
| 4 | 8, 9, 10, ..., 30 |
| 8 | 16, 17, ..., 60 |
| 16 | 32, 33, ..., 120 |

CPU units: 256 = 0.25 vCPU. Memory: 1024 = 1 GB.

| Workload | CPU | Memory | Rationale |
|---|---|---|---|
| Lightweight API | 0.25 vCPU | 0.5 GB | Low traffic, fast startup |
| Standard API | 0.5 vCPU | 1 GB | Typical Node/Python API |
| Heavy API (ML inference) | 1-2 vCPU | 4-8 GB | Parallel processing |
| Worker (queue consumer) | 0.5-1 vCPU | 1-2 GB | I/O-bound |
| Java/JVM (Spring Boot) | 1-2 vCPU | 4-8 GB | JVM heap; always >= 2 GB |

**Architecture:** Fargate supports `X86_64` (default) and `ARM64`
(Graviton, up to 20% price-performance). Set `runtimePlatform.cpuArchitecture`.

### Step 3: Container definitions

```json
[{
  "name": "app",
  "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3",
  "cpu": 512, "memory": 1024, "essential": true,
  "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
  "environment": [{"name": "LOG_LEVEL", "value": "info"}],
  "secrets": [{"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:payments/db-XXXXXX"}],
  "logConfiguration": {"logDriver": "awslogs", "options": {"awslogs-group": "/ecs/payments-api", "awslogs-region": "us-east-1", "awslogs-stream-prefix": "ecs"}},
  "healthCheck": {"command": ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"], "interval": 30, "timeout": 5, "retries": 3, "startPeriod": 60}
}]
```

Key fields: **image** (full ECR URI, NEVER `:latest`), **portMappings**
(`hostPort` ignored on Fargate), **environment** (plaintext only, NEVER
secrets), **secrets** (injected at start via ARN reference), **healthCheck**
(`startPeriod` gives grace time), **essential** (true = failure stops task).

### Step 4: Service definition

```bash
aws ecs create-service \
  --cluster payments-prod \
  --service-name payments-api-prod \
  --task-definition payments-api:5 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[sg-payments-api],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-payments-api/abc,containerName=app,containerPort=8080" \
  --deployment-configuration "deploymentCircuitBreaker={enable=true,rollback=true},minimumHealthyPercent=100,maximumPercent=200" \
  --scheduling-strategy REPLICA
```

Key fields:
- **desiredCount** — >= 2 across >= 2 AZs for HA.
- **deploymentCircuitBreaker** — `enable=true, rollback=true` auto-rolls
  back failed deployments. Without it, a bad task definition leaves service
  degraded indefinitely.
- **minimumHealthyPercent=100** — old tasks stay until new ones are healthy.
- **maximumPercent=200** — allows rolling double during deployment.
- **assignPublicIp=DISABLED** for private subnets (production).

**Capacity provider strategy (preferred over launch-type for Spot):**

```bash
aws ecs create-service \
  --cluster payments-prod \
  --service-name payments-api-prod \
  --task-definition payments-api:5 \
  --desired-count 6 \
  --capacity-provider-strategy \
    capacityProvider=FARGATE,weight=4,base=2 \
    capacityProvider=FARGATE_SPOT,weight=1 \
  ...
```

`base=2` guarantees 2 On-Demand tasks; remaining split 4:1 between
FARGATE and FARGATE_SPOT. Spot interruption drains tasks gracefully via
the 2-minute warning.

### Step 5: Networking (awsvpc mode)

Fargate REQUIRES `networkMode: awsvpc`. Each task gets a primary ENI.

- **Use PRIVATE subnets** in production. Tasks do not need public IPs.
- **Spread across >= 2 AZs.** Set `availabilityZoneRebalancing=ENABLED`.
- **NAT Gateway for internet access** — #1 Fargate networking issue.
  Without it, task cannot reach ECR, AWS SDK endpoints, or external APIs.
- **VPC endpoints** for high-volume traffic (S3, DynamoDB, ECR) to avoid
  NAT Gateway charges. Gateway endpoints (S3, DynamoDB) are free.
- **Security group** — inbound from ALB SG on container port, outbound for
  dependencies.

Full networking reference in `references/networking-and-scaling-guide.md`.

### Step 6: Load balancer integration (ALB)

```bash
aws elbv2 create-target-group \
  --name tg-payments-api --protocol HTTP --port 8080 --vpc-id vpc-xxx \
  --target-type ip --health-check-path /healthz \
  --health-check-interval-seconds 30 --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 --matcher HttpCode=200
```

**Critical:** ALB health check path MUST match the container health check
path. A mismatch causes the ALB to mark the task unhealthy even when ECS
considers it healthy.

### Step 7: Secrets (Secrets Manager / SSM Parameter Store)

Secrets are injected as environment variables at container start. NOT
visible in the task definition (only the ARN is).

```json
"secrets": [
  {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:payments/db-XXXXXX"},
  {"name": "API_KEY", "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/payments/api-key"}
]
```

Execution role needs `secretsmanager:GetSecretValue` or `ssm:GetParameters`
plus `kms:Decrypt` if a customer-managed KMS key is used.

### Step 8: Logging (FireLens / CloudWatch)

**awslogs driver (default):**
```json
"logConfiguration": {
  "logDriver": "awslogs",
  "options": {"awslogs-group": "/ecs/payments-api", "awslogs-region": "us-east-1", "awslogs-stream-prefix": "ecs"}
}
```

**FireLens (advanced routing):** route different log streams to different
destinations (audit → S3, app → CloudWatch, metrics → Kinesis). Uses a
sidecar container with `firelensConfiguration: {type: fluentbit}`.

Pre-create the log group with retention — ECS does NOT auto-create:
```bash
aws logs create-log-group --log-group-name /ecs/payments-api
aws logs put-retention-policy --log-group-name /ecs/payments-api --retention-in-days 30
```

### Step 9: Auto-scaling (target tracking)

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/payments-prod/payments-api-prod \
  --min-capacity 3 --max-capacity 12

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/payments-prod/payments-api-prod \
  --policy-name payments-api-cpu-60 --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 60.0,
    "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"},
    "ScaleOutCooldown": 60, "ScaleInCooldown": 300}'
```

Metrics: `ECSServiceAverageCPUUtilization`, `ECSServiceAverageMemoryUtilization`,
`ALBRequestCountPerTarget`. Cooldown: scale-out 60s, scale-in 300s (never
< 300s to avoid flapping).

### Step 10: Verification

```bash
aws ecs describe-services --cluster <cluster> --services <service>
aws ecs describe-task-definition --task-definition <family>:<rev>
aws ecs describe-tasks --cluster <cluster> --tasks <task-id>
aws elbv2 describe-target-health --target-group-arn <arn>
aws logs describe-log-groups --log-group-name-prefix /ecs/<service>
aws application-autoscaling describe-scaling-policies --service-namespace ecs
```

## Latest ECS Fargate features (2024-2026)

- **Fargate Spot capacity provider (GA):** Spot drains tasks on 2-minute
  warning. Use capacity-provider strategy with `base=N` on FARGATE plus
  FARGATE_SPOT for burst capacity.
- **EFA support on Fargate (2024-2025):** Elastic Fabric Adapter for ML/HPC
  workloads. Available on selected CPU configs.
- **Container health check improvements (2024-2025):** `START_PERIOD`
  (1-300s) configurable per container. Eliminates false-negative rollbacks
  for slow-start JVM/Spring workloads.
- **Availability Zone rebalancing (2024-2025):** ECS auto-rebalances tasks
  across AZs after failure. Set `availabilityZoneRebalancing=ENABLED`.
- **Deployment circuit breaker rollback (GA):** auto-rolls back failed
  deployments. Requires `enableExecution=true` + container health check.
- **Graviton (ARM64) on Fargate (2024-2025):** `runtimePlatform.cpuArchitecture=ARM64`
  for up to 20% price-performance. Image must be ARM64.
- **Fargate platform version 1.4 (current default):** `LATEST` no longer
  auto-upgrades — pin `platformVersion` for reproducibility.
- **ECS Exec (session manager):** `enableExecuteCommand` for shell access.
  Never enable in production without audit review.

## Workload matrix

| Workload | CPU / Memory | AZ count | LB | Auto-scale | Spot | Logging |
|---|---|---|---|---|---|---|
| **Public API** | 0.5 vCPU / 1 GB | 3 | ALB | CPU 60% | No | awslogs |
| **Internal API** | 0.5 vCPU / 1 GB | 2 | Internal ALB | CPU 60% | Optional | awslogs |
| **Queue worker (SQS)** | 0.5-1 vCPU / 1-2 GB | 2 | None | Queue depth | Yes | awslogs |
| **Scheduled batch** | 1-2 vCPU / 2-4 GB | 1 | None | None | Yes | awslogs |
| **ML inference** | 4 vCPU / 16 GB | 2 | ALB | CPU 70% | No | FireLens |
| **Streaming (Kinesis)** | 1 vCPU / 2 GB | 2 | None | None | No | awslogs |
| **Java/Spring Boot** | 1-2 vCPU / 4-8 GB | 3 | ALB | CPU 65% | No | awslogs + startPeriod 60s |

## NEVER (top 5 — full list of 14 in references)

- NEVER use `:latest` image tag in production. It is mutable — a new push
  silently changes what runs. Pin to a version tag or SHA digest. #1
  rollback-breaker.
- NEVER combine the execution role and task role into one. Execution role
  pulls images and writes logs; task role is the app's identity. Combining
  produces pull failures or least-privilege violations.
- NEVER use a target group with `target_type=instance` for Fargate. Fargate
  tasks register by ENI private IP — only `target_type=ip` works. Silently
  fails registration.
- NEVER deploy Fargate tasks to a public subnet with
  `assignPublicIp=ENABLED` in production. Use private subnets + NAT
  Gateway or VPC endpoints.
- NEVER deploy without the deployment circuit breaker when using rolling
  deployments. Without `enable=true, rollback=true`, a bad task definition
  leaves the service degraded indefinitely.

## Expert heuristic — choosing CPU, memory, and AZ spread

- **60/70 rule:** CPU target tracking at 60% for latency-sensitive, 70%
  for batch. Scale-out takes ~60-90s on Fargate.
- **Memory: 2x the working set.** JVM app with 2 GB heap needs >= 4 GB.
  Set `-XX:MaxRAMPercentage=75`.
- **AZ spread:** minimum 2 AZs for HA, 3 for user-facing. Pair with
  `desiredCount >= AZ count`.
- **Fargate Spot blend:** `base=2` on FARGATE + FARGATE_SPOT weight 1-3
  for burst. NEVER put stateful workloads on Spot.
- **ALB vs. NLB:** ALB for HTTP/HTTPS, NLB for TCP/TLS. Target type must
  be `ip` either way.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm cluster exists with Fargate capacity provider.**
- **Confirm ECR image exists** — missing image causes `CannotPullContainerError`.
- **Confirm both roles exist** and trust `ecs-tasks.amazonaws.com`.
- **Confirm target group is `target_type=ip`** — `instance` silently fails.
- **Confirm subnets are private and span >= 2 AZs.**
- **Pre-create CloudWatch log group with retention.**
- **For existing services, capture current config for rollback.**

Full CLI sequences for all checks in `references/networking-and-scaling-guide.md`.

## Output format — MANDATORY literal labels

When invoked with a service deployment request, your ENTIRE response MUST
be the checklist block below. The labels are **case-sensitive all-caps
keywords**. Do NOT write a preamble. Start with `SERVICE:` and stop after
the `VERIFICATION_COMMANDS:` block.

```text
SERVICE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Cluster — <cluster> (Fargate capacity provider)
  [✓]      Task definition — <family>:<rev> (<cpu> vCPU / <memory> MB)
  [✓]      Container — <image-uri>
  [✓]      Container health check — <path> (<interval>, <timeout>, <retries>)
  [✓]      Networking — awsvpc, subnets <subnets>, sg-<name>
  [✓]      Load balancer — ALB <tg-name>:<port> (target type ip)
  [✓]      Desired count — <n> (across <az-count> AZs)
  [✓]      Deployment circuit breaker — enabled with rollback
  [✓]      Minimum healthy percent — 100% / Maximum percent — 200%
  [✓]      Execution role — <exec-role> (ECR + Secrets Manager + logs)
  [✓]      Task role — <task-role> (<service-specific permissions>)
  [✓]      Secrets — <secret-names> from secretsmanager / ssm
  [✓]      Logging — FireLens / awslogs → CloudWatch /ecs/<name>, retention <days>
  [OPTIONAL] Auto-scaling — target tracking <metric> <target>, min <x> / max <y>
VERIFICATION_COMMANDS:
  aws ecs describe-services --cluster <cluster> --services <name>
  aws ecs describe-task-definition --task-definition <family>:<rev>
  aws ec2 describe-security-groups --group-ids <sg>
  aws elbv2 describe-target-health --target-group-arn <tg-arn>
  aws logs describe-log-groups --log-group-name-prefix /ecs/<name>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is missing
(cluster, task definition, subnets, execution role, target group ARN for
ALB-fronted service), the verdict is `PREREQUISITES_MISSING`.

## Domain

AWS CloudOps / ECS Fargate Container Compute Provisioning.

## Edge-case handling

- **Cross-account ECR pull:** execution role needs `ecr:BatchGetImage` on
  the cross-account repo AND the repo policy in the other account must
  grant your root.
- **ECS Exec in production:** `enableExecuteCommand=true` allows shell
  access. Bypasses bastion auditing. Enable only for break-glass.
- **ALB vs. container health check divergence:** if ALB passes but
  container check fails, ECS marks task unhealthy while ALB keeps sending
  traffic. Align both checks.
- **Slow-start JVM tasks:** set `healthCheck.startPeriod=60` and
  `unhealthyThresholdCount=3` to avoid spurious rollback.
- **Spot interruption drain:** Fargate Spot sends 2-min warning + SIGTERM.
  Set `stopTimeout=30` for graceful shutdown.
- **Capacity provider vs. launch type:** once a service uses a
  capacity-provider strategy, you cannot switch back without recreating.
- **Service Connect / Cloud Map:** namespace must exist before service
  creation for service-to-service discovery.

## AWS documentation

- **Amazon ECS Developer Guide** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- **ECS Fargate** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- **ECS Task Definition** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html
- **ECS Service** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html
- **Fargate CPU/Memory** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#task_size
- **ECS Capacity Providers** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-capacity-providers.html
- **ECS Deployment Circuit Breaker** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
- **ECS Logging with FireLens** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_firelens.html
- **ECS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ecs/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI command
  sequence for all 10 deployment steps, including execution role + task role
  creation, task definition registration, service creation, ALB target group
  + listener rule, auto-scaling, and Terraform equivalents.

- `references/networking-and-scaling-guide.md` — deep reference on awsvpc
  networking (ENI lifecycle, NAT Gateway vs VPC endpoints), ALB integration,
  target-tracking auto-scaling, Fargate Spot strategy, full NEVER list,
  edge-case handling, expert heuristics, and pre-flight safety CLI.
