---
name: ecs-fargate-deployer
description: 'Deploys AWS ECS Fargate services with production-grade configuration: right-sized task definition (CPU/memory combos, Fargate sizing), container definitions (image, port mappings, env vars,
  health checks), service definition (desired count, deployment circuit breaker, minimum healthy percent), awsvpc networking (security groups, subnets), ALB integration (target group, listener rules), target-tracking
  auto-scaling (CPU/memory/ALB request count), separate task execution role and task role, secrets via Secrets Manager / SSM Parameter Store, FireLens and CloudWatch logging, and latest features (Fargate
  Spot, EFA, container health check improvements). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new ECS Fargate service, deploying a container to production,
  validating an ECS service configuration, or generating deployment CLI and IaC templates. Triggers: ECS Fargate, task definition, service, ALB, auto-scaling, container, deployment, ECS deploy.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ecs, ec2, iam, elasticloadbalancingv2, servicediscovery, logs, secretsmanager,
  and ssm access. Works with Terraform aws_ecs_service / aws_ecs_task_definition resources, CloudFormation AWS::ECS::* resources, and AWS Copilot.'
keywords:
- aws
- ecs
- fargate
- cloudops
- deploy
- provisioning
- containers
- task-definition
- awsvpc
- alb
- target-group
- auto-scaling
- circuit-breaker
- firelens
- fargate-spot
tags:
- aws
- ecs
- fargate
- cloudops
- deploy
- containers
- task-definition
- awsvpc
- alb
- auto-scaling
dependencies:
- aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
  - aws
  - ecs
  - fargate
  - cloudops
  - deploy
  - containers
  - task-definition
  - awsvpc
  - alb
  - auto-scaling
  dependencies:
  - aws-orchestrator
  keywords:
  - create ecs fargate service
  - deploy ecs fargate
  - ecs task definition
  - ecs service
  - fargate cpu memory
  - ecs awsvpc networking
  - alb target group ecs
  - ecs auto scaling
  - ecs circuit breaker
  - ecs secrets
  - fargate spot
  - ecs firelens
  when_to_use: Invoke when the user wants to create a new ECS Fargate service, deploy a container workload to Fargate, validate an existing ECS service configuration against best practices, generate deployment
    CLI commands or IaC templates, or troubleshoot a Fargate deployment failure caused by missing prerequisites (task definition, subnets, ALB, execution role, secrets). Do NOT invoke for ECS on EC2 deployments
    (use an EC2-launch-type-specific skill) or for EKS deployments (use an EKS skill).
---

# ECS Fargate Deployer

An AWS CloudOps agent skill that deploys Amazon ECS services on the
Fargate serverless compute engine with correct production defaults. The
skill walks the operator through a 10-step deployment procedure, explains
why each default matters, and emits a READY_TO_DEPLOY checklist verifying
every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the deployment order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Choosing CPU / memory / AZ spread | "Expert heuristic" |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Networking, ALB, auto-scaling | `references/networking-and-scaling-guide.md` |

## Activation keywords

create ECS Fargate service, deploy ECS Fargate, ECS task definition, ECS
service definition, Fargate CPU memory combos, ECS awsvpc mode, ECS
security group, ALB target group ECS, ECS listener rule, ECS
auto-scaling, target tracking, Fargate Spot, ECS circuit breaker,
deployment circuit breaker, ECS task execution role, ECS task role,
FireLens, ECS container health check, ECS secrets, Secrets Manager ECS,
SSM Parameter Store ECS.

## STRICT output contract

When this skill is invoked with an ECS Fargate deployment request
(service name, container image, workload type, or a partial existing
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in "Output format" using the literal all-caps labels
`SERVICE:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do
NOT preface the checklist with prose, headings, or disclaimers — emit
the block as the first lines of the response.

### Required output structure

1. `SERVICE: <service-name>` — the ECS service being deployed.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING` —
   nothing else.
3. `CHECKLIST:` followed by indented lines, each prefixed with a status
   marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws ecs ...` /
   `aws ec2 ...` / `aws logs ...` commands the operator can run.

### 6 FORBIDDEN output patterns (each silently breaks automation)

1. **FORBIDDEN — prose preamble before `SERVICE:`.** Do not write "Here
   is your deployment checklist…" or "Sure, let me help…". The first
   non-empty line MUST be `SERVICE:`.
2. **FORBIDDEN — markdown variants of the labels.** Write `VERDICT:`,
   not `**VERDICT:**`, `### Verdict`, `Verdict =`, or `\`VERDICT\``.
   The labels are case-sensitive all-caps keywords.
3. **FORBIDDEN — swapping verdict tokens.** The verdict is exactly
   `READY_TO_DEPLOY` or `PREREQUISITES_MISSING` — not "ready",
   "missing", "BLOCKED", "OK", or "needs review".
4. **FORBIDDEN — omitting `VERIFICATION_COMMANDS:`.** Even when the
   verdict is `PREREQUISITES_MISSING`, include the commands the operator
   needs to verify the gaps.
5. **FORBIDDEN — extra sections after `VERIFICATION_COMMANDS:`.** The
   checklist block is the entire response. Put deeper explanation in
   `references/` files, not after the block.
6. **FORBIDDEN — status marker drift.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`,
   `[WARN]`, or emoji markers.

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

ECS Fargate deployment has **dependency and ordering constraints** that
make the deployment sequence non-trivial. Applying configurations in
the wrong order causes deployment failures or silent runtime issues:

1. **Task definition FIRST** — a service cannot be created without
   referencing a valid `taskDefinition` ARN. The task definition is the
   blueprint: it defines the containers, CPU/memory, networking mode
   (always `awsvpc` for Fargate), the task execution role, the task
   role, and logging. Creating the service before the task definition
   exists returns `ClientException`.

2. **Execution role + task role (separate!)** — the **task execution
   role** is what the ECS agent uses to pull the ECR image, retrieve
   secrets, and write logs. The **task role** is what the application
   code assumes at runtime to call AWS services (DynamoDB, S3, etc.).
   Conflating the two is the #1 IAM mistake on Fargate: it produces
   either a deployment failure (image pull access denied) or a
   least-privilege violation (the app inherits pull/log permissions).

3. **Cluster + capacity provider** — Fargate and Fargate Spot are
   capacity providers, not launch types. The cluster must have a
   capacity provider strategy (e.g., base=2 on FARGATE, weight=4
   FARGATE / weight=1 FARGATE_SPOT). The launch-type API still exists
   but does not support Spot.

4. **Networking (awsvpc + subnets + security group)** — Fargate
   REQUIRES `networkMode: awsvpc`. The task gets an ENI in the
   specified subnets. Use private subnets across at least 2 AZs for
   production. If the task needs internet access, route through a NAT
   Gateway or VPC endpoints. Without a NAT Gateway, AWS SDK calls fail
   silently with connection timeouts.

5. **Load balancer integration** — the ALB target group MUST use
   `target_type=ip` (not `instance`), because awsvpc tasks register by
   ENI private IP. The target group must exist before the service if
   `loadBalancers` is specified in the service definition.

6. **Container health check + deployment circuit breaker** — without a
   container-level health check, ECS cannot determine if a task is
   healthy and the circuit breaker cannot fire. The circuit breaker
   rolls back failed deployments automatically only when health checks
   are defined and `enableExecution` is true.

7. **Auto-scaling** — target-tracking policies scale the service based
   on CPU, memory, or ALB request count per target. Apply auto-scaling
   AFTER the service is stable — applying it during a deployment
   interferes with the deployment controller.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Cluster** | Must exist with Fargate capacity provider. | `aws ecs describe-clusters --clusters <name>` |
| **Container image** | ECR image URI with valid tag. Pull permissions in execution role. | `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` |
| **VPC subnets** | Private subnets in >= 2 AZs for production. Fargate creates ENIs in these subnets. | `aws ec2 describe-subnets --subnet-ids subnet-aaa subnet-bbb` |
| **Security group** | Allows inbound to container ports + outbound for dependencies. | `aws ec2 describe-security-groups --group-ids sg-xxx` |
| **ALB target group** (if ALB) | `target_type=ip` required. Health check path must match container health check. | `aws elbv2 describe-target-groups --target-group-arns <arn>` |
| **ALB listener** (if ALB) | A listener to attach listener rules to. | `aws elbv2 describe-listeners --listener-arns <arn>` |
| **Execution role** | Trust `ecs-tasks.amazonaws.com`. Must have ECR + Secrets Manager + SSM + logs permissions. | `aws iam get-role --role-name <exec-role>` |
| **Task role** | Permissions the application code needs. Scoped to specific resources. | `aws iam get-role --role-name <task-role>` |
| **Secrets ARNs** (if secrets) | Secrets Manager secret or SSM Parameter Store parameter exists. | `aws secretsmanager describe-secret --secret-id <id>` / `aws ssm get-parameter --name <name>` |
| **CloudWatch log group** | ECS does not auto-create log groups. Pre-create `/ecs/<service>` with retention. | `aws logs describe-log-groups --log-group-name-prefix /ecs/<service>` |
| **KMS key** (if env var encryption or encrypted secrets) | Grant execution role `kms:Decrypt` for the key used to encrypt secrets / env vars. | `aws kms describe-key --key-id <alias>` |
| **IAM permissions** | Caller needs `ecs:RegisterTaskDefinition`, `ecs:CreateService`, `iam:PassRole` on both roles. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Task execution role + task role (separate)

**Two distinct roles. Never combine them.**

**Task execution role** — used by the ECS agent to pull the image,
retrieve secrets, write logs. Attach the managed policy
`AmazonECSTaskExecutionRolePolicy` plus any permissions needed to read
secrets and decrypt KMS keys.

Trust policy (allows ECS to assume the role):

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

Minimum execution role permissions (ECR pull + CloudWatch logs +
Secrets Manager + SSM):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
      "Resource": "arn:aws:ecr:<region>:<account-id>:repository/<repo>"
    },
    {
      "Effect": "Allow",
      "Action": ["ecr:GetAuthorizationToken"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/ecs/<service>:*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue", "ssm:GetParameters"],
      "Resource": ["arn:aws:secretsmanager:<region>:<account-id>:secret:<secret-name>*"]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:<region>:<account-id>:key/<key-id>"
    }
  ]
}
```

**Task role** — assumed by the application code at runtime. Scope to
the specific AWS resources the application needs (e.g., DynamoDB, S3,
SQS). This role has nothing to do with image pulls or log writes.

| Workload | Task role permissions |
|---|---|
| API backend (DynamoDB) | `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query` on the table ARN |
| Queue consumer (SQS) | `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on the queue ARN |
| S3 processor | `s3:GetObject`, `s3:PutObject` on the bucket ARN |
| Web app (RDS) | The task role usually has no AWS perms; the DB credentials come via secrets |
| Cross-account | Resource policy on the target + `sts:AssumeRole` if assuming a role in another account |

**NEVER use `AdministratorAccess` on either role.** A compromised
container with broad permissions can access every resource in the
account.

### Step 2: Task definition (CPU/memory combos)

Fargate enforces **specific CPU/memory combinations**. Any other
combination fails with `ClientException`.

| CPU (vCPU) | Memory options (GB) |
|---|---|
| 0.25 | 0.5, 1, 2 |
| 0.5 | 1, 2, 3, 4 |
| 1 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 |
| 4 | 8, 9, 10, ..., 30 (1 GB increments) |
| 8 | 16, 17, ..., 60 (1 GB increments) |
| 16 | 32, 33, ..., 120 (1 GB increments) |

**CPU value** is in CPU units: 256 = 0.25 vCPU, 512 = 0.5 vCPU, etc.
**Memory value** is in MB: 1024 = 1 GB.

**Workload-based sizing guidance:**

| Workload | CPU | Memory | Rationale |
|---|---|---|---|
| Lightweight API | 0.25 vCPU | 0.5 GB | Low traffic, fast startup |
| Standard API | 0.5 vCPU | 1 GB | Typical Node/Python API |
| Heavy API (ML inference, image processing) | 1-2 vCPU | 4-8 GB | Parallel processing |
| Worker (queue consumer) | 0.5-1 vCPU | 1-2 GB | I/O-bound, modest CPU |
| Data pipeline (Spark, Flink) | 4-8 vCPU | 16-60 GB | JVM heap + GC headroom |
| Java/JVM (Spring Boot) | 1-2 vCPU | 4-8 GB | JVM heap; always >= 2 GB |

**Architecture:** Fargate supports `X86_64` (default) and `ARM64`
(Graviton). ARM64 provides up to 20% price-performance for compatible
images. Set `runtimePlatform: { operatingSystemFamily: LINUX, cpuArchitecture: ARM64 }`.

### Step 3: Container definitions

```json
[
  {
    "name": "app",
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3",
    "cpu": 512,
    "memory": 1024,
    "essential": true,
    "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
    "environment": [
      {"name": "LOG_LEVEL", "value": "info"},
      {"name": "DB_HOST", "value": "prod-db.cluster.example.rds.amazonaws.com"}
    ],
    "secrets": [
      {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:payments/db-XXXXXX"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/payments-api",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 60
    }
  }
]
```

**Key fields:**

- **image** — full ECR URI including tag. NEVER use `:latest` in
  production — it is mutable and breaks rollback. Pin to a version tag
  or SHA digest.
- **portMappings** — `containerPort` only; `hostPort` is ignored on
  Fargate (always equals `containerPort` in awsvpc mode).
- **environment** — plaintext env vars. NEVER put secrets here.
- **secrets** — references to Secrets Manager or SSM Parameter Store;
  injected at container start. The execution role needs
  `secretsmanager:GetSecretValue` or `ssm:GetParameters`.
- **healthCheck** — Docker-level health check. The `startPeriod`
  (1-300s) gives the container grace time before unhealthy counts.
- **essential** — if true (default), container failure stops the task.

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
  --deployment-controller "type=ECS" \
  --scheduling-strategy REPLICA
```

**Key fields:**

- **desiredCount** — number of running task replicas. For HA, set >= 2
  across >= 2 AZs.
- **deploymentCircuitBreaker** — `enable=true, rollback=true` rolls
  back a failed deployment automatically. Without it, a bad task
  definition leaves the service in a degraded state indefinitely.
- **minimumHealthyPercent** — minimum healthy tasks during deployment.
  `100%` means the old tasks stay until new ones are healthy.
- **maximumPercent** — upper bound during deployment. `200%` allows
  rolling double during deployment.
- **schedulingStrategy** — `REPLICA` (standard) or `DAEMON` (one per
  instance; NOT supported on Fargate).
- **assignPublicIp** — `DISABLED` for private subnets (production).
  `ENABLED` only when the task needs direct internet via an IGW (no NAT
  Gateway). Never use `ENABLED` with private subnets.

**Capacity provider strategy (preferred over launch-type):**

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

The `base=2` guarantees 2 tasks on FARGATE; the remaining tasks split
4:1 between FARGATE and FARGATE_SPOT. Spot interruption drains tasks
gracefully via the Spot interruption notice.

### Step 5: Networking (awsvpc mode)

Fargate REQUIRES `networkMode: awsvpc` in the task definition. Each
task gets a primary ENI with a private IP from the subnet.

**Subnet rules:**

1. **Use PRIVATE subnets** in production. Tasks do not need public IPs.
2. **Spread across >= 2 AZs** for HA. Configure
   `availabilityZoneRebalancing=ENABLED` so ECS rebalances tasks after
   AZ failures.
3. **NAT Gateway for internet access** — private subnet route table
   routes `0.0.0.0/0` to a NAT Gateway in a public subnet. Without
   this, the task cannot reach ECR, AWS SDK endpoints, or external
   APIs. This is the #1 Fargate networking issue.
4. **VPC endpoints** — for high-volume AWS service traffic (S3,
   DynamoDB, ECR), use VPC endpoints to avoid NAT Gateway data
   processing charges. Gateway endpoints (S3, DynamoDB) are free;
   Interface endpoints cost per-hour per-AZ.
5. **Security group** — define inbound rules for the container port
   from the ALB's security group. Define outbound for dependencies.

### Step 6: Load balancer integration (ALB)

Fargate services fronted by an ALB use `target_type=ip` target groups.
The ALB routes requests to the task ENI private IP.

```bash
# Create target group (target_type=ip REQUIRED for Fargate)
aws elbv2 create-target-group \
  --name tg-payments-api \
  --protocol HTTP \
  --port 8080 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-path /healthz \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200

# Create listener rule
aws elbv2 create-listener-rule \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/alb/xxx/yyy \
  --priority 10 \
  --conditions Field=path-pattern,Values=["/payments/*"] \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-payments-api/abc
```

**Critical:** the ALB health check path MUST match the container health
check path. A mismatch causes the ALB to mark the task unhealthy even
when ECS considers it healthy.

### Step 7: Secrets (Secrets Manager / SSM Parameter Store)

Secrets are injected as environment variables at container start. They
are NOT visible in the task definition (only the ARN is).

```json
"secrets": [
  {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:payments/db-XXXXXX"},
  {"name": "API_KEY", "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/payments/api-key"}
]
```

**Execution role needs:**
- `secretsmanager:GetSecretValue` on the secret ARN (Secrets Manager)
- `ssm:GetParameters` on the parameter ARN (SSM Parameter Store)
- `kms:Decrypt` on the key used to encrypt the secret (if a
  customer-managed KMS key is used)

For SSM SecureString parameters, both `ssm:GetParameters` AND
`kms:Decrypt` are required.

### Step 8: Logging (FireLens / CloudWatch)

**awslogs driver (default, simplest):**

```json
"logConfiguration": {
  "logDriver": "awslogs",
  "options": {
    "awslogs-group": "/ecs/payments-api",
    "awslogs-region": "us-east-1",
    "awslogs-stream-prefix": "ecs"
  }
}
```

**FireLens (advanced routing):** route different log streams to
different destinations (e.g., audit logs to S3, app logs to
CloudWatch, metrics to Kinesis).

```json
{
  "name": "log_router",
  "image": "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable",
  "essential": false,
  "firelensConfiguration": {
    "type": "fluentbit"
  }
}
```

Pre-create the log group with retention — ECS does NOT auto-create
log groups:

```bash
aws logs create-log-group --log-group-name /ecs/payments-api
aws logs put-retention-policy --log-group-name /ecs/payments-api --retention-in-days 30
```

### Step 9: Auto-scaling (target tracking)

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/payments-prod/payments-api-prod \
  --min-capacity 3 \
  --max-capacity 12

# Target tracking on CPU (60% average)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/payments-prod/payments-api-prod \
  --policy-name payments-api-cpu-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 60.0,
    "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"},
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

**Metric options:**
- `ECSServiceAverageCPUUtilization` — CPU usage (0-100).
- `ECSServiceAverageMemoryUtilization` — memory usage (0-100).
- `ALBRequestCountPerTarget` — requests per target per minute. Requires
  the ALB target group ARN in `ResourceLabel`.

**Cooldown:** scale-out 60s (respond to spikes fast), scale-in 300s
(avoid flapping). Never set scale-in < 300s.

### Step 10: Verification

```bash
aws ecs describe-services --cluster <cluster> --services <service>
aws ecs describe-task-definition --task-definition <family>:<rev>
aws ecs describe-tasks --cluster <cluster> --tasks <task-id>
aws ec2 describe-security-groups --group-ids <sg>
aws elbv2 describe-target-health --target-group-arn <arn>
aws logs describe-log-groups --log-group-name-prefix /ecs/<service>
aws application-autoscaling describe-scaling-policies --service-namespace ecs
```

## Latest ECS Fargate features (2024-2026)

- **Fargate Spot capacity provider (GA):** Spot capacity drains tasks
  on a 2-minute warning via the Spot interruption notice. Use a
  capacity-provider strategy with `base=N` on FARGATE for HA-critical
  tasks plus FARGATE_SPOT for burst capacity.

- **EFA support on Fargate (2024-2025):** Elastic Fabric Adapter for
  high-performance ML / HPC workloads. Available on selected CPU
  configurations; requires the task role to have
  `elastic-inference:Connect`.

- **Container health check improvements (2024-2025):** the
  `START_PERIOD` (grace period before unhealthy counts) is now
  configurable per container (1-300s). Combined with the deployment
  circuit breaker, this eliminates false-negative rollbacks for
  slow-start JVM/Spring workloads.

- **Availability Zone rebalancing (2024-2025):** when enabled, ECS
  automatically rebalances tasks across AZs after an AZ failure or
  capacity loss. Set `availabilityZoneRebalancing=ENABLED` on the
  service.

- **Deployment circuit breaker rollback (GA):** rolls back a failed
  deployment automatically when the circuit breaker fires. Requires
  `enableExecution=true` and a container health check.

- **Graviton (ARM64) on Fargate (2024-2025):** set
  `runtimePlatform.cpuArchitecture=ARM64` for up to 20%
  price-performance improvement. Image must be built for ARM64.

- **Fargate platform version 1.4 (current default):** all tasks use
  the latest platform. `LATEST` no longer auto-upgrades — pin
  `platformVersion` for reproducibility.

- **ECS Exec (session manager):** enable `enableExecuteCommand` on the
  service for `aws ecs execute-command` shell access. Task role needs
  `ssmmessages:CreateControlChannel` etc. Never enable in production
  without audit review.

## Workload matrix

| Workload | CPU / Memory | AZ count | LB | Auto-scale | Spot | Logging |
|---|---|---|---|---|---|---|
| **Public API** | 0.5 vCPU / 1 GB | 3 | ALB | CPU 60% | No | awslogs |
| **Internal API** | 0.5 vCPU / 1 GB | 2 | Internal ALB | CPU 60% | Optional | awslogs |
| **Queue worker (SQS)** | 0.5-1 vCPU / 1-2 GB | 2 | None | Queue depth (custom) | Yes | awslogs |
| **Scheduled batch** | 1-2 vCPU / 2-4 GB | 1 (event) | None | None | Yes | awslogs |
| **ML inference** | 4 vCPU / 16 GB | 2 | ALB | CPU 70% | No | FireLens |
| **Streaming consumer (Kinesis)** | 1 vCPU / 2 GB | 2 | None | None | No | awslogs |
| **Java/Spring Boot** | 1-2 vCPU / 4-8 GB | 3 | ALB | CPU 65% | No | awslogs + startPeriod 60s |

## NEVER (anti-patterns)

- NEVER use `:latest` image tag in production. `:latest` is mutable —
  a new push silently changes what runs. Pin to a version tag
  (`:1.2.3`) or a SHA digest
  (`@sha256:abc...`). This is the #1 rollback-breaker.

- NEVER combine the execution role and task role into one. The
  execution role pulls images and writes logs; the task role is the
  application's identity. Combining produces either pull failures or
  least-privilege violations.

- NEVER use a target group with `target_type=instance` for a Fargate
  service. Fargate tasks register by ENI private IP — only
  `target_type=ip` works. A mismatch silently fails target
  registration.

- NEVER deploy Fargate tasks to a public subnet with
  `assignPublicIp=ENABLED` in production. This exposes the task
  directly to the internet, bypassing the ALB and security group
  controls. Use private subnets + NAT Gateway or VPC endpoints.

- NEVER deploy without the deployment circuit breaker when using a
  rolling deployment. Without `enable=true, rollback=true`, a bad task
  definition leaves the service in a degraded state and ECS keeps
  trying to deploy it indefinitely.

- NEVER rely on the ALB health check alone. Always define a container
  health check so the deployment circuit breaker and task lifecycle
  have a signal independent of the ALB.

- NEVER set `minimumHealthyPercent=0` for a production service. This
  stops all old tasks before new ones start, causing a downtime window
  during every deployment. Use `100%` for HA services.

- NEVER use `awslogs` log driver without pre-creating the log group.
  ECS does NOT auto-create log groups; the first task fails to start
  with `ResourceNotFoundException`.

- NEVER reference Secrets Manager secrets in plaintext environment
  variables. Use the `secrets` array in the container definition so
  they are injected at runtime and not visible in the task definition.

- NEVER set `scaleInCooldown` below 300 seconds. Sub-300s scale-in
  causes flapping — tasks scale in then immediately scale back out.

- NEVER use `DAEMON` scheduling strategy on Fargate. It is only valid
  for ECS on EC2. Fargate services must use `REPLICA`.

- NEVER use the legacy `launch-type` API with FARGATE_SPOT. Spot is a
  capacity provider, not a launch type. Use a capacity-provider
  strategy.

- NEVER omit the `startPeriod` on slow-start containers (Java, .NET,
  large Python). Without it, the health check fires before the app is
  ready and the circuit breaker rolls back a healthy deployment.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal `VERDICT:`
  label silently breaks downstream deployment pipelines and
  assertion-based evals.

## Expert heuristic — choosing CPU, memory, and AZ spread

**The 60/70 rule:** set the CPU target tracking at 60% for
latency-sensitive services, 70% for batch. This leaves headroom for
spikes before auto-scaling kicks in (a scale-out takes ~60-90 seconds
on Fargate — task startup + ALB health check).

**Memory: 2x the working set.** A JVM app with a 2 GB heap needs at
least 4 GB task memory (heap + metaspace + GC overhead + container
agent). Set JVM heap via `-XX:MaxRAMPercentage=75` to leave room for
off-heap.

**AZ spread:** minimum 2 AZs for HA, 3 AZs for user-facing services.
Pair with `desiredCount >= AZ count` so a single AZ failure does not
drop capacity below 1.

**Fargate Spot blend:** for cost optimization, use a capacity-provider
strategy with `base=2` on FARGATE (HA floor) plus FARGATE_SPOT weight
1-3 for burst capacity. NEVER put stateful or single-tenant workloads
on Spot.

**ALB vs. NLB:** ALB for HTTP/HTTPS (path-based routing, OIDC, WAF).
NLB for TCP/TLS (low latency, static IPs, preserved source IP). Fargate
supports both; target type must be `ip` either way.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm the cluster exists with the right capacity provider:**
  ```bash
  aws ecs describe-clusters --clusters <cluster> --include ATTACHMENTS
  ```
  Look for `capacityProviders` including `FARGATE` (and `FARGATE_SPOT`
  if blending).

- **Confirm the ECR image exists:**
  ```bash
  aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>
  ```
  A missing image causes `CannotPullContainerError` at task start.

- **Confirm both roles exist and have the right trust policy:**
  ```bash
  aws iam get-role --role-name <exec-role> --query 'Role.AssumeRolePolicyDocument'
  aws iam get-role --role-name <task-role> --query 'Role.AssumeRolePolicyDocument'
  ```
  Both MUST trust `ecs-tasks.amazonaws.com`.

- **Confirm the target group is `target_type=ip`:**
  ```bash
  aws elbv2 describe-target-groups --target-group-arns <arn> --query 'targetGroups[0].TargetType'
  ```
  Must be `ip`. `instance` silently fails registration.

- **Confirm subnets are private and span >= 2 AZs:**
  ```bash
  aws ec2 describe-subnets --subnet-ids subnet-aaa subnet-bbb \
    --query 'Subnets[].{AZ:AvailabilityZone,Public:MapPublicIpOnLaunch}'
  ```

- **Pre-create the CloudWatch log group with retention:**
  ```bash
  aws logs create-log-group --log-group-name /ecs/<service>
  aws logs put-retention-policy --log-group-name /ecs/<service> --retention-in-days 30
  ```

- **For existing services, capture current config for rollback:**
  ```bash
  aws ecs describe-services --cluster <cluster> --services <service> --output json > /tmp/<service>-backup.json
  ```

## Output format — MANDATORY literal labels

When invoked with a service deployment request, your ENTIRE response
MUST be the checklist block below. The labels are **case-sensitive
all-caps keywords** — write them EXACTLY as shown. Do NOT substitute
`Verdict`, `**VERDICT**`, `### Verdict`, or any markdown variant. Do
NOT write a preamble ("Here is your deployment checklist…"). Start with
`SERVICE:` and stop after the `VERIFICATION_COMMANDS:` block.

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
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing (cluster name,
  subnets, target group ARN, execution role) and the operator must
  provide it before deployment can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (cluster, task definition, subnets, execution role, target
group ARN for an ALB-fronted service), the verdict is
`PREREQUISITES_MISSING` with each gap listed. The checklist shows the
target configuration with `[INPUT NEEDED]` or `[✗]` for unmet
prerequisites.

## Edge-case handling

- **Cross-account ECR pull.** The execution role in account A pulling
  an image from account B's ECR needs `ecr:BatchGetImage` on the
  cross-account repository AND the repository policy in account B must
  grant account A's root. The `ecr:GetAuthorizationToken` call is
  always against the calling account.

- **ECS Exec in production.** `enableExecuteCommand=true` allows
  `aws ecs execute-command` shell access. This bypasses bastion
  auditing. Enable only for break-glass scenarios; require a change
  ticket and CloudTrail alert.

- **ALB health check vs. container health check divergence.** If the
  ALB health check passes but the container health check fails, ECS
  will mark the task unhealthy while the ALB keeps sending traffic.
  Align the path, interval, and timeout of both checks.

- **Slow-start JVM tasks.** Java/Spring Boot apps can take 60-120
  seconds to start. Set `healthCheck.startPeriod=60` (or higher) and
  `unhealthyThresholdCount=3` to avoid spurious rollback.

- **Spot interruption drain.** When a Fargate Spot task receives an
  interruption notice (2-minute warning), ECS sends a
  `SIGTERM` to the container. Set `stopTimeout=30` (max) to allow
  graceful shutdown.

- **Capacity provider vs. launch type.** Once a service uses a
  capacity-provider strategy, you cannot switch back to launch type
  without recreating the service. Pick the strategy at creation time.

- **Service Connect / Cloud Map.** For service-to-service discovery,
  enable Service Connect (built-in) or Cloud Map (external). Both
  require the Lattice / Cloud Map namespace to exist before service
  creation.

- **Task placement constraints.** Fargate ignores most placement
  constraints (these are EC2-only). Use `spread=attribute:ecs.availability-zone`
  to balance across AZs.

## Section taxonomy (CloudOps deployer pattern)

1. **Frontmatter** — name, description, version, when-to-use.
2. **Quick navigation** — what each section covers.
3. **Activation keywords** — discoverability terms.
4. **STRICT output contract** — mandatory output format + FORBIDDEN
   patterns + perfect example.
5. **Reasoning framework** — the *why* behind the deployment order.
6. **Prerequisites** — what must be verified before deployment.
7. **Deployment procedure** — the ordered 10-step deployment sequence.
8. **Latest Fargate features** — 2024-2026 feature changes.
9. **Workload matrix** — per-workload configuration.
10. **NEVER** — anti-patterns with explicit *why* each is wrong.
11. **Expert heuristic** — sizing and AZ-spread rules of thumb.
12. **Pre-flight safety checks** — non-destructive deployment guards.
13. **Output format** — the fixed checklist report shape.
14. **Edge-case handling** — cross-account ECR, Spot drain, ECS Exec.
15. **References** — pointer to deeper references.

## Domain

AWS CloudOps / ECS Fargate Container Compute Provisioning.

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

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 10 deployment steps, including execution
  role + task role creation, task definition registration, service
  creation, ALB target group + listener rule, auto-scaling, and
  Terraform `aws_ecs_service` / `aws_ecs_task_definition` resource
  equivalents.

- `references/networking-and-scaling-guide.md` — deep reference on
  awsvpc networking for Fargate (ENI lifecycle, NAT Gateway vs VPC
  endpoints), ALB integration (target type ip, health check alignment,
  listener rules), target-tracking auto-scaling (CPU, memory, ALB
  request count per target), and Fargate Spot capacity provider
  strategy internals.
