# Networking and Scaling Guide — ECS Fargate Deployer

Deep reference on Fargate awsvpc networking, ALB integration,
target-tracking auto-scaling, and the Fargate Spot capacity provider
strategy.

## 1. awsvpc networking for Fargate

Fargate REQUIRES `networkMode: awsvpc`. Each task gets a dedicated
primary ENI with a private IP from the subnet CIDR.

### 1.1 ENI lifecycle

- **Task start:** ECS provisions an ENI in one of the specified subnets.
  The ENI is tagged `aws:ecs:taskDefinition` / `aws:ecs:cluster` for
  tracking. ENI creation takes 5-15 seconds.
- **Task run:** the ENI stays attached for the task's lifetime. Fargate
  also attaches a "branch" ENI if the task uses Elastic Inference.
- **Task stop:** ECS detaches and deletes the ENI. Detach takes 10-30
  seconds.

The ENI's security group IS the task's security group. Inbound rules
on the task SG control what can reach the task; outbound rules control
what the task can reach.

### 1.2 Subnet selection

ECS balances tasks across the specified subnets. To pin tasks to
specific AZs, pass only subnets in those AZs. To balance across 3 AZs,
pass 3 subnets (one per AZ) and set `desiredCount >= 3`.

```bash
--network-configuration awsvpcConfiguration={subnets=[subnet-us-east-1a,subnet-us-east-1b,subnet-us-east-1c],securityGroups=[sg-xxx],assignPublicIp=DISABLED}
```

For HA, NEVER put all tasks in one subnet — a single AZ outage takes
down the service.

### 1.3 NAT Gateway vs. VPC endpoints

Private subnets have no direct internet route. Two ways for Fargate
tasks to reach AWS services:

**NAT Gateway** (general internet route):
- Routes all `0.0.0.0/0` traffic through a NAT Gateway in a public
  subnet.
- Charged per-hour (~$0.045/hr) + per-GB data processing (~$0.045/GB).
- Works for any external endpoint (Stripe, GitHub, public APIs).
- Required if the task calls non-AWS external services.

**VPC endpoints** (cheaper, AWS-only):
- Gateway endpoints (S3, DynamoDB): free, route via the VPC's route
  table.
- Interface endpoints (everything else): per-hour per-AZ charge
  (~$0.010/hr/AZ) + per-GB data processing (~$0.010/GB).
- Cheaper than NAT Gateway for high-volume AWS service traffic.
- No internet exposure.

**Rule of thumb:** use Gateway endpoints for S3/DynamoDB always. Use
Interface endpoints for ECR, STS, Secrets Manager, SSM, CloudWatch
Logs. Use a NAT Gateway for non-AWS external traffic. Combine both
for production.

### 1.4 assignPublicIp

- `DISABLED` (production default): task gets a private IP only. Use
  with private subnets + NAT Gateway or VPC endpoints.
- `ENABLED`: task gets a public IP from the subnet's pool. Use with
  public subnets + IGW for tasks that need direct internet (rare).
  NEVER use `ENABLED` with private subnets — the task cannot reach
  the internet (private subnet has no IGW route).

## 2. ALB integration

### 2.1 target_type=ip is mandatory

Fargate tasks register with the ALB by their ENI private IP, not an
instance ID. The target group MUST be `target_type=ip`. Using
`target_type=instance` silently fails target registration — the ALB
marks all targets as `unused`.

### 2.2 Health check alignment

The ALB health check and the container health check should align:

| Field | ALB health check | Container healthCheck |
|---|---|---|
| Path | `/healthz` | `curl -f http://localhost:8080/healthz` |
| Interval | 30s | 30s |
| Timeout | 5s | 5s |
| Healthy threshold | 2 | 2 (implicit via retries) |
| Unhealthy threshold | 3 | 3 |

If they diverge, ECS may consider a task healthy (container check
passes) while the ALB considers it unhealthy (ALB check fails), or
vice versa. Either way, traffic routing breaks.

### 2.3 Listener rules

```bash
aws elbv2 create-listener-rule \
  --listener-arn <listener> \
  --priority 10 \
  --conditions Field=path-pattern,Values=["/payments/*"] \
  --actions Type=forward,TargetGroupArn=<tg-arn>
```

- Each rule has a unique priority (1-50000). Lower = higher priority.
- The default action (priority = `DEFAULT`) on the listener forwards
  unmatched traffic — usually to a "catch-all" target group.
- Use `host-header` conditions for virtual-host routing
  (`payments.example.com`).
- Use weighted target groups for blue/green deployments (CodeDeploy).

### 2.4 Deregistration delay

When a task is deregistered, the ALB waits `deregistration_delay`
(default 300s) before removing it. Set to 30-60s for fast deployments
(after verifying the app drains in-flight requests gracefully).

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=deregistration_delay.timeout_seconds,Value=60
```

## 3. Target-tracking auto-scaling

### 3.1 How it works

Target tracking maintains a metric at a target value by adjusting
`desiredCount`. ECS publishes the metric every minute; Application
Auto Scaling evaluates every 60 seconds.

- If `metric > target`, scale OUT by `desiredCount + step`.
- If `metric < target * (1 - cool-down-buffer)`, scale IN.

### 3.2 Built-in metrics

| PredefinedMetricType | What it measures | Use when |
|---|---|---|
| `ECSServiceAverageCPUUtilization` | Average CPU across all tasks | CPU-bound workloads |
| `ECSServiceAverageMemoryUtilization` | Average memory | Memory-bound (JVM) |
| `ALBRequestCountPerTarget` | Requests per target per minute | HTTP traffic |

For `ALBRequestCountPerTarget`, set `ResourceLabel`:

```json
"PredefinedMetricSpecification": {
  "PredefinedMetricType": "ALBRequestCountPerTarget",
  "ResourceLabel": "app/<alb-name>/<alb-id>/<tg-name>/<tg-id>"
}
```

### 3.3 Custom metrics

Use a CloudWatch metric (e.g., SQS `ApproximateNumberOfMessagesVisible`)
via a step scaling policy + CloudWatch alarm, or a custom metric stream.

For SQS queue depth, the canonical pattern is `messages per task`:

```
messages_per_task = queue_depth / desiredCount
```

Scale out when `messages_per_task > threshold` (e.g., 10). This scales
with backlog depth, not just queue depth.

### 3.4 Cooldowns

- `ScaleOutCooldown`: 60s (respond to spikes fast).
- `ScaleInCooldown`: 300s (avoid flapping).
- NEVER set `ScaleInCooldown < 300s` — sub-300s scale-in causes tasks
  to scale in then immediately scale back out.

### 3.5 Min/Max capacity

- `min-capacity`: floor (e.g., 3 for HA across 3 AZs).
- `max-capacity`: ceiling (e.g., 12, set based on cost budget and
  downstream capacity).

A 1-task service cannot be HA. Set `min-capacity >= AZ count`.

## 4. Fargate Spot capacity provider strategy

### 4.1 Spot interruption

Fargate Spot tasks receive a 2-minute interruption notice via:
- EventBridge event `AWS Fargate Spot Interruption Warning`.
- Task metadata endpoint `v2/task/metadata` `StopCode=TerminationNotice`.

When the notice fires:
1. ECS sends SIGTERM to the container's PID 1.
2. The container has `stopTimeout` seconds (max 120) to drain.
3. ECS drains the ALB target (waits `deregistration_delay`).
4. The task is replaced on another capacity provider.

### 4.2 Strategy

```bash
--capacity-provider-strategy \
  capacityProvider=FARGATE,weight=4,base=2 \
  capacityProvider=FARGATE_SPOT,weight=1
```

- `base=2`: first 2 tasks run on FARGATE (HA floor).
- `weight=4` (FARGATE) / `weight=1` (FARGATE_SPOT): after the base,
  tasks split 4:1.

This gives ~20% Spot capacity, balancing cost savings with HA. For
more aggressive Spot use, set weight=1/1 (50/50); for purely
stateless burst, omit the base and use FARGATE_SPOT only.

### 4.3 NEVER use Spot for

- Stateful workloads (databases, in-memory session stores).
- Single-tenant compliance workloads (PCI, HIPAA).
- Long-running jobs that cannot recover from interruption (e.g., a
  2-hour batch job started 1:55 ago).

Spot is fine for stateless HTTP services, queue consumers, and
embarrassingly-parallel batch jobs.

## 5. Service Connect and Cloud Map

For service-to-service discovery:

- **Service Connect** (built-in, 2023+): built into ECS, no extra
  service. Adds a per-task sidecar (envoy-based) that handles
  discovery + retry + traffic policy. Enable via
  `serviceConnectConfiguration` on the service.
- **Cloud Map** (older): a separate service (`servicediscovery:*`).
  Creates a DNS record per task. Works with any client (not just
  ECS).

Both require a namespace to exist before service creation:

```bash
aws servicediscovery create-private-dns-namespace \
  --name payments.internal \
  --vpc vpc-xxx
```

## 6. ECS Exec

```bash
aws ecs update-service \
  --cluster <cluster> \
  --service <service> \
  --enable-execute-command

# Then shell in
aws ecs execute-command \
  --cluster <cluster> \
  --task <task-id> \
  --container app \
  --command "/bin/sh" \
  --interactive
```

**Task role needs:**

```json
{
  "Effect": "Allow",
  "Action": [
    "ssmmessages:CreateControlChannel",
    "ssmmessages:CreateDataChannel",
    "ssmmessages:OpenControlChannel",
    "ssmmessages:OpenDataChannel"
  ],
  "Resource": "*"
}
```

NEVER enable in production without a change ticket — `execute-command`
bypasses bastion auditing. CloudTrail logs the session, but session
contents are not recorded by default.

## Full NEVER list (anti-patterns)

- NEVER use `:latest` image tag in production. It is mutable — a new push
  silently changes what runs. Pin to a version tag or SHA digest. #1
  rollback-breaker.
- NEVER combine the execution role and task role into one. The execution
  role pulls images and writes logs; the task role is the application's
  identity. Combining produces pull failures or least-privilege violations.
- NEVER use a target group with `target_type=instance` for a Fargate
  service. Fargate tasks register by ENI private IP — only `target_type=ip`
  works. Silently fails registration.
- NEVER deploy Fargate tasks to a public subnet with
  `assignPublicIp=ENABLED` in production. Exposes the task directly to
  the internet. Use private subnets + NAT Gateway or VPC endpoints.
- NEVER deploy without the deployment circuit breaker when using a rolling
  deployment. Without `enable=true, rollback=true`, a bad task definition
  leaves the service degraded indefinitely.
- NEVER rely on the ALB health check alone. Always define a container
  health check for the circuit breaker and task lifecycle signal.
- NEVER set `minimumHealthyPercent=0` for a production service. Stops all
  old tasks before new ones start — downtime window every deployment.
- NEVER use `awslogs` log driver without pre-creating the log group. ECS
  does NOT auto-create log groups; first task fails with
  `ResourceNotFoundException`.
- NEVER reference Secrets Manager secrets in plaintext environment
  variables. Use the `secrets` array so they are injected at runtime.
- NEVER set `scaleInCooldown` below 300 seconds. Sub-300s causes flapping.
- NEVER use `DAEMON` scheduling strategy on Fargate. Only valid for EC2.
- NEVER use the legacy `launch-type` API with FARGATE_SPOT. Spot is a
  capacity provider, not a launch type.
- NEVER omit the `startPeriod` on slow-start containers (Java, .NET).
  Health check fires before app is ready → circuit breaker false rollback.
- NEVER deviate from the checklist output format. Substituting labels
  silently breaks downstream pipelines and evals.

## Edge-case handling (full detail)

- **Cross-account ECR pull.** Execution role in account A pulling from
  account B's ECR needs `ecr:BatchGetImage` on the cross-account repo AND
  the repository policy in B must grant A's root. `ecr:GetAuthorizationToken`
  is always against the calling account.

- **ECS Exec in production.** `enableExecuteCommand=true` allows shell
  access via `aws ecs execute-command`. Bypasses bastion auditing. Enable
  only for break-glass; require change ticket and CloudTrail alert.

- **ALB health check vs. container health check divergence.** If ALB
  passes but container check fails, ECS marks task unhealthy while ALB
  keeps sending traffic. Align path, interval, timeout of both checks.

- **Slow-start JVM tasks.** Java/Spring Boot can take 60-120s to start.
  Set `healthCheck.startPeriod=60` (or higher) and
  `unhealthyThresholdCount=3` to avoid spurious rollback.

- **Spot interruption drain.** Fargate Spot receives 2-minute warning, ECS
  sends `SIGTERM`. Set `stopTimeout=30` (max) for graceful shutdown.

- **Capacity provider vs. launch type.** Once a service uses a
  capacity-provider strategy, you cannot switch back to launch type
  without recreating the service.

- **Service Connect / Cloud Map.** For service-to-service discovery,
  enable Service Connect (built-in) or Cloud Map (external). Both require
  the namespace to exist before service creation.

- **Task placement constraints.** Fargate ignores most placement
  constraints (EC2-only). Use `spread=attribute:ecs.availability-zone`
  to balance across AZs.

## Expert heuristic (full detail)

**The 60/70 rule:** set CPU target tracking at 60% for latency-sensitive
services, 70% for batch. Leaves headroom before auto-scaling kicks in
(scale-out takes ~60-90s on Fargate — task startup + ALB health check).

**Memory: 2x the working set.** A JVM app with 2 GB heap needs at least
4 GB task memory. Set JVM heap via `-XX:MaxRAMPercentage=75`.

**AZ spread:** minimum 2 AZs for HA, 3 AZs for user-facing services. Pair
with `desiredCount >= AZ count` so a single AZ failure does not drop
capacity below 1.

**Fargate Spot blend:** `base=2` on FARGATE (HA floor) plus FARGATE_SPOT
weight 1-3 for burst. NEVER put stateful workloads on Spot.

**ALB vs. NLB:** ALB for HTTP/HTTPS (path routing, OIDC, WAF). NLB for
TCP/TLS (low latency, static IPs, preserved source IP). Target type must
be `ip` either way.

## Pre-flight safety checks (full detail with CLI)

```bash
# Confirm the cluster exists with the right capacity provider
aws ecs describe-clusters --clusters <cluster> --include ATTACHMENTS

# Confirm the ECR image exists
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>

# Confirm both roles exist and have the right trust policy
aws iam get-role --role-name <exec-role> --query 'Role.AssumeRolePolicyDocument'
aws iam get-role --role-name <task-role> --query 'Role.AssumeRolePolicyDocument'

# Confirm the target group is target_type=ip
aws elbv2 describe-target-groups --target-group-arns <arn> --query 'targetGroups[0].TargetType'

# Confirm subnets are private and span >= 2 AZs
aws ec2 describe-subnets --subnet-ids subnet-aaa subnet-bbb \
  --query 'Subnets[].{AZ:AvailabilityZone,Public:MapPublicIpOnLaunch}'

# Pre-create the CloudWatch log group with retention
aws logs create-log-group --log-group-name /ecs/<service>
aws logs put-retention-policy --log-group-name /ecs/<service> --retention-in-days 30

# For existing services, capture current config for rollback
aws ecs describe-services --cluster <cluster> --services <service> \
  --output json > /tmp/<service>-backup.json
```
