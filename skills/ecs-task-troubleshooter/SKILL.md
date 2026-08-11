---
name: ecs-task-troubleshooter
description: >-
  Diagnoses AWS ECS task failures via a stoppedReason-first decision tree
  covering ResourceInitializationError (ENI trunking, subnet IP
  exhaustion), CannotPullContainerError (ECR auth, throttle, size limit,
  private-subnet ECR endpoint), EC2InstanceStateError, capacity provider
  placement failures, task-role vs execution-role confusion, service
  event messages (task failed to start, unable to place), CPU/memory
  oversubscription, container health check failures, deregistered
  container instances, Fargate platform version issues, and deployment
  circuit breaker rollbacks. Walks describe-tasks stoppedReason +
  containers[].reason + describe-services events to a verified root
  cause with evidence-backed probes. Emits ROOT_CAUSE_IDENTIFIED or
  INSUFFICIENT_DATA. Use when an ECS task is stuck in PROVISIONING,
  transitions to STOPPED, fails placement, cannot pull an image, or
  the deployment circuit breaker fires.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works on supplied describe-tasks /
  describe-services JSON. Live-account diagnosis uses aws ecs
  describe-tasks, describe-services, describe-task-definition,
  describe-container-instances, describe-capacity-providers, aws logs
  get-log-events / filter-log-events, aws elbv2 describe-target-health,
  aws ecr get-repository-policy / describe-images, aws ec2
  describe-subnets / describe-network-interfaces (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - ECS
  - Fargate
  - EC2 launch type
  - task stopped
  - stoppedReason
  - ResourceInitializationError
  - CannotPullContainerError
  - EC2InstanceStateError
  - ENI trunking
  - awsvpc
  - task role
  - execution role
  - capacity provider
  - placement failure
  - service event
  - unable to place
  - CPU oversubscription
  - memory oversubscription
  - container health check
  - deregistered container instance
  - task definition validation
  - Fargate platform version
  - ECR image pull
  - ECR auth
  - ECR throttle
  - ECR size limit
  - deployment circuit breaker
tags:
  - ecs
  - compute
  - troubleshoot
  - task-failure
  - fargate
  - ec2
  - eni
  - ecr
  - circuit-breaker
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
  when_to_use: >-
    Diagnosing why an ECS task stays in PROVISIONING, transitions to
    STOPPED, fails placement with "No ContainerInstances were found" or
    "unable to place a task", cannot pull a container image
    (CannotPullContainerError), fails container health checks, hits the
    deployment circuit breaker, or exits with a non-zero code; interpreting
    describe-tasks stoppedReason / containers[].reason / lastStatus, or
    triaging an ECS service event message.
  when_not_to_use: >-
    Application-code debugging inside a running container (use CloudWatch
    Logs and the application's own debugger); EKS pod troubleshooting
    (use eks-pod-troubleshooter); Fargate capacity reservation sizing
    (use fargate-cost-optimizer); ECS task-definition IAM posture audits
    (use ecs-task-definition-auditor); steady-state service-auto-scaling
    tuning (use autoscaling-policy-deployer).
  activation_triggers:
    - "ECS task stopped"
    - "ECS task PROVISIONING stuck"
    - "ECS task PENDING forever"
    - "ResourceInitializationError"
    - "CannotPullContainerError"
    - "EC2InstanceStateError"
    - "unable to place a task"
    - "No ContainerInstances were found"
    - "Essential container in task exited"
    - "ECS health check failing"
    - "ECS task crash loop"
    - "ECS task OutOfMemory"
    - "deployment circuit breaker"
    - "service deregistered container instances"
    - "Fargate platform version"
  invocation_schema: >-
    Input: either (a) a symptom description (the failing service/cluster,
    the observed state, any error strings from the console), OR (b) a
    live-account scenario where the agent runs aws ecs describe-tasks /
    describe-services / describe-task-definition to gather evidence.
    Output: a deterministic TARGET / VERDICT / ROOT_CAUSE / REASON /
    EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED,
    INSUFFICIENT_DATA} and ROOT_CAUSE names the specific failure category
    (RESOURCE_INIT_ENI / RESOURCE_INIT_SUBNET_IP / IMAGE_PULL_AUTH /
    IMAGE_PULL_ENDPOINT / IMAGE_PULL_SIZE / CAPACITY_PLACEMENT /
    CAPACITY_DEREGISTERED / CONFIG_TASK_ROLE / CONFIG_EXECUTION_ROLE /
    CONFIG_DEFINITION_INVALID / HEALTH_CHECK / OOM / ExitCode /
    CIRCUIT_BREAKER / PLATFORM_VERSION / UNKNOWN).
---

# ECS Task Troubleshooter

## Quick navigation

| Symptom / signal | Jump | Likely ROOT_CAUSE |
|---|---|---|
| `stoppedReason: ResourceInitializationError: failed to ... ENI` | Step 1 | `RESOURCE_INIT_ENI` (trunk / interface limit) |
| `stoppedReason: ResourceInitializationError: unable to pull secrets or ...` (awsvpc, private subnet) | Step 1 | `RESOURCE_INIT_SUBNET_IP` (no free IP in subnet) |
| `stoppedReason: CannotPullContainerError: inspect image ... 401/403` | Step 2 | `IMAGE_PULL_AUTH` (execution role lacks `ecr:*` or ECR policy denies) |
| `stoppedReason: CannotPullContainerError: RequestError ... timeout` (private subnet, Fargate) | Step 2 | `IMAGE_PULL_ENDPOINT` (no ECR + S3 VPC endpoints) |
| `stoppedReason: CannotPullContainerError: ... layer size exceeds` | Step 2 | `IMAGE_PULL_SIZE` (> 10 GB uncompressed layer) |
| `stoppedReason: EC2InstanceStateError: Container instance ... deregistered` | Step 3 | `CAPACITY_DEREGISTERED` |
| service event `was unable to place a task ... No ContainerInstances` | Step 3 | `CAPACITY_PLACEMENT` (no matching attributes / capacity) |
| task exits non-zero immediately, `stoppedReason: Essential container in task exited` | Step 4 | `ExitCode` → app error / OOM / `CONFIG_TASK_ROLE` |
| `CannotPullContainerError` only on first deploy of cross-account image | Step 2 + 5 | `IMAGE_PULL_AUTH` + `CONFIG_EXECUTION_ROLE` |
| target group `target_health: unhealthy` + service event `task failed to start` | Step 6 | `HEALTH_CHECK` (path/port/interval mismatch) |
| service event `service ... deployment failed: Circuit Breaker` (TaskFailed) | Step 7 | `CIRCUIT_BREAKER` → fold to underlying cause |
| `runtime platform: LATEST` shifted after a Fargate patch window | Step 8 | `PLATFORM_VERSION` (behavioural regression) |
| describe-task-definition returns `ClientException: ...` | Step 9 | `CONFIG_DEFINITION_INVALID` |
| Symptom does not match any row, evidence incomplete | Step 10 | `INSUFFICIENT_DATA` |

## STRICT output contract

Every invocation MUST emit exactly one diagnostic block as the final
answer. The block is machine-parsable; any drift breaks the eval harness
and the downstream orchestrator.

```text
TARGET: <cluster / service / task ARN or unknown>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <CATEGORY_NAME>
REASON: <1-3 sentences naming the failing config element + the probe
  that proves it>
EVIDENCE:
  - <observed signal — stoppedReason / containers[].reason / exitCode
    / service event / metric>
  - <failing probe — CLI command and the specific output line that
    confirms the cause>
  - <passing probes — categories ruled out with one-line justification>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <resource>. Proceed? (yes/no)"
```

Rules:

- `VERDICT: ROOT_CAUSE_IDENTIFIED` requires at least one FAILING probe
  that matches the symptom — never a process-of-elimination answer.
- `VERDICT: INSUFFICIENT_DATA` MUST list the missing inputs and the next
  probe to run; it is never a dead-end.
- `ROOT_CAUSE` is a single UPPER_SNAKE_CASE category name from the set
  above — free-text root causes are forbidden.
- `EVIDENCE` lists BOTH the failing probe AND the categories ruled out.
- One block per target; multi-target incidents separate blocks with `---`.

## NEVER

- **NEVER** declare `ROOT_CAUSE_IDENTIFIED` without a failing probe that
  matches the symptom. The `stoppedReason` string alone ("Essential
  container in task exited") is a symptom, not a root cause; cross-
  reference `containers[].reason`, `exitCode`, and CloudWatch Logs
  before naming the category.
- **NEVER** conflate the task role with the execution role. The **task
  role** is assumed by the container at runtime (permissions for the
  application to call AWS APIs). The **execution role** is assumed by
  the ECS agent / Fargate to pull the image, fetch secrets, and write
  CloudWatch Logs. An `AccessDenied` from the application code is the
  task role; a `CannotPullContainerError: 401` is the execution role.
  Swapping the two is the single most common ECS misdiagnosis.
- **NEVER** recommend adding a NAT Gateway to fix `CannotPullContainerError`
  on Fargate in a private subnet without first checking for the ECR
  interface endpoint (`ecr.api` + `ecr.dkr`) AND the S3 gateway
  endpoint. Fargate cannot use a NAT for ECR auth; the S3 gateway is
  required because ECR layers are stored in S3.
- **NEVER** assume an `awsvpc` task has an ENI just because the task
  reached RUNNING. The ENI is attached during PROVISIONING; if the
  subnet has zero free IPs, the task fails with
  `ResourceInitializationError` BEFORE the container starts.
- **NEVER** conclude "the container image is broken" without first
  pulling it locally on the same architecture. A `CMD` typo or an
  `ENTRYPOINT` override in the task definition produces an exit-code-127
  that mimics a broken image.
- **NEVER** propose changing the capacity provider strategy or
  launch type without confirming the placement failure mode. "Unable
  to place" can be capacity (no free CPU units), attributes (no
  instance with `ecs.capability.execution-role-awslogs`), or
  availability-zone constraints. The wrong fix masks the symptom.
- **NEVER** delete and recreate a service to clear a circuit-breaker
  rollback. The circuit breaker fires BECAUSE the new task definition
  is failing; recreate-without-fix triggers the same failure. Read
  Step 7 first and fold to the underlying category.

## Expert heuristic

> **`stoppedReason` is the primary diagnostic surface.** Every stopped
> ECS task carries a `stoppedReason` string and, in nearly every case,
> a per-container `containers[].reason` with the exit code. Read these
> BEFORE opening CloudWatch Logs. The string maps deterministically to
> a root-cause category:
>
> - `ResourceInitializationError` → ENI / subnet / ECR endpoint layer
> - `CannotPullContainerError` → ECR auth / endpoint / size layer
> - `EC2InstanceStateError` → deregistered container instance
> - `Essential container in task exited` → application / OOM / task role
>   (fold via `exitCode`)
> - `GoOffline` / `TaskFailed` from circuit breaker → fold to underlying
>
> **For `awsvpc` mode, ENI attachment requires a free IP in every
> subnet the task is placed in.** A `/28` subnet has 11 usable IPs; a
> burst of 12 tasks exhausts the pool. ENI trunking on EC2 launch type
> raises the per-instance ENI cap but is NOT automatic — the trunk must
> be requested and the instance must support it (`ecs.awsvpc-trunking`
> instance attribute).
>
> **For private subnets, ECR pull requires the ECR interface endpoint
> (`ecr.api`, `ecr.dkr`) AND the S3 gateway endpoint.** The execution
> role must grant `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`,
> `ecr:GetAuthorizationToken`. Without the endpoints, Fargate cannot
> authenticate to ECR; without the role, the pull returns 401/403.

## Configuration dependency graph

```
                       task definition
                             │
            ┌────────────────┼───────────────────┐
            ▼                ▼                   ▼
       taskRole        executionRole        containerDefinitions
       (runtime        (ECS agent /         (image, cpu, memory,
        AWS creds)     Fargate pulls          healthCheck, ports,
                       image + writes         secrets, entryPoint)
                       logs)
                             │
                             ▼
              ┌──────────────┴───────────────┐
              ▼                              ▼
        ECR repo policy              CloudWatch Logs
        (cross-account grants        (execution role needs
        for the function account)    logs:CreateLogStream +
                                     logs:PutLogEvents on the
                                     log group)
                             │
                             ▼
                       service
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
        launch type    capacity        network config
        (Fargate /     provider        (awsvpc → ENI in
         EC2)          strategy        subnet → needs free IP
                        placement       + SG; bridge/none →
                        constraints     host ENI)
                             │
                             ▼
                       subnet / VPC
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
        free IP count   route table      VPC endpoints
        (per /28 etc)   (NAT / IGW /    (ecr.api, ecr.dkr
                         TGW)             interface + s3
                                          gateway required for
                                          private subnets)
```

Read top-down: a task failure is a broken edge or broken node in this
graph. The diagnostic tree walks the graph from the symptom down.

## Mindset

An ECS task failure is a state-machine problem, not a container-debugging
problem. The ECS control plane records exactly what went wrong in
`stoppedReason`, `containers[].reason`, `exitCode`, and the service
event log. Senior container engineers start with `describe-tasks` and
`describe-services`, then drill into CloudWatch Logs only after the
category is confirmed. Operators who start with the application logs
frequently miss a `ResourceInitializationError` that fired BEFORE the
container ever started.

## Process — stoppedReason-first diagnostic tree

### Step 0: Pre-flight — gather task and service state

```bash
# 1. Most recent stopped task for the service (highest-quality signal)
aws ecs list-tasks --cluster <cluster> --service-name <service> \
  --desired-status STOPPED --output json | \
  jq -r '.taskArns[0]'

# 2. Full describe-tasks for that task
aws ecs describe-tasks --cluster <cluster> \
  --tasks <task-arn> --output json | \
  jq '.tasks[] | {stopCode, stoppedReason, stoppedAt, lastStatus,
    launchType, platformVersion, platformFamily,
    attachments: [.attachments[] | {type, status, details}],
    containers: [.containers[] | {name, exitCode, reason, healthStatus,
      lastStatus}]}'

# 3. Service event log (last 30 events — placement, circuit breaker)
aws ecs describe-services --cluster <cluster> \
  --services <service> --output json | \
  jq '.services[0].events[:30] | [.[] | {createdAt, message}]'

# 4. Task definition (CPU, memory, roles, container defs, health checks)
aws ecs describe-task-definition --task-definition <family:rev> \
  --output json | jq '.taskDefinition'

# 5. (EC2 launch type only) container instance state
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <ci-arn> --output json | \
  jq '.containerInstances[] | {status, runningTasksCount,
    remainingResources, registeredResources, attributes:
    [.attributes[] | select(.name | startswith("ecs."))]}' \
    2>/dev/null || echo "Fargate launch type — skip"
```

Short-circuit cases that mimic task failure:

| Signal | Effect on diagnosis |
|---|---|
| `desiredCount: 0` (service scaled to zero) | No failure — the scheduler is doing what it was told. Do NOT diagnose as a stopped-task incident. |
| `pendingTasksCount` rising, no STOPPED tasks | Tasks are PROVISIONING but not failing yet. Wait 60–90s; if they transition to STOPPED, return here. |
| `status: INACTIVE` on the service | Service was deleted; no live target. Emit `INSUFFICIENT_DATA` listing the deleted service. |
| AWS Health event `AWS_ECS_SERVICE` open in the region | Fold to AWS-side; surface the event ARN and recommend opening a Support case. Do NOT continue diagnosing customer-side causes. |

If the input lacks the cluster, service, or task ARN, emit
`INSUFFICIENT_DATA` listing the missing fields and the exact probe to run.

### Step 1: ResourceInitializationError — ENI and subnet IP

`stoppedReason` contains `ResourceInitializationError`. Two sub-cases.

#### 1a: ENI attachment failure (trunking / interface limit)

Symptom string contains `failed to initialize ENI` or
`ResourceInitializationError: unable to pull secrets or register log
driver`. On EC2 launch type with `awsvpc`, the instance has a per-
instance ENI cap. Without trunking, a `c5.large` (2 ENIs) can run at
most 1 `awsvpc` task — the second ENI is the host's primary interface.

```bash
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <ci-arn> --output json | \
  jq '.containerInstances[] | {
    remaining: [.registeredResources[] | select(.name=="ENI")],
    trunking: .attributes[]? | select(.name=="ecs.awsvpc-trunking")
  }'
```

If `ecs.awsvpc-trunking` is absent or `"value": "disabled"`, and the
instance has hit its ENI cap, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: RESOURCE_INIT_ENI`. Fix: enable trunking
(`put-attribute-content --attribute ecs.awsvpc-truncation ...` is NOT
a thing — request a trunk ENI via `create-carrier-gateway` /
`modify-network-interface-attribute` per the AWS trunking docs) on a
supported instance type, OR move the workload to Fargate.

#### 1b: Subnet IP exhaustion (awsvpc private subnet)

For `awsvpc` mode, each task consumes one primary private IP from its
subnet. A `/28` subnet has 11 usable IPs; a burst of tasks can exhaust
the pool. Fargate additionally reserves 1 IP per task for the ENI.

```bash
aws ec2 describe-subnets --subnet-ids <subnet-1> <subnet-2> \
  --output json | jq '.Subnets[] | {SubnetId, CidrBlock,
    AvailableIpAddressCount}'
```

`AvailableIpAddressCount < desiredCount + 2` (headroom for the ENI
itself) is the failure. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: RESOURCE_INIT_SUBNET_IP`. Fix: widen the subnet CIDR
(`modify-subnet-attribute` cannot resize; create a new wider subnet
and update the service's `networkConfiguration`), OR add more subnets
to the VPC and update the service's `networkConfiguration.awsvpcConfiguration.subnets`.

### Step 2: CannotPullContainerError — ECR auth / endpoint / size

`stoppedReason` contains `CannotPullContainerError`. Three sub-cases.

#### 2a: Authentication failure (401 / 403)

The image exists but the execution role or ECR repo policy denies the
pull. Symptom string contains `401`, `403`, `no basic auth credentials`,
or `RequestError ... send request`.

```bash
# Execution role must include these actions
aws iam simulate-principal-policy \
  --policy-source-arn <execution-role-arn> \
  --action-names ecr:BatchGetImage ecr:GetDownloadUrlForLayer \
                 ecr:GetAuthorizationToken \
  --output json --profile <p>
```

If `implicitDeny`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: IMAGE_PULL_AUTH` and the offending side is the execution
role. Attach `AmazonECSTaskExecutionRolePolicy` or grant the three
actions inline.

For cross-account images, also check the ECR repo policy:

```bash
aws ecr get-repository-policy --repository-name <repo> \
  --registry-id <source-account> --output json --profile <p>
```

The policy must allow `ecr:BatchGetImage` + `ecr:GetDownloadUrlForLayer`
for the task's execution role ARN (or its account). Same-account pulls
are allowed by the service principal automatically.

#### 2b: Network endpoint failure (private subnet, Fargate)

The execution role has the right permissions, but the task is in a
private subnet without an ECR VPC endpoint. The pull hangs and
eventually times out. Symptom string contains `Client.Timeout`,
`RequestError: ... dial tcp ... i/o timeout`, or
`net/http: request canceled`.

```bash
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc-id> \
  --output json | \
  jq '.VpcEndpoints[] | {ServiceName, VpcEndpointType, State}'
```

Required endpoints for ECR from a private subnet:

| Endpoint | Type | Required? |
|---|---|---|
| `com.amazonaws.<region>.ecr.api` | Interface | YES (auth + manifest) |
| `com.amazonaws.<region>.ecr.dkr` | Interface | YES (Docker registry) |
| `com.amazonaws.<region>.s3` | Gateway | YES (image layers stored in S3) |

If any of the three is missing, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: IMAGE_PULL_ENDPOINT`. Fix: create the missing endpoint(s).
A NAT Gateway is NOT sufficient for Fargate ECR auth.

#### 2c: Image size exceeds limit

Symptom string contains `layer size exceeds` or the image is above the
10 GB uncompressed cap. Confirm:

```bash
aws ecr describe-images --repository-name <repo> \
  --image-ids imageTag=<tag> --output json | \
  jq '.imageDetails[].imageSizeInBytes'
```

ECS / Fargate caps at 10 GB uncompressed. Above the cap, the pull
fails deterministically. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: IMAGE_PULL_SIZE`. Fix: rebuild the image (multi-stage
build, slim base image, exclude dev dependencies).

### Step 3: Placement and capacity failures

Service event contains `was unable to place a task`,
`No ContainerInstances were found`, or `unfulfilled capacity`.

#### 3a: No matching container instance (EC2 launch type)

```bash
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <ci-arns> --output json | \
  jq '.containerInstances[] | {status, agentConnected,
    remaining: [.remainingResources[] | {name, integerValue}],
    registered: [.registeredResources[] | {name, integerValue}]}'
```

Common causes:

| Pattern | ROOT_CAUSE |
|---|---|
| `status: INACTIVE` or agent disconnected | `CAPACITY_DEREGISTERED` — instance was drained or the agent lost connection |
| `remaining CPU < task CPU` or `remaining MEMORY < task MEMORY` | `CAPACITY_PLACEMENT` — capacity oversubscribed; add instances or reduce task size |
| Instance lacks `ecs.capability.execution-role-awslogs` attribute | `CAPACITY_PLACEMENT` — task requires `awslogs` log driver but instance cannot provide it |
| All instances in wrong AZ vs service's `placementStrategy` | `CAPACITY_PLACEMENT` — AZ constraint cannot be satisfied |

#### 3b: Capacity provider failure (Fargate or EC2)

```bash
aws ecs describe-capacity-providers --capacity-providers <name> \
  --output json | jq('.capacityProviders[] | {status,
    autoScalingGroupProvider: .autoScalingGroupProvider?,
    updateStatus}')
```

If `status: INACTIVE` or the ASG has zero instances, the provider
cannot service the task. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: CAPACITY_PLACEMENT`. Fix: activate the provider, scale
the ASG, or update the service's `capacityProviderStrategy`.

### Step 4: Essential container exit — exit code analysis

`stoppedReason: Essential container in task exited` with a non-zero
`exitCode`. The exit code routes to the next probe.

| `exitCode` | Likely cause | Next probe |
|---|---|---|
| `0` | Container exited cleanly but was marked essential | Application logic / liveness probe mismatch |
| `1` | Generic application error | CloudWatch Logs for the container |
| `137` | SIGKILL (OOM killer or ECS resource cap) | Step 4a — CPU/memory oversubscription |
| `139` | SIGSEGV | Application code (out of scope) |
| `143` | SIGTERM (graceful stop) | Check `stopTimeout` and whether the service was scaled in |
| `127` | Command not found | `entryPoint` / `command` mismatch in task definition |
| `255` | Often an auth or framework init failure | CloudWatch Logs |

#### 4a: CPU / memory oversubscription (exit 137)

```bash
# Container-level memory limit vs actual usage
aws ecs describe-tasks --cluster <cluster> --tasks <task-arn> \
  --output json | jq('.tasks[].containers[] | {name, exitCode,
    reason, memory, memoryReservation}')

# Service-wide MemoryUtilization
aws cloudwatch get-metric-statistics --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

If the task's `memory` (hard limit) is below the container's resident
set at peak, the OOM killer fires with exit 137. **ROOT_CAUSE_IDENTIFIED**
with `ROOT_CAUSE: OOM`. Fix: raise `memory` in the container definition.

For Fargate, the task-level `cpu` and `memory` must match a valid
combination. A task at `cpu: 256` (0.25 vCPU) and `memory: 0.5 GB` is
valid, but the same task with a JVM heap set to 1 GB OOMs deterministically.

#### 4b: Task role AccessDenied (application AWS calls)

If CloudWatch Logs show `AccessDenied` / `is not authorized`, the
task role (NOT the execution role) lacks the IAM permission. Fold to
Step 5.

### Step 5: Task role vs execution role confusion

The two roles are easy to conflate. The decision tree:

| Symptom | Which role is broken | Probe |
|---|---|---|
| `CannotPullContainerError: 401/403` | Execution role | `simulate-principal-policy` on the execution role for `ecr:*` |
| `AccessDenied` from application code calling S3/DynamoDB/Secrets | Task role | `simulate-principal-policy` on the task role for the denied action |
| `AccessDenied` when fetching a secret referenced in `secrets` | Execution role | `simulate-principal-policy` on the execution role for `secretsmanager:GetSecretValue` |
| No logs in CloudWatch Logs but task ran | Execution role | Execution role needs `logs:CreateLogStream` + `logs:PutLogEvents` on the log group ARN |

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CONFIG_TASK_ROLE` or
`CONFIG_EXECUTION_ROLE`. Fix: add the missing permission via
`iam put-role-policy` (inline) or attach a managed policy.

### Step 6: Container health check failures

The task reaches RUNNING but the ALB / target group health check or
the ECS container health check fails. Service event:
`task failed to start` or
`container <name> failed container health checks`.

#### 6a: ECS container health check (in task definition)

```bash
aws ecs describe-task-definition --task-definition <family:rev> \
  --output json | jq('.taskDefinition.containerDefinitions[] |
    {name, healthCheck}')
```

The `healthCheck.command` runs inside the container; the exit code
must be 0 for HEALTHY. Common failure: `CMD-SHELL` curl against a
path that returns non-200, or the `interval`/`timeout` is too short
for cold-start workloads.

#### 6b: ALB target group health check

```bash
aws elbv2 describe-target-health --target-group-arn <tg-arn> \
  --targets <target-list> --output json | \
  jq('.TargetHealthDescriptions[] | {Target: .Target.Id,
    Health: .TargetHealth)')
```

Common patterns:

| Pattern | ROOT_CAUSE |
|---|---|
| `State: unhealthy`, `Description: Request timed out` | Security group on the task does not allow the ALB's SG on the container port |
| `State: unhealthy`, `Description: HTTP 404` | `healthCheckPath` in the target group does not match the application's routes |
| `State: unhealthy`, `Description: HTTP 502` | Application crashed mid-health-check (fold to Step 4) |
| Target not registered at all | `loadBalancers.containerName` or `containerPort` in the service definition does not match any container in the task definition |

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: HEALTH_CHECK`. Fix: align
the path/port/SG to what the application actually serves.

### Step 7: Deployment circuit breaker

Service event contains
`deployment failed: Task failed to start` or
`service <name> deployment failed: Circuit Breaker`
(`deploymentCircuitBreaker: { enable: true, rollback: true }`).

The circuit breaker is NOT a root cause — it is a rollup signal that
the replacement tasks are failing. The actual cause is in the
underlying stopped task's `stoppedReason`. ALWAYS fold to the
underlying category via Steps 1–6 before declaring
`ROOT_CAUSE: CIRCUIT_BREAKER`. If the underlying category is
identified, emit that category and note the circuit breaker in
`EVIDENCE`. Reserve `ROOT_CAUSE: CIRCUIT_BREAKER` for the rare case
where the underlying `stoppedReason` is empty or self-contradictory.

### Step 8: Fargate platform version regressions

Service recently changed `platformVersion` from a pinned version to
`LATEST`, or AWS patched `LATEST`. Symptom: tasks that ran fine for
weeks start failing with no config change.

```bash
aws ecs describe-services --cluster <cluster> \
  --services <service> --output json | \
  jq('.services[0] | {platformVersion, platformFamily,
    deployments: [.deployments[] | {status, rolloutState,
      platformVersion, runningCount})]')
```

Confirm by pinning to the previous platform version and re-deploying.
If the failure disappears, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: PLATFORM_VERSION`. Fix: pin to the previous working
version (`platformVersion: 1.4.0` for Fargate); do NOT use `LATEST`
for production.

### Step 9: Task definition validation errors

`register-task-definition` or `run-task` returns
`ClientException` / `InvalidParameterException`. Common patterns:

| Error string | ROOT_CAUSE |
|---|---|
| `Container.instanceType is not compatible with cpu/memory` | Invalid Fargate CPU/memory combo |
| `Invalid parameter at 'containerDefinitions[0].portMappings'` | Port conflict between containers |
| `requiresCompatibilities lists FARGATE but networkMode is not awsvpc` | Network mode mismatch |
| `Task role or execution role ARN is malformed or does not exist` | Role ARN invalid |

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CONFIG_DEFINITION_INVALID`.
Fix: correct the offending field in the task definition.

### Step 10: INSUFFICIENT_DATA — when to bail

Emit `INSUFFICIENT_DATA` when:

- The input lacks the cluster / service / task ARN and the symptom is
  too generic to identify a category.
- A probe requires operator input (e.g., the application's expected
  health check path is unknown).
- The symptom matches no row in the quick navigation table and the
  describe-tasks output is empty or stale.
- An AWS Health event is OPEN in the region and may be the cause; the
  agent cannot confirm without operator-supplied AWS Health access.

ALWAYS list the missing inputs and the exact next probe to run.

## Output format

See the STRICT output contract above. Two worked examples follow.

### Worked example — CannotPullContainerError, ECR endpoint missing

```text
TARGET: cluster:prod-app / service:payments-api / task:abc123
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: IMAGE_PULL_ENDPOINT
REASON: Task stoppedReason is `CannotPullContainerError: inspect image
  ... i/o timeout`. The task is in a private subnet (subnet-0abc,
  10.0.20.0/24) without an ECR interface endpoint. The VPC has the s3
  gateway endpoint but is missing `ecr.api` and `ecr.dkr`; Fargate
  cannot use a NAT for ECR auth.
EVIDENCE:
  - Probe: aws ecs describe-tasks returns stopCode=EssentialContainerExited,
    stoppedReason contains `CannotPullContainerError: ... i/o timeout`.
  - Probe: aws ec2 describe-vpc-endpoints for vpc-0abc returns only the
    s3 gateway endpoint; ecr.api and ecr.dkr are absent.
  - Probe: aws iam simulate-principal-policy on the execution role
    returns allowed for ecr:BatchGetImage (auth is not the issue).
  - Passing: subnet-0abc has AvailableIpAddressCount: 22; image is
    480 MB compressed (size is not the issue).
REMEDIATION:
  1. Create the two ECR interface endpoints in the VPC:
     aws ec2 create-vpc-endpoint --vpc-id vpc-0abc \
       --service-name com.amazonaws.us-east-1.ecr.api \
       --vpc-endpoint-type Interface --subnet-ids subnet-0abc \
       --security-group-ids <sg>
     aws ec2 create-vpc-endpoint --vpc-id vpc-0abc \
       --service-name com.amazonaws.us-east-1.ecr.dkr \
       --vpc-endpoint-type Interface --subnet-ids subnet-0abc \
       --security-group-ids <sg>
  2. Verify by running a one-off task in the same subnet and watching
     it transition to RUNNING without a CannotPullContainerError.
CONFIRM: Before creating the endpoints, emit and await:
  "CONFIRM: About to create ecr.api + ecr.dkr interface endpoints in
   vpc-0abc. Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown
VERDICT: INSUFFICIENT_DATA
ROOT_CAUSE: UNKNOWN
REASON: Input is "ECS task failing in prod" with no cluster, service,
  task ARN, or symptom string; the category cannot be determined.
EVIDENCE:
  - Missing: cluster name or ARN
  - Missing: service name or task ARN
  - Missing: observed stoppedReason or service event string
REMEDIATION:
  1. Run aws ecs list-clusters and share the cluster ARN.
  2. Run aws ecs list-tasks --cluster <c> --desired-status STOPPED and
     share the most recent task ARN.
  3. Run aws ecs describe-tasks --cluster <c> --tasks <arn> and share
     the stoppedReason field.
```

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-service`, `register-task-definition`, `create-vpc-endpoint`,
  `put-role-policy`), emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is read-only.
- **Updating a service** with a new task definition is the production
  cutover; prefer `maximumPercent: 100, minimumHealthyPercent: 100`
  for rolling deploys.
- **Circuit breaker rollback** is automatic when
  `deploymentCircuitBreaker.rollback: true`. Do not disable it to
  "force through" a failing deployment.
- **Capacity provider swaps** can strand in-flight tasks — confirm
  during a maintenance window.
- **Bulk remediation batch limit.** When the same root cause affects
  multiple services, batch into groups of at most 5 and verify between
  batches.

## Remediation guidance

| ROOT_CAUSE | Specific fix |
|---|---|
| `RESOURCE_INIT_ENI` | Enable ENI trunking on supported EC2 instance types, OR migrate to Fargate. |
| `RESOURCE_INIT_SUBNET_IP` | Create new wider subnets and update the service `networkConfiguration.awsvpcConfiguration.subnets`. Do NOT resize in-use subnets. |
| `IMAGE_PULL_AUTH` | Attach `AmazonECSTaskExecutionRolePolicy` to the execution role; for cross-account, add a statement to the ECR repo policy granting the task's execution role ARN. |
| `IMAGE_PULL_ENDPOINT` | Create the three required VPC endpoints (ecr.api, ecr.dkr interface + s3 gateway). Interface endpoints need a SG that allows inbound 443 from the task's SG. |
| `IMAGE_PULL_SIZE` | Rebuild the image below 10 GB uncompressed (target < 1 GB for fast cold starts). |
| `CAPACITY_PLACEMENT` | Add container instances or scale the capacity provider's ASG; confirm instance attributes match the task's `requiresCompatibilities`. |
| `CAPACITY_DEREGISTERED` | Reconnect the ECS agent (`systemctl restart ecs`) or replace the instance via the ASG; check `/var/log/ecs/ecs-agent.log`. |
| `CONFIG_TASK_ROLE` / `CONFIG_EXECUTION_ROLE` | Add the missing IAM permission via `iam put-role-policy` or attach a managed policy; verify with `simulate-principal-policy`. |
| `HEALTH_CHECK` | Align `healthCheckPath` in the target group to the application's route; ensure the task's SG allows the ALB's SG on the container port. |
| `OOM` | Raise `memory` (hard limit) in the container definition, or fix the memory leak in the application code. |
| `PLATFORM_VERSION` | Pin `platformVersion` to the previous working version; avoid `LATEST` in production. |
| `CIRCUIT_BREAKER` | Fold to the underlying category via Steps 1–6; the circuit breaker is never the actual root cause. |
| `CONFIG_DEFINITION_INVALID` | Correct the offending field in the task definition; re-register via `aws ecs register-task-definition`. |

## Domain

AWS CloudOps / ECS & Fargate Compute, Task Lifecycle Diagnostics, ENI
& VPC Networking for Containers, ECR Image Distribution, ECS Deployment
Automation.

## AWS documentation

- ECS troubleshooting — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html
- Stopped tasks — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html#ts-stopped
- CannotPullContainerError — https://repost.aws/knowledge-center/ecs-pull-container-error
- ENI trunking — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/container-instance-eni.html
- ECS circuit breaker — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
- Fargate platform versions — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/platform_versions.html
- ECS task execution role — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html
- ECS task role — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html
