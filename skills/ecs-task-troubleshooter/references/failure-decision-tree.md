# ECS Task Failure Decision Tree — Reference

Supplementary reference for the ECS Task Troubleshooter skill. Walks
the full symptom-to-cause tree with worked examples per category.

## Task lifecycle and where each failure category strikes

```
PROVISIONING  ──→  PENDING  ──→  RUNNING  ──→  (DEACTIVATING)  ──→  STOPPED
     │                  │             │                │                  │
     │                  │             │                │                  │
  [A] ENI attach     [G] placement  [B] essential   [B'] draining      [B] stoppedReason
      subnet IP        capacity       container       deregistration    containers[].reason
      Service Linked   AZ constraint    exit           delay
      Role missing     attribute
      [F] image pull   constraint
                       (instance
                        capacity)
                       [F] image pull
                        (manifest)
                                                                     
                              ↓
                       [D] health check
                           ALB target unhealthy
                           ECS healthCheck failing
                           grace period too short
                                                                     
                              ↓
                       [E] crash loop
                           (repeated B/D)
                           app error in logs
```

The category letters map to the steps in SKILL.md:

- A = PROVISIONING_STUCK (Step 2)
- B = ESSENTIAL_CONTAINER_EXIT (Step 3)
- C = OOM (Step 4)
- D = HEALTH_CHECK (Step 5)
- E = CRASH_LOOP (Step 6)
- F = IMAGE_PULL (Step 7)
- G = PLACEMENT (Step 8)

**Rule:** pick the EARLIEST transition failure as the root cause. Later
categories are consequences. A task that fails image pull never gets to
RUNNING, so a health-check diagnosis is wrong.

## Category A: PROVISIONING_STUCK

A task in PROVISIONING has not yet been assigned compute or attached
networking. Failure here is platform-side.

### Worked example — Fargate ENI subnet IP exhaustion

**Symptom:** Task in PROVISIONING for 3+ minutes, then STOPPED with
`stoppedReason: "Timeout waiting for network interface"`.

**Walk:**

1. `describe-tasks.attachments` shows an ENI attachment in `ATTACHING`
   state that never transitions to `ATTACHED`.
2. `aws ec2 describe-subnets --subnet-ids <subnet>` shows
   `AvailableIpAddressCount: 2`.
3. Other Fargate services in the same subnet also failing — confirms
   capacity issue, not configuration.

**Root cause:** subnet IP exhaustion (catalog #1).

**Fix:** add subnets to the service's
`networkConfiguration.awsvpcConfiguration.subnets`, OR clean up
orphaned ENIs:

```bash
aws ec2 describe-network-interfaces \
  --filters Name=subnet-id,Values=<subnet-id> Name=status,Values=available \
  --query 'NetworkInterfaces[*].{id:NetworkInterfaceId,desc:Description}'
# Review and delete orphans:
aws ec2 delete-network-interface --network-interface-id <eni-id>
```

### Worked example — EC2 launch type capacity

**Symptom:** EC2 launch type task in PENDING forever. Service events
show "was unable to place a task."

**Walk:**

1. `aws ecs list-container-instances --cluster <cluster>` returns 3
   instances.
2. `describe-container-instances` for each: instance A has
   `remainingResources.cpu: 1024, memory: 1024` but the task wants
   2048 CPU. Instance B and C are at 0 remaining.
3. No instance can fit the task.

**Root cause:** PLACEMENT — insufficient registered CPU (catalog #8).

**Fix:** scale out the ASG behind the capacity provider, OR reduce the
task definition CPU requirement.

## Category B: ESSENTIAL_CONTAINER_EXIT

A task reached RUNNING and then transitioned to STOPPED because an
essential container exited. The exit code is the diagnostic.

### Worked example — Secret injection failure (exit code 1 quickly)

**Symptom:** Task RUNNING for 2 seconds, then STOPPED. Exit code 1.
CloudWatch Logs has one line: `ResourceInitializationError: unable to
retrieve secrets`.

**Walk:**

1. `describe-task-definition` shows a `secrets` entry referencing
   `arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf`.
2. The execution role's identity policy does NOT include
   `secretsmanager:GetSecretValue` on the secret ARN.
3. CloudTrail shows an `AccessDenied` event for
   `secretsmanager:GetSecretValue` at task start time.

**Root cause:** ESSENTIAL_CONTAINER_EXIT — secret injection failed
because the execution role lacks the GetSecretValue permission.

**Fix:** add a statement to the execution role identity policy:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-*"
}
```

For SSM SecureString references, also add `kms:Decrypt` on the key ARN
used to encrypt the parameter.

### Worked example — Application crash on missing env var

**Symptom:** Task RUNNING for 5 seconds, then STOPPED. Exit code 1.
CloudWatch Logs shows:

```
Traceback (most recent call last):
  File "app.py", line 12, in <module>
    db_host = os.environ["DB_HOST"]
  File "/usr/lib/python3.10/os.py", line 680, in __getitem__
    raise KeyError(key) from None
KeyError: 'DB_HOST'
```

**Root cause:** ESSENTIAL_CONTAINER_EXIT — missing environment variable
(catalog #3).

**Fix:** add `DB_HOST` to the container's `environment` array in the
task definition, OR to the `secrets` array if it is sensitive.

## Category C: OOM

Container exceeded its memory hard limit and was OOM-killed.

### Worked example — Java JVM heap larger than container memory

**Symptom:** Java application container exits with code 137.
`containers[].reason: "OOMKilled"`. Container was running for ~2 hours.

**Walk:**

1. `describe-task-definition` shows `memory: 1024` (1 GB).
2. The container image runs with `java -Xmx2g ...` — heap is set to 2
   GB, twice the container limit.
3. CloudWatch Container Insights shows memory utilisation at ~100% at
   the crash.

**Root cause:** OOM — JVM heap larger than container memory limit
(catalog #4).

**Fix:** either raise container `memory` to 3072 (gives headroom for
non-heap JVM memory), OR set `-XX:MaxRAMPercentage=75` to bound the
heap to 75% of the container limit. The MaxRAMPercentage approach is
preferred because it adapts automatically when the limit changes.

### Worked example — Host OOM on EC2

**Symptom:** EC2 launch type. Multiple co-located containers on the
same host all stop simultaneously. None of them has a container-level
`memory` set.

**Walk:**

1. `describe-task-definition` for each running task on the host:
   none has `memory` (hard limit) — only `memoryReservation` (soft
   limit).
2. The host's total memory is exhausted. The Linux OOM killer picks a
   victim, often the ECS agent itself, which then loses track of all
   tasks.

**Root cause:** Host OOM — no container-level hard memory limits
(catalog #4 variant).

**Fix:** set `memory` (hard limit) on every container. The Docker
cgroup prevents any single container from consuming host memory beyond
its limit.

## Category D: HEALTH_CHECK

Task is RUNNING but the ALB target group marks it unhealthy. ECS
eventually stops the task.

### Worked example — Path mismatch

**Symptom:** Target group health checks fail. Tasks RUNNING for ~90
seconds then STOPPED.

**Walk:**

1. `describe-target-groups`: `HealthCheckPath: /healthz`,
   `HealthCheckPort: "traffic-port"`, `HealthCheckProtocol: "HTTP"`.
2. `describe-task-definition`: container port mapping 8080→8080.
3. CloudWatch Logs: GET requests to `/healthz` return 404. Application
   defines the health endpoint at `/api/health`.
4. ECS Exec into the container: `curl -i http://localhost:8080/api/health`
   returns 200 OK.

**Root cause:** HEALTH_CHECK — ALB health check path mismatch (catalog
#5).

**Fix:** update the target group:

```bash
aws elbv2 modify-target-group --target-group-arn <tg-arn> \
  --health-check-path /api/health
```

### Worked example — Security group rule missing

**Symptom:** Target group marks targets `unhealthy` with `description:
"Request timed out"`. Application logs show no incoming requests at all.

**Walk:**

1. `describe-target-groups`: path `/api/health` is correct.
2. ECS Exec into container: `curl` from inside returns 200 — the app
   is healthy.
3. `describe-network-interfaces` for the task ENI: attached security
   group does NOT have an inbound rule allowing port 8080 from the
   ALB's security group.
4. The ALB health check probe never reaches the container.

**Root cause:** HEALTH_CHECK — security group rule missing.

**Fix:** add an inbound rule to the task security group:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <task-sg> --protocol tcp --port 8080 \
  --source-security-group-id <alb-sg>
```

### Worked example — Grace period too short

**Symptom:** Tasks RUNNING for 30 seconds, then STOPPED. Target group
shows targets transitioning healthy → unhealthy just before the task is
stopped.

**Walk:**

1. `describe-services`: `healthCheckGracePeriodSeconds: 30`.
2. The Spring Boot application takes ~75 seconds to start (visible in
   CloudWatch Logs from the first startup line to the "ready" line).
3. The ALB health check has `healthyThreshold: 3` and
   `interval: 10` — needs 30 seconds of healthy responses to mark a
   target healthy. The application is not even ready to respond until
   75 seconds.

**Root cause:** HEALTH_CHECK — grace period too short (catalog #6).

**Fix:** raise the grace period to 120 seconds:

```bash
aws ecs update-service --cluster <cluster> --service <service> \
  --health-check-grace-period-seconds 120
```

## Category E: CRASH_LOOP

Repeated RUNNING → STOPPED cycles with the same exit code.

### Worked example — Database dependency outage

**Symptom:** Service crash-looping. Exit code 1. Logs show
`ConnectionRefusedError: could not connect to database`.

**Walk:**

1. `describe-services` events show alternating "started a task" and
   "stopped a task" every ~30 seconds.
2. CloudWatch Logs: each instance has the same connection error.
3. The database endpoint is offline (verified separately).

**Root cause:** CRASH_LOOP — dependency outage.

**Fix:** restore the database, OR add retry/backoff in the application
to survive transient dependency failures.

### Worked example — Deployment version mismatch

**Symptom:** New deployment immediately crash-loops. Previous
deployment was stable.

**Walk:**

1. New task definition revision uses image tag `v2.3.1`. Previous used
   `v2.3.0`.
2. Logs show `ImportError: cannot import name 'BaseModel' from 'pydantic'`
   — a dependency was upgraded in v2.3.1 and broke the application.
3. The deployment circuit breaker opened and rolled back to v2.3.0.
4. Operator thought the rollback was the cause; the rollback is the
   consequence.

**Root cause:** CRASH_LOOP — version mismatch (the rollback is correct
behaviour).

**Fix:** fix the application code to be compatible with the new
dependency, OR pin the dependency in the Dockerfile.

## Category F: IMAGE_PULL

The container image cannot be pulled before the container starts.

### Worked example — Execution role missing ECR permissions

**Symptom:** Task STOPPED with `stoppedReason:
"Essential container in task exited"` and `containers[].reason:
"CannotPullContainerError: inspect image has been retried 5 times"`.

**Walk:**

1. `describe-task-definition`: image at
   `111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1`.
2. Execution role attached policies: only `AmazonECSTaskExecutionRolePolicy`
   (which DOES include ECR permissions) — wait, actually the policy is
   a stripped inline policy without ECR actions.
3. `aws iam simulate-principal-policy` for the execution role against
   `ecr:BatchGetImage` returns `implicitDeny`.

**Root cause:** IMAGE_PULL — execution role missing ECR permissions
(catalog #2).

**Fix:** attach `AmazonEC2ContainerRegistryReadOnly` managed policy to
the execution role.

### Worked example — ECR lifecycle policy deleted image

**Symptom:** Tasks that worked yesterday fail to start today. Same
task definition, no changes. `containers[].reason:
"CannotPullContainerError: manifest unknown"`.

**Walk:**

1. `describe-task-definition`: image tag `app:latest`.
2. `aws ecr describe-images --repository-name app --image-ids imageTag=latest`
   returns the image — so the tag exists.
3. BUT: `aws ecr describe-images` shows the image's `imagePushedAt` is
   yesterday. The task definition references `latest`, which now points
   to a new image built this morning.
4. The new image was built with a different base layer that the running
   ECS agent version cannot pull.

**Root cause:** IMAGE_PULL — image overwritten (tag immutability off).

**Fix:** enable tag immutability on the ECR repo; reference images by
digest (`app@sha256:...`) instead of tag.

### Worked example — Cross-account ECR repo policy

**Symptom:** Task in account 111111111111 pulls from ECR in account
222222222222. AccessDenied on image pull.

**Walk:**

1. Execution role in account 111111111111 has ECR permissions on
   `arn:aws:ecr:us-east-1:222222222222:repository/app` — identity
   policy OK.
2. ECR repo policy in account 222222222222 does NOT include
   `arn:aws:iam::111111111111:root` in `Principal`.
3. Cross-account intersection rule (same as IAM): BOTH the identity
   policy AND the repo policy must allow.

**Root cause:** IMAGE_PULL — cross-account ECR repo policy missing
caller.

**Fix:** update the repo policy in account 222222222222:

```bash
aws ecr set-repository-policy --repository-name app \
  --policy-text file://policy.json --profile acct222
```

Where `policy.json` includes:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CrossAccountPull",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::111111111111:root" },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
    }
  ]
}
```

## Category G: PLACEMENT

The scheduler cannot match the task definition's requirements to
available capacity.

### Worked example — Attribute constraint missing

**Symptom:** Service events show `"was unable to place a task ... no
container instances met the requirements"`.

**Walk:**

1. `describe-task-definition`: requires
   `requiresCompatibilities: ["EC2"]`, no special attributes.
2. The task definition includes a `runtimePlatform.cpuArchitecture: "ARM64"`.
3. `describe-container-instances`: all instances advertise only
   `ecs.capability.cpu.architecture.x86_64`. None advertises ARM64.
4. No instance matches the architecture requirement.

**Root cause:** PLACEMENT — attribute constraint (CPU architecture)
not satisfied.

**Fix:** add Graviton (ARM64) instances to the cluster, OR change the
task definition to `X86_64` if ARM is not required.

### Worked example — Capacity provider scaling lag

**Symptom:** Sudden burst of desired tasks. Service events show
placement failures. After a few minutes, tasks succeed.

**Walk:**

1. `describe-capacity-providers`: capacity provider is healthy and
   `managedScalingStatus: ENABLED`.
2. The ASG behind the capacity provider is at 2 instances; the desired
   task count needs 4 instances worth of capacity.
3. The capacity provider triggered scale-out 90 seconds ago — new
   instances take 60-120 seconds to register.

**Root cause:** PLACEMENT — capacity provider scaling lag (transient).

**Fix:** pre-warm with scheduled scaling for known spikes, OR add
capacity provider reservation capacity.

## Cross-category decision flowchart

```
START
  │
  ▼
Task stuck in PROVISIONING > 2 min?
  ├── YES ──→ Category A (PROVISIONING_STUCK)
  │            ├── ENI attachment failing → subnet IP / SLR
  │            ├── Capacity missing → Category G
  │            └── EBS attachment failing → AZ capacity
  │
  ▼ NO
describe-services events show "unable to place"?
  ├── YES ──→ Category G (PLACEMENT)
  │            ├── Insufficient CPU/memory → scale out
  │            ├── Attribute constraint → instance type
  │            └── AZ constraint → add subnets
  │
  ▼ NO
Task STOPPED, stoppedReason mentions "CannotPull"?
  ├── YES ──→ Category F (IMAGE_PULL)
  │            ├── Auth error → execution role ECR perms
  │            ├── Manifest unknown → tag immutability
  │            ├── Cross-account → repo policy
  │            └── Network → VPC endpoint / NAT
  │
  ▼ NO
Task STOPPED, containers[].exitCode present?
  ├── 137 / OOMKilled ──→ Category C (OOM)
  ├── 1 + ResourceInitializationError → secret injection
  ├── 1 + application traceback → Category B / E
  └── 0 → app thinks it is done; essential flag review
  │
  ▼
Task RUNNING but target group unhealthy?
  ├── YES ──→ Category D (HEALTH_CHECK)
  │            ├── Path mismatch → catalog #5
  │            ├── SG rule missing
  │            └── Grace period too short → catalog #6
  │
  ▼
Repeated STOPPED cycles with same exit code?
  ├── YES ──→ Category E (CRASH_LOOP)
  │            └── Read CloudWatch Logs for root cause
  │
  ▼
NEED_MORE_INFO — gather more context
```

## Common diagnostic shortcuts

- If the task is on Fargate and never leaves PROVISIONING, suspect
  subnet IP exhaustion first.
- If the task is on Fargate and fails within 2 seconds of RUNNING,
  suspect secret injection or missing env var.
- If the task worked yesterday and fails today with no change, suspect
  an image purge (ECR lifecycle policy) or a dependency outage.
- If the target group is `unhealthy` but the application is fine,
  suspect security group or path mismatch.
- If a deployment rollback happened, the rollback is correct behaviour
  — find the underlying task failure.
- If only some tasks in a service fail, suspect capacity or AZ
  constraints affecting only some instances.
- If all tasks in a service fail simultaneously, suspect a config
  change in the task definition or service.
