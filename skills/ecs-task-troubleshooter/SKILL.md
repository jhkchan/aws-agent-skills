---
name: ecs-task-troubleshooter
description: >-
  Diagnoses why AWS ECS tasks fail to start, transition to STOPPED
  immediately, fail health checks, crash-loop, cannot pull container
  images, or fail placement — via a symptom-to-cause decision tree that
  covers ENI attachment, exit codes, memory/OOM, ALB/target-group health
  check config, application errors in CloudWatch Logs, ECR repo policy,
  and capacity/attribute constraints. Emits a deterministic verdict
  (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the specific
  failure category and evidence from describe-tasks / describe-services
  / describe-task-definition / get-log-events / describe-target-health.
  Use when an ECS task is stuck in PROVISIONING, transitions to STOPPED,
  fails ELB health checks, restarts continuously, cannot pull from ECR,
  or fails placement.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works on supplied describe-tasks /
  describe-services JSON. Live-account diagnosis uses aws ecs
  describe-tasks, describe-services, describe-task-definition, aws logs
  get-log-events, aws elbv2 describe-target-health (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - ECS
  - Fargate
  - EC2 launch type
  - task failure
  - stoppedReason
  - PROVISIONING stuck
  - ENI attachment
  - exit code
  - OutOfMemory
  - OOM
  - health check
  - ALB target group
  - crash loop
  - image pull
  - ECR
  - placement failure
  - capacity provider
  - CloudWatch Logs
  - circuit breaker
tags: [ecs, compute, troubleshoot, task-failure, fargate, ec2, health-check, oom, image-pull]
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
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing why an ECS task stays in PROVISIONING, transitions to
    STOPPED, fails ALB/ECS health checks, restarts continuously, cannot
    pull a container image from ECR, or fails placement; investigating
    a deployment rollback; or interpreting describe-tasks
    stoppedReason / lastStatus / containers[].reason.
  activation_triggers:
    - "ECS task stopped"
    - "ECS task PROVISIONING stuck"
    - "ECS task PENDING forever"
    - "ECS health check failing"
    - "ECS task crash loop"
    - "ECS cannot pull container image"
    - "ECS placement failed"
    - "ECS task OutOfMemory"
    - "ECS task exited with code"
    - "ALB target unhealthy ECS"
  invocation_schema: >-
    Input: either (a) a symptom description (the failing service/cluster,
    the observed state, any error strings from the console), OR (b) a
    live-account scenario where the agent runs aws ecs describe-tasks /
    describe-services / describe-task-definition / aws logs get-log-events
    to gather evidence. Output: a deterministic INCIDENT / VERDICT /
    ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT ∈
    {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names
    the specific failure category (PROVISIONING_STUCK /
    ESSENTIAL_CONTAINER_EXIT / OOM / HEALTH_CHECK / CRASH_LOOP /
    IMAGE_PULL / PLACEMENT) and the offending config element.
---

# ECS Task Troubleshooter

## Activation

Activate this skill when the user reports an ECS task lifecycle failure.
Trigger phrases: "ECS task stopped", "ECS task PROVISIONING stuck",
"ECS task PENDING forever", "ECS health check failing", "ECS task crash
loop", "ECS cannot pull container image", "ECS placement failed", "ECS
task OutOfMemory", "ECS task exited with code", "ALB target unhealthy
ECS".

## Mindset

**One-line takeaway:** every ECS task failure has a `stoppedReason` and
a `containers[].reason` field — these strings are the primary diagnostic
surface, but they are often generic ("Essential container in task
exited"). The job of this skill is to walk from the symptom category to
the specific root cause by combining describe-tasks output with
describe-task-definition, CloudWatch Logs, and ELB target health.

Three facts make ECS troubleshooting different from generic container
debugging:

- **The ECS task lifecycle has six states, and the failure cause depends
  on WHICH transition failed.** A task stuck in PROVISIONING has a
  different cause set (ENI attachment, capacity) than a task that
  transitions RUNNING → STOPPED within seconds (essential container
  exit, OOM, image pull). Diagnosing without knowing the transition is
  guessing.
- **`stoppedReason` is high-level; `containers[].reason` is specific.**
  The task-level `stoppedReason` often says "Essential container in
  task exited" with no detail. The per-container `reason` field in the
  same describe-tasks response usually has the exit code and the
  specific cause ("Essential container in task exited", "CannotPullContainerError",
  "OutOfMemoryError"). Always read both.
- **ECS hides application errors behind infrastructure signals.** A
  crash-looping task often has a perfectly healthy task definition,
  service configuration, and capacity — the root cause is in the
  application logs (CloudWatch Logs), not in any ECS field. Without
  reading `get-log-events`, the diagnosis is incomplete.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| Task stays `PROVISIONING` > 2 minutes (Fargate) or > 1 minute (EC2) | PROVISIONING_STUCK | `describe-tasks` → ENI attachment status; subnet IP capacity |
| Task `STOPPED` within seconds of `RUNNING`, exit code in `containers[].reason` | ESSENTIAL_CONTAINER_EXIT | Exit code + CloudWatch Logs (last 1 minute) |
| Task `STOPPED`, `stoppedReason` mentions memory | OOM | Task definition memory limit vs container RSS; `docker stats` |
| Target group targets `unhealthy`, draining, or unused | HEALTH_CHECK | `describe-target-health` + ALB health check path/port |
| Task transitions `RUNNING` → `STOPPED` repeatedly with same exit code | CRASH_LOOP | CloudWatch Logs error pattern; missing env var / config |
| `stoppedReason` mentions "CannotPullContainer" or "image" | IMAGE_PULL | ECR repo policy; image digest; lifecycle policy; exec role ECR perms |
| Service events show "was unable to place a task" / "No ContainerInstances were found" | PLACEMENT | Capacity provider status; AZ constraints; instance attributes |
| Task definition `cpu`/`memory` exceeds instance capacity (EC2) | PLACEMENT | Instance registered CPU/memory vs task definition request |

See the ordered steps below for the full diagnostic walk.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Before any deep walk, gather these three pieces. Each step below
branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Task ARN + cluster** | User-provided or `aws ecs list-tasks --service <svc>` | All describe-tasks calls need this |
| **Last observed state + stoppedReason** | `aws ecs describe-tasks --tasks <arn>` | Drives the symptom category |
| **Container reasons + exit codes** | Same `describe-tasks` response, `containers[].reason` and `containers[].exitCode` | Narrows from symptom to cause |

If the user has not provided the task ARN or cluster, output:

```text
INCIDENT: <service> on <cluster> — <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without task ARN. Identify the failing task
with: aws ecs list-tasks --cluster <cluster> --service-name <service>
--desired-status STOPPED  (or RUNNING for stuck tasks)
MISSING:
  - Task ARN (or service+cluster name so we can find it)
  - Last observed state (PROVISIONING / RUNNING / STOPPED)
```

If the user reports "tasks keep stopping" but does not know which task
or service, ask for the cluster name. Then run:

```bash
aws ecs describe-services --cluster <cluster> --services <service>
# events[] shows the most recent service-level events including
# "task has stopped" and "was unable to place a task"
aws ecs list-tasks --cluster <cluster> --desired-status STOPPED --max-items 5
```

### Step 1: Identify the symptom category

Map the observed state to one of six categories. Each category has a
different diagnostic walk in Steps 2-7.

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. PROVISIONING_STUCK** | `lastStatus: PROVISIONING` for > 2 min (Fargate) or > 1 min (EC2); `desiredStatus: RUNNING` | Step 2 |
| **B. ESSENTIAL_CONTAINER_EXIT** | `lastStatus: STOPPED`, transitioned from RUNNING within seconds, `stoppedReason: "Essential container in task exited"` | Step 3 |
| **C. OOM** | `stoppedReason: "OutOfMemoryError"` or `containers[].reason: "OOMKilled"`; alternatively task-level STOPPED with `stoppedReason: "Essential container in task exited"` + container exit code 137 | Step 4 |
| **D. HEALTH_CHECK** | Task RUNNING but target group targets `unhealthy` or service events show deregistration | Step 5 |
| **E. CRASH_LOOP** | Repeated STOPPED → STARTED cycles with the same exit code; service deployment unstable | Step 6 |
| **F. IMAGE_PULL** | `stoppedReason` or `containers[].reason` mentions "CannotPullContainer", "image", "manifest", "ECR" | Step 7 |
| **G. PLACEMENT** | `describe-services` events[] shows "was unable to place a task", "No ContainerInstances were found", "unsatisfiable" | Step 8 |

If the symptom matches more than one category, pick the EARLIEST
transition failure. PROVISIONING_STUCK precedes IMAGE_PULL precedes
ESSENTIAL_CONTAINER_EXIT precedes HEALTH_CHECK precedes CRASH_LOOP. The
earliest category in the lifecycle is the cause; later categories are
consequences.

### Step 2: PROVISIONING_STUCK diagnostic

A task that stays in PROVISIONING has not yet reached RUNNING. The
failure is in the platform's preparation: ENI attachment (awsvpc), EBS
volume attachment, capacity reservation, or compute capacity.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Fargate, `PROVISIONING` > 2 min, then `STOPPED` with `stoppedReason: "Timeout waiting for network interface"` | ENI attachment failing — subnet out of free IPs, or subnet security group limit hit | Check subnet available IP count; check service-level security group rules count |
| Fargate, `PROVISIONING` > 2 min, intermittent | Fargate capacity (spot vs on-demand) — Fargate spot can wait for capacity | Switch to on-demand or wait; not a config issue |
| EC2 launch type, `PENDING` forever | Container instance has insufficient registered CPU/memory for the task | `describe-container-instances` → compare `remainingResources` against task definition `cpu`/`memory` |
| EC2 launch type, awsvpc mode, `PROVISIONING` forever | ENI attachment failing on the host — `ECS_ENABLE_AWSVPC_BOOTSTRAP_CHECK` misconfigured, or ENI trunking not enabled where needed | Check ECS agent logs on the host; verify trunking config for supported instance types |
| EBS volume attachment failing | The task definition mounts an EBS volume but the AZ lacks EBS capacity or the volume type is unavailable | Check `describe-tasks` attachments; CloudTrail for `AttachVolume` failures |
| Service-linked role missing | Fargate ENI attachment requires `AWSServiceRoleForECS` — without it, ENI creation fails | `aws iam get-role --role-name AWSServiceRoleForECS` — should exist |
| EFA network interface failing (HPC/ML tasks) | EFA not supported on the instance type or AZ | Verify instance type supports EFA; check security group for EFA traffic |

**Diagnostic commands:**

```bash
aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].{lastStatus:lastStatus,desiredStatus:desiredStatus,stoppedReason:stoppedReason,containers:containers[*].{name:name,reason:reason,exitCode:exitCode},attachments:attachments}'

# For Fargate ENI failures, check subnet IP availability:
aws ec2 describe-subnets --subnet-ids <subnet-id> \
  --query 'Subnets[0].{AvailableIp:AvailableIpAddressCount,CIDR:CidrBlock}'

# For EC2 launch type, check container instance capacity:
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <ci-id> \
  --query 'containerInstances[0].{remainingResources:remainingResources,runningTasks:runningTasksCount,registeredResources:registeredResources}'
```

**Common fix patterns:**

- ENI attachment / subnet IP exhaustion: add more subnets to the service's
  `networkConfiguration.awsvpcConfiguration.subnets`, OR clean up
  orphaned ENIs in the subnet, OR widen the CIDR.
- Service-linked role missing: `aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com`.
- Fargate spot capacity: switch to on-demand for the workload.
- EC2 instance capacity: scale out the ASG or use a capacity provider.

### Step 3: ESSENTIAL_CONTAINER_EXIT diagnostic

A task that reaches RUNNING and transitions to STOPPED within seconds
almost always has an essential container that exited. The exit code and
container reason narrow the cause.

| Exit code | Meaning | First probe |
|---|---|---|
| 0 | Clean exit — application thinks it is done | CloudWatch Logs — application may have completed a batch and should NOT be marked essential, OR an env var like `RUN_ONCE=true` was set |
| 1 | General application error | CloudWatch Logs (last 1 minute before exit) — exception traceback |
| 137 | SIGKILL — usually OOM killer, sometimes manual kill | See Step 4 (OOM) |
| 139 | SIGSEGV — segfault, native library crash | CloudWatch Logs for native stack trace; check glibc compatibility |
| 255 | Application-defined error code | CloudWatch Logs |
| Missing exit code + "CannotPullContainer" reason | Image pull failed before container started | Step 7 (IMAGE_PULL) |

**Diagnostic command:**

```bash
aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].containers[*].{name:name,exitCode:exitCode,reason:reason,lastStatus:lastStatus}'

# Then pull the application logs for the failing container:
aws logs get-log-events \
  --log-group-name /ecs/<family> \
  --log-stream-name ecs/<container-name>/<task-id> \
  --start-time $(($(date +%s) * 1000 - 60000)) \
  --limit 100
```

**Common root causes for exit code 1:**

- Missing required environment variable (the application crashes during
  bootstrap when reading `process.env.DB_HOST`).
- Secret injection failure: the `secrets` array references a Secrets
  Manager ARN that the execution role cannot read
  (`ResourceInitializationError: unable to retrieve secrets`).
- Database connection refused: the application starts faster than the
  dependency; use a retry/backoff or a health-check dependency.
- Config file missing: a ConfigMap-style file was expected at a mount
  path that is not configured.

If the container exits too quickly to produce logs (e.g., the secret
injection fails before the container starts), the failure is in the
task definition's `secrets` configuration and the execution role's
IAM policy. Look in CloudTrail for `secretsmanager:GetSecretValue`
AccessDenied events around the task start time.

### Step 4: OOM diagnostic

Out-of-memory has two flavors with different causes:

### 4a. Container OOM (`OOMKilled`, exit code 137)

The container exceeded its `memory` hard limit. The Docker daemon
OOM-kills the container process.

| Cause | Probe | Fix |
|---|---|---|
| `memory` hard limit too low | `describe-task-definition` container `memory` vs application RSS profile | Raise `memory` (container-level on EC2; task-level on Fargate) |
| Memory leak in application | CloudWatch Container Insights — `MemoryUtilization` trending up over hours/days | Fix the leak; meanwhile add a periodic restart (sidecar or scheduled action) |
| Java JVM heap larger than container memory | `-Xmx` set higher than container `memory`, OR not set and JVM uses host memory hints | Set `-Xmx` to 75% of container memory; use `-XX:MaxRAMPercentage=75` |
| Off-heap / native memory growth | Container Insights shows RSS growth beyond JVM heap | Profile native allocations; raise `memory` |

### 4b. Host OOM (EC2 launch type)

The container did not exceed its own limit, but the host ran out of
memory. Multiple co-located containers summed over the host limit.

| Cause | Probe | Fix |
|---|---|---|
| No container-level `memory` hard limit on co-located tasks | `describe-task-definition` for each running task on the host | Set `memory` on every container |
| Oversubscription — host runs more tasks than memory allows | `describe-container-instances` remaining memory vs running task count | Reduce task density per host; scale out |
| ECS agent or `amazon-ecs-cni-plugins` consuming memory | SSH to host, `top` / `ps aux --sort -rss` | Upgrade ECS agent; report bug |

**Diagnostic command:**

```bash
aws ecs describe-task-definition --task-definition <family:revision> \
  --query 'taskDefinition.containerDefinitions[*].{name:name,memory:memory,memoryReservation:memoryReservation}'

aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].{stoppedReason:stoppedReason,containers:containers[*].{name:name,exitCode:exitCode,reason:reason}}'

# Enable CloudWatch Container Insights for memory utilization trends:
aws ecs update-cluster-settings --cluster <cluster> \
  --settings name=containerInsights,value=enabled
```

**Fargate vs EC2 memory semantics:**

- Fargate: task-level `memory` is the hard limit. Container-level `memory`
  is advisory. A container exceeding its own limit but not the task limit
  will NOT be OOM-killed by Docker — Fargate enforces at the task level.
- EC2: container-level `memory` is the Docker cgroup hard limit. A
  container exceeding it is OOM-killed regardless of host free memory.

Misdiagnosing Fargate as EC2 leads to "raise container memory" advice
that has no effect — the fix is to raise task-level `memory` (which
requires a Fargate-compatible CPU/memory combination).

### Step 5: HEALTH_CHECK diagnostic

A task is RUNNING but the ALB target group marks it `unhealthy`, and
ECS eventually stops the task. The failure is in the path between the
load balancer and the application.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Targets `unhealthy` from start | ALB health check path returns non-200 | `curl` the health check path from inside the container; check application logs |
| Targets `unhealthy` after being `healthy` | Application degraded; dependency outage; connection pool exhausted | Application logs around the transition; downstream dependency status |
| Targets `healthy` in target group but ECS stops task anyway | ECS health check (separate from ALB) failing | `describe-tasks` healthStatus; task definition `healthCheck` |
| Intermittent `unhealthy` | Health check grace period too short — target deregisters before app finishes startup | `describe-services` healthCheckGracePeriodSeconds |
| New tasks `unhealthy` after deploy, old tasks fine | Container port or path changed in new revision; security group rule missing for new port | Compare old/new task definition port mappings; security group rules |
| Draining targets accumulating | Deregistration delay too long for the workload | `describe-target-groups` deregistrationDelay |

**Diagnostic walk:**

1. **Identify whose health check is failing.** ALB target group health
   and ECS task definition health check are independent. Identify which
   one is producing the unhealthy verdict first.
2. **For ALB health checks:** read `describe-target-groups` for the
   configured path, port, interval, timeout, healthy/unhealthy
   thresholds. Then `describe-target-health` for the per-target status
   and `description` field (which has the failure reason).
3. **Verify the path responds:** use ECS Exec
   (`aws ecs execute-command`) to shell into the running container and
   `curl localhost:<port><path>`. A 200 response means the application
   is healthy; the ALB cannot reach it (security group, port mapping).
   A non-200 response means the application has a bug.
4. **Verify the network path:** on awsvpc mode, the task ENI security
   group must allow inbound from the ALB on the container port. On
   bridge mode, the host security group must allow inbound and the
   container port must be mapped to a host port.
5. **Check the grace period:** if `healthCheckGracePeriodSeconds` is
   shorter than the application's startup time, the ALB will fail
   health checks before the application is ready. Raise the grace
   period.
6. **Check the target group deregistration delay:** during deployments,
   old tasks deregister and stop accepting new connections but remain
   in `draining` for the configured delay. If the delay is too long,
   the deployment appears stalled.

**Diagnostic commands:**

```bash
aws elbv2 describe-target-groups --load-balancer-arn <alb-arn> \
  --query 'TargetGroups[*].{name:TargetGroupName,path:HealthCheckPath,port:HealthCheckPort,protocol:HealthCheckProtocol,interval:HealthCheckIntervalSeconds,timeout:HealthCheckTimeoutSeconds,healthy:HealthyThresholdCount,unhealthy:UnhealthyThresholdCount}'

aws elbv2 describe-target-health --target-group-arn <tg-arn> \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,port:Target.Port,state:TargetHealth.State,reason:TargetHealth.Reason,desc:TargetHealth.Description}'

aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{gracePeriod:healthCheckGracePeriodSeconds,lbConfig:loadBalancers,deployments:deployments[*].{status:status,running:runningCount,desired:desiredCount,rollout:rolloutState}}'

aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].{healthStatus:healthStatus,containers:containers[*].{name:name,healthStatus:healthStatus,lastStatus:lastStatus}}'
```

**Common fix patterns:**

- Path returns 404: align the ALB health check path with the
  application's actual health endpoint. Common: `/health` vs `/healthz`
  vs `/api/health`.
- Path returns 200 but ALB still unhealthy: security group missing the
  inbound rule from the ALB subnet CIDR or security group.
- Bridge mode, host port `0`: dynamic port mapping — the ALB auto-
  discovers the port. But `hostPort: 0` requires the ALB target type to
  be `instance` (not `ip`); awsvpc requires target type `ip`.
- Grace period too short: a Spring Boot app may need 60-120 seconds to
  start; raise `healthCheckGracePeriodSeconds` to 120+.

### Step 6: CRASH_LOOP diagnostic

A crash loop is repeated `RUNNING` → `STOPPED` cycles with the same
exit code. The service scheduler restarts the task (up to the
deployment circuit breaker threshold). The root cause is almost always
in the application logs, not in the ECS configuration.

**Diagnostic walk:**

1. **Confirm the loop:** `describe-services` events should show a
   repeating pattern of "has started" and "has stopped" within minutes.
2. **Read the application logs for the most recent crash:** the logs
   typically contain the exception traceback or error message that
   caused the exit. Look at the last 100 lines before exit.
3. **Cross-reference the exit code:** exit 1 with logs showing
   "KeyError: 'DATABASE_URL'" → missing environment variable. Exit 1
   with logs showing "Connection refused" → dependency unavailable.
   Exit 137 → OOM (Step 4).
4. **Check the deployment circuit breaker:** if enabled
   (`deploymentConfiguration.deploymentCircuitBreaker.enabled: true`),
   the service will roll back after a threshold of failures. The
   rollback itself produces events — distinguish "circuit breaker open,
   rolling back" from "tasks crash-looping."
5. **Check for missing secrets or config:** the application may require
   an env var that is not in the task definition's `environment` or
   `secrets`. Compare the failed task definition to the last known-good
   revision.

**Diagnostic command:**

```bash
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{events:events[:10],circuitBreaker:deploymentConfiguration.deploymentCircuitBreaker}'

aws logs filter-log-events \
  --log-group-name /ecs/<family> \
  --filter-pattern "ERROR Exception Traceback" \
  --start-time $(($(date +%s) * 1000 - 600000)) \
  --limit 50
```

**Common crash-loop patterns:**

- Application reads an env var that is not set; crash on bootstrap.
  Fix: add the env var to the task definition, or add a default.
- Application connects to a database that does not exist or refuses
  connections. Fix: verify the DB endpoint and security group.
- Application expects a file at a mount path that is not configured
  (ConfigMap, secret file). Fix: add the volume + mountPoint.
- Application version mismatch: a new image tag points to a build with
  a breaking change. Fix: roll back to the previous task definition
  revision.
- TLS certificate expired for an outbound dependency. Fix: renew the
  cert or use the AWS CA bundle.

### Step 7: IMAGE_PULL diagnostic

A task fails before the container starts because the ECS agent (EC2)
or Fargate platform cannot pull the container image.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `CannotPullContainerError: inspect image has been retried` | ECR repo policy does not allow the execution role | `ecr:GetRepositoryPolicy` — verify execution role ARN |
| `CannotPullContainerError: RequestError: send request failed` | Network: no route to ECR (VPC endpoint missing, NAT gateway missing) | Check VPC endpoint for ECR (ecr.api + ecr.dkr); NAT gateway route |
| `CannotPullContainerError: manifest unknown` | Image tag does not exist or was deleted by ECR lifecycle policy | `ecr describe-images` — verify tag exists; check lifecycle policy |
| `CannotPullContainerError: image digest mismatch` | Image was overwritten with the same tag (immutability disabled) | Enable immutable tags; reference by digest |
| `Client.UnauthorizedOperation` for `ecr:BatchGetImage` | Execution role missing ECR permissions | Add `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage` |
| Slow image pull causing PROVISIONING timeout | Image too large; no image cache | Use ECR cross-region replication; optimise Dockerfile layer cache |
| Private registry (non-ECR) auth failing | `repositoryCredentials` not configured or credentials expired | Update the secrets-arn in `repositoryCredentials` |

**Diagnostic walk:**

1. **Read the full `stoppedReason` and `containers[].reason`.** ECS
   surfaces "CannotPullContainerError" with a sub-reason. The sub-reason
   distinguishes auth, network, manifest, and digest failures.
2. **Verify the image exists in ECR:**
   `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>`.
3. **Verify the execution role has ECR permissions:** the four required
   actions are `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`,
   `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`. The managed policy
   `AmazonEC2ContainerRegistryReadOnly` covers all four.
4. **Verify network reachability:** from a Fargate task in a private
   subnet, the route to ECR goes through a NAT gateway OR a VPC endpoint
   for ECR (interface endpoint, two endpoints needed: `com.amazonaws.<region>.ecr.api`
   and `com.amazonaws.<region>.ecr.dkr`). Verify the route table and
   VPC endpoint existence.
5. **Verify ECR repo policy for cross-account pulls:** if the image is
   in account B's ECR but the task runs in account A, BOTH the task
   execution role in A AND the ECR repo policy in B must allow the
   pull. This is the cross-account intersection rule.
6. **Check the ECR lifecycle policy:** if a lifecycle rule deletes
   untagged or older images, the specific tag/digest may have been
   purged. `ecr describe-images` will return empty.

**Diagnostic commands:**

```bash
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>
aws ecr get-repository-policy --repository-name <repo>
aws ecr get-lifecycle-policy --repository-name <repo>

# Verify execution role ECR permissions:
aws iam list-attached-role-policies --role-name <execution-role>
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<execution-role> \
  --action-names ecr:GetAuthorizationToken ecr:BatchCheckLayerAvailability \
                  ecr:GetDownloadUrlForLayer ecr:BatchGetImage \
  --resource-arns arn:aws:ecr:<region>:<account>:repository/<repo>
```

### Step 8: PLACEMENT diagnostic

A service scheduler reports it cannot place a task. The failure is in
matching the task definition's requirements to available capacity.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `No ContainerInstances were found` (EC2 launch type) | No EC2 instances registered to the cluster | `aws ecs list-container-instances --cluster <cluster>` |
| `was unable to place a task ... no container instances met the requirements` | Instance has insufficient CPU/memory for the task | `describe-container-instances` — compare `remainingResources` vs task def `cpu`/`memory` |
| `unsatisfiable: attribute [ecs.capability.execution-role-awslogs] is not available` | Task definition requires a capability the instance does not advertise | Match instance AMI / ECS agent version to the required capability |
| `unsatisfiable: member of constraint ...` (AZ constraint) | Service-level AZ constraint excludes instances in the AZs with capacity | `describe-services` availabilityZoneConstraints |
| Fargate `Compute capacity unavailable` | Fargate capacity (especially spot) unavailable in the AZ | Switch to on-demand or different AZ |
| GPU/accelerator constraint | Instance type lacks GPU; instance does not advertise `ecs.capability.gpu` | Use a GPU instance type (G4dn, P4, etc.) |
| Capacity provider not at ready state | ASG capacity provider scaling failed or not configured | `describe-capacity-providers` — verify status and ASG health |

**Diagnostic commands:**

```bash
aws ecs list-container-instances --cluster <cluster>
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <ci-1> <ci-2> \
  --query 'containerInstances[*].{status:status,agent:agentConnected,remaining:remainingResources,attributes:attributes,running:runningTasksCount}'

aws ecs describe-capacity-providers --cluster <cluster>
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{placement:placementConstraints,strategy:placementStrategy,capacity:capacityProviderStrategy}'
```

**Common fix patterns:**

- Insufficient CPU/memory: scale out the ASG, or add a capacity provider
  with auto-scaling tied to the service's `CPUUtilization` / `MemoryUtilization`.
- Attribute constraint: upgrade the ECS agent on the host, or use a
  different instance type/AMI that advertises the required capability.
- AZ constraint: add subnets in additional AZs to the service's
  network configuration, OR relax the constraint.
- Capacity provider scaling not triggering: verify the capacity provider
  has `managedScalingStatus: ENABLED` and a target tracking policy.

### Step 9: Map to root-cause catalog

After the walk identifies the category, cross-reference with this
catalog. The catalog names the top eight ECS failure patterns and
their canonical fixes.

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Subnet IP exhaustion (Fargate awsvpc) | PROVISIONING_STUCK | Add subnets, clean up orphaned ENIs, widen CIDR |
| 2 | Execution role missing ECR read permissions | IMAGE_PULL | Attach `AmazonEC2ContainerRegistryReadOnly` managed policy |
| 3 | Application crash on missing env var / secret injection failure | ESSENTIAL_CONTAINER_EXIT / CRASH_LOOP | Add the env var / `secrets` entry; verify exec role has `secretsmanager:GetSecretValue` |
| 4 | Container memory limit too low (OOM 137) | OOM | Raise task-level (Fargate) or container-level (EC2) `memory` hard limit |
| 5 | ALB health check path/port mismatch | HEALTH_CHECK | Align the configured path with the application's actual endpoint; verify security group + port mapping |
| 6 | Health check grace period too short | HEALTH_CHECK | Raise `healthCheckGracePeriodSeconds` above application startup time |
| 7 | ECR repo policy / lifecycle policy image purge | IMAGE_PULL | Update repo policy or restore image tag |
| 8 | EC2 instance has insufficient registered capacity | PLACEMENT | Scale out the ASG / capacity provider; right-size task definition CPU/memory |

### Step 10: Verify the fix

Before applying, validate the proposed fix with one of:

- **For task definition changes:** register a new revision and run a
  one-off task (`aws ecs run-task`) before updating the service.
- **For service configuration changes:** apply during a maintenance
  window and monitor `describe-services` events for the deployment.
- **For capacity changes:** wait for the ASG / capacity provider to
  reach steady state before deploying new tasks.
- **For health check changes:** use ECS Exec to shell into the
  container and `curl` the health check endpoint manually before
  trusting the ALB verdict.

### Step 11: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category
  and a specific configuration element (task definition field, service
  configuration, IAM policy, capacity setting). Output REMEDIATION with
  the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator
  cannot supply evidence (e.g., application logs require elevated
  CloudWatch access). Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: capacity provider owned by another team, ECR repo in another
  account, VPC networking owned by a network team. Output the
  escalation target and the specific request to make.

## Output format

```text
INCIDENT: <cluster / service / task ARN>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - <describe-tasks signal>: <value>
  - <describe-services signal>: <value>
  - <describe-task-definition signal>: <value>
  - <get-log-events signal>: <key log line>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with field name>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — ALB health check mismatch

```text
INCIDENT: cluster prod-app / service api-svc / task 6f8a...
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: HEALTH_CHECK — ALB target group health check path /healthz
does not match the application's actual endpoint /api/health
EVIDENCE:
  - describe-tasks: healthStatus "UNHEALTHY", lastStatus "RUNNING"
  - describe-target-groups: HealthCheckPath "/healthz", HealthCheckPort
    "traffic-port", HealthCheckProtocol "HTTP"
  - get-log-events: no requests logged on /healthz; only requests on
    /api/health
  - describe-task-definition: container portMappings 8080→8080,
    hostPort 0 (awsvpc)
ROOT_CAUSE_CATALOG: #5 (ALB health check path/port mismatch)
REMEDIATION:
  1. Update the target group health check path to /api/health:
     aws elbv2 modify-target-group --target-group-arn <tg-arn> \
       --health-check-path /api/health
  2. Verify with curl from inside the container:
     aws ecs execute-command --cluster prod-app --task <arn> \
       --container api --command "curl -i http://localhost:8080/api/health" --interactive
  3. Monitor target health: aws elbv2 describe-target-health \
     --target-group-arn <tg-arn> — targets should transition to
     healthy within 60-120 seconds.
```

## Diagnostic command reference

Run these in order. Each command's output narrows the decision tree.

```bash
# 1. Identify the failing task and its last state.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{events:events[:10],desiredCount:desiredCount,runningCount:runningCount,deployments:deployments[*].{status:status,running:runningCount,desired:desiredCount,rollout:rolloutState,failed:failedTasks}}'

aws ecs list-tasks --cluster <cluster> --service-name <service> --desired-status STOPPED --max-items 5

# 2. Read the full stoppedReason and container reasons/exit codes.
aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].{lastStatus:lastStatus,desiredStatus:desiredStatus,stoppedReason:stoppedReason,stoppedAt:stoppedAt,startedAt:startedAt,healthStatus:healthStatus,containers:containers[*].{name:name,exitCode:exitCode,reason:reason,lastStatus:lastStatus,healthStatus:healthStatus},attachments:attachments[*].{type:type,status:status,reason:reason}}'

# 3. Read the task definition (CPU/memory, port mappings, secrets, healthCheck).
aws ecs describe-task-definition --task-definition <family:revision> \
  --query 'taskDefinition.{cpu:cpu,memory:memory,networkMode:networkMode,executionRole:executionRoleArn,taskRole:taskRoleArn,containers:containerDefinitions[*].{name:name,image:image,cpu:cpu,memory:memory,memoryReservation:memoryReservation,ports:portMappings,secrets:secrets,env:environment,health:healthCheck,essential:essential}}'

# 4. Pull the application logs for the failing container (last minute before exit).
aws logs get-log-events \
  --log-group-name /ecs/<family> \
  --log-stream-name ecs/<container-name>/<task-id> \
  --start-time $(($(date +%s) * 1000 - 60000)) \
  --limit 100

# 5. For health-check failures, read the target group config and target status.
aws elbv2 describe-target-groups --load-balancer-arn <alb-arn>
aws elbv2 describe-target-health --target-group-arn <tg-arn>

# 6. For image-pull failures, verify the ECR image and policy.
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>
aws ecr get-repository-policy --repository-name <repo>
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<execution-role> \
  --action-names ecr:GetAuthorizationToken ecr:BatchCheckLayerAvailability ecr:GetDownloadUrlForLayer ecr:BatchGetImage

# 7. For placement failures, list container instances and their capacity.
aws ecs list-container-instances --cluster <cluster>
aws ecs describe-container-instances --cluster <cluster> --container-instances <ci-1> <ci-2> \
  --query 'containerInstances[*].{status:status,remaining:remainingResources,attributes:attributes,running:runningTasksCount}'

# 8. For deployment issues, check the circuit breaker state.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{circuitBreaker:deploymentConfiguration.deploymentCircuitBreaker,rollback:deploymentConfiguration.rollback}'
```

## Expert edge cases

These patterns represent genuine, non-obvious ECS failure modes that a
senior operator would catch but a generalist would miss.

### Exit code 137 is not always OOM

Exit 137 means SIGKILL. While the OOM killer is the most common cause,
137 also appears when:

- The ECS agent sends SIGKILL after the task is deregistered (30 seconds
  after SIGTERM during draining). Check `stoppedAt` vs `startedAt` — if
  the task ran for ~30 seconds after a deployment, it was killed by
  draining, not OOM.
- The host kernel killed the container for a non-memory reason (e.g.,
  the host was running low on disk for container ephemeral storage).
- A liveness probe in the orchestrator killed the container (not
  applicable to ECS directly but to sidecar orchestrators).

If `describe-tasks` shows `stoppedReason: "Essential container in task
exited"` and `containers[].reason: "OOMKilled"`, it is OOM. If the
reason is empty or different, check the timing first.

### Fargate ephemeral storage exhaustion

Fargate tasks have an ephemeral storage limit (default 20 GB, up to 200
GB). A task that writes large temporary files (build artifacts, ML
checkpoints, log buffers) can exhaust ephemeral storage and fail with
`stoppedReason: "Essential container in task exited"` and no clear
exit-code explanation. The Fargate platform reports this differently
from container OOM. The diagnostic is `docker images` size + container
scratch usage, but you cannot SSH to Fargate — use ECS Exec to inspect,
or `docker df` if available in the image.

### ECS deployment circuit breaker open vs task failure loop

When the deployment circuit breaker is enabled, repeated task failures
during a deployment trigger a rollback. The events show "circuit
breaker triggered, rolling back" — operators often mistake this for the
cause. The cause is the underlying task failure that triggered the
breaker; the rollback is the consequence. Always read the task-level
`stoppedReason` from before the breaker opened.

### Bridge mode dynamic port mapping and ALB target type

A bridge-mode task with `hostPort: 0` gets a dynamic port assigned by
Docker. The ALB target group must be of type `instance` for the ALB to
discover the dynamic port via the ECS scheduler's registration. If the
target group is of type `ip` and the task uses bridge mode with dynamic
ports, the ALB never learns the port and the target stays
`unhealthy` / `unused`. The fix is to either switch the task to
`awsvpc` mode (recommended) or change the target group to type
`instance`.

### awsvpc mode and ENI security group limits

Each awsvpc task gets its own ENI. Each ENI has a security-group
attachment limit (typically 5, varies by instance type). A service
configured with 5+ security groups will fail to attach all of them at
task start. The failure surfaces as PROVISIONING_STUCK with ENI
attachment errors. The fix is to consolidate the security group rules
into fewer groups (under the per-ENI limit).

### Service Connect / Cloud Map integration failures

When using ECS Service Connect or Cloud Map for service discovery, a
task can be RUNNING but unreachable from other services because the
service-discovery registration failed. The failure is in the
`serviceRegistries` configuration or in the Cloud Map namespace. The
diagnostic is `aws servicediscovery get-instance` for the task's
registration — if the registration is missing or stale, the task is
invisible to other services even though ECS shows it as healthy.

### Container `essential: false` and partial task failures

A task with one essential container and one non-essential container
behaves differently when the non-essential container exits. The task
continues running (because the essential container is still up). But
if the non-essential container was a sidecar providing required
functionality (e.g., a proxy), the application may degrade silently.
The diagnostic is to read each container's `lastStatus` separately —
do not assume the task-level `RUNNING` means all containers are
healthy.

### IAM Identity Center permission boundaries and ECS task roles

When using IAM Identity Center with permission boundaries, a task role
inherited via Identity Center may have a session policy that narrows
the effective permissions. A task role that "should" have S3 access
may have it restricted by the session policy. The diagnostic is to
read the Identity Center permission set attached to the user / group
that assumed the role, then run `aws iam simulate-principal-policy`
against the role ARN. This is the same session-policy gotcha as in
the iam-permission-troubleshooter skill.

### Graviton (ARM64) image architecture mismatch

A task definition that specifies `runtimePlatform.cpuArchitecture: "ARM64"`
but references an image built for X86_64 will fail at runtime with
`exec format error` in the container logs. The task may transition
from RUNNING to STOPPED quickly with exit code 1 and no clear
application error. The diagnostic is to `docker inspect` the image
locally and verify the `Architecture` field matches the task definition.

## Anti-Patterns — NEVER

- NEVER assume `stoppedReason: "Essential container in task exited"`
  is the root cause. It is the symptom. The root cause is in the
  container's exit code and CloudWatch Logs. Always read both before
  declaring the cause.

- NEVER recommend raising container memory without checking whether the
  task is on Fargate (where container `memory` is advisory) or EC2
  (where it is enforced). Misdiagnosing the launch type leads to a fix
  that has no effect.

- NEVER recommend `privileged: true` as a fix for any ECS failure.
  Privileged mode is almost never the actual fix and grants full host
  access on EC2. The real fix is almost always a missing capability,
  file permission, or network configuration.

- NEVER declare ROOT_CAUSE_FOUND without reading the application logs.
  A crash-looping task has its cause in CloudWatch Logs, not in any
  ECS field. If you cannot access logs, emit NEED_MORE_INFO.

- NEVER assume the task definition is correct because it registered
  successfully. ECS validates JSON schema at registration but not
  semantic correctness — a typo in a secret ARN, a missing environment
  variable, or a wrong container port all register fine and fail at
  runtime.

- NEVER confuse ALB target group health with ECS task health. They are
  independent checks with independent failure modes. Always identify
  which one is failing first.

- NEVER conflate `hostPort: 0` (dynamic) with `hostPort` matching
  `containerPort` (static). Dynamic port mapping requires ALB target
  type `instance`; static or awsvpc works with `ip`. Mixing them is a
  common silent failure.

- NEVER recommend `healthCheckGracePeriodSeconds: 0` for production
  services. Applications that need 30+ seconds to start will fail the
  health check before they are ready and get killed by the scheduler.
  Set the grace period to the application's known startup time plus
  a margin.

- NEVER assume a deployment rollback means the deployment is broken.
  The rollback is triggered by the circuit breaker, which fires after
  a threshold of task failures. The cause is the underlying task
  failure; the rollback is the consequence. Always look at the
  task-level stoppedReason from before the breaker opened.

- NEVER declare IMAGE_PULL as the cause without verifying the image
  exists in ECR. The error string "CannotPullContainerError: inspect
  image has been retried" is also returned for transient network
  failures. Run `aws ecr describe-images` to confirm the image is
  present.

- NEVER recommend running an ECS task without an execution role. The
  execution role is required for ECR pulls and CloudWatch Logs
  delivery. Without it, the task cannot start if the image is in ECR
  or if `awslogs` logging is configured.

- NEVER assume capacity provider auto-scaling will respond instantly.
  Capacity provider scaling has a cooldown and a step-scaling
  schedule. A sudden spike in desired task count will exceed capacity
  until the ASG provisions new instances (60-120 seconds minimum).
  Pre-warm or use scheduled scaling for known spikes.

- NEVER treat `ECS_ENABLE_AWSVPC_BOOTSTRAP_CHECK=true` as a fix for
  awsvpc ENI attachment failures. The flag enables the check; it does
  not increase the ENI limit. The fix is to choose an instance type
  with higher ENI density, or use ENI trunking (supported instance
  types only), or reduce the task count per host.

- NEVER ignore the deployment circuit breaker state. A service with
  the breaker enabled will roll back automatically after a threshold
  of failures. Operators may not realise the rollback happened, and
  continue "fixing" the old revision while the service runs the
  rolled-back (previous) revision.

## Remediation guidance

### For PROVISIONING_STUCK

1. Read `describe-tasks.attachments` to identify which attachment
   (ENI, EBS volume) is failing.
2. For ENI failures (Fargate): check subnet IP availability. Add
   subnets to the service configuration, OR clean up orphaned ENIs.
3. For capacity failures (EC2 launch type): scale out the ASG or
   capacity provider; verify the new instance registers before retrying.
4. Verify `AWSServiceRoleForECS` exists in the account.

### For ESSENTIAL_CONTAINER_EXIT

1. Read the container exit code and CloudWatch Logs.
2. For exit 0: the application thinks it is done. Verify whether the
   container should be marked `essential: false` (batch job pattern),
   OR add a process supervisor (init) to keep the container alive.
3. For exit 1: read the traceback. Add the missing env var / config /
   dependency. Register a new task definition revision.
4. For exit 137 (OOM): see OOM remediation.
5. Register a new revision with the fix and update the service.

### For OOM

1. Identify container-level vs host-level OOM from `containers[].reason`.
2. For container OOM: raise the `memory` hard limit (container-level on
   EC2; task-level on Fargate).
3. For host OOM (EC2): set `memory` on every co-located container;
   reduce task density per host; scale out.
4. For Java: set `-XX:MaxRAMPercentage=75` so the JVM heap is bounded
   relative to the container limit.
5. Enable CloudWatch Container Insights to monitor memory utilisation
   trends and catch leaks before they OOM.

### For HEALTH_CHECK

1. Identify ALB vs ECS health check failure.
2. For ALB: align the configured path with the application's actual
   endpoint. Verify the security group allows inbound from the ALB
   on the container port. Verify the port mapping matches.
3. Raise `healthCheckGracePeriodSeconds` if the application needs more
   startup time.
4. Adjust the deregistration delay if draining targets accumulate.
5. Use ECS Exec to curl the health endpoint from inside the container
   for direct verification.

### For CRASH_LOOP

1. Read the application logs for the most recent crash.
2. Cross-reference the exit code and log pattern with common causes
   (missing env var, dependency outage, version mismatch).
3. If the deployment circuit breaker is open, the service has already
   rolled back. Identify the failing revision and fix it before the
   next deploy.
4. Roll back to the last known-good task definition revision if the
   fix is not immediately available.

### For IMAGE_PULL

1. Verify the image exists in ECR with `describe-images`.
2. Verify the execution role has ECR read permissions (use the
   `AmazonEC2ContainerRegistryReadOnly` managed policy).
3. Verify network reachability (NAT gateway or VPC endpoints for ECR).
4. For cross-account ECR, update the repo policy to allow the task
   execution role from the other account.
5. For digest mismatches, enable immutable tags on the ECR repo.

### For PLACEMENT

1. Verify container instances are registered with
   `aws ecs list-container-instances`.
2. Verify `remainingResources` (CPU, memory) on each instance covers
   the task definition request.
3. Verify the required attributes (capabilities, GPU) are advertised
   by at least one instance.
4. Configure or fix the capacity provider (ASG scaling, target
   tracking).
5. Relax AZ constraints or add subnets in additional AZs.

## Recent AWS features (2024-2026)

- **EBS volumes for ECS tasks (2024 GA):** ECS tasks can mount EBS
  volumes in addition to EFS. Troubleshoot EBS attachment failures in
  PROVISIONING state by reading `describe-tasks.attachments` for the
  EBS volume and checking AZ capacity.
- **Deployment alarm-based rollback (2024-2025):** ECS can roll back
  a deployment automatically when a CloudWatch alarm fires. Read the
  `deploymentConfiguration.alarms` field on the service to determine
  whether a rollback was alarm-triggered vs circuit-breaker-triggered.
- **ECS Service Connect (2024 GA):** Service Connect provides
  built-in service discovery and load balancing. Troubleshoot Service
  Connect failures via the service's `serviceConnectConfiguration`
  and the Cloud Map namespace.
- **Enhanced health check policies (2024-2025):** More granular
  health check configuration including graceful shutdown. Read the
  `healthCheck` field on the task definition and the service's
  `healthCheckGracePeriodSeconds` for the full picture.
- **Fargate platform version 1.4.0 (default LATEST):** Platform 1.4.0
  changed the logging delivery path and supports `initProcessEnabled`
  and ephemeral storage API. Troubleshoot tasks still on platform
  1.3.0 by upgrading to 1.4.0 — some features will become available
  and the logging agent path changes.
- **Capacity provider drift detection (2024-2025):** ECS now reports
  when a capacity provider's ASG drifts from the expected
  configuration. Read `describe-capacity-providers` for status.

## References

See `references/failure-decision-tree.md` for the full symptom-to-cause
walk with worked examples per category, and `references/diagnostic-
commands.md` for the canonical command script for each failure category.

## Domain

AWS CloudOps / ECS Compute Reliability & Container Operations.

## AWS documentation

- **Amazon Elastic Container Service Developer Guide** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- **ECS troubleshooting** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html
- **ECS task lifecycle** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle.html
- **Deployment circuit breaker** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
- **ECS health checks** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/health-checks.html
- **ECS capacity providers** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-capacity-providers.html
- **ECS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ecs/
