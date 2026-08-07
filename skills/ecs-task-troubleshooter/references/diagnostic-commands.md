# ECS Diagnostic Commands — Reference

Supplementary reference for the ECS Task Troubleshooter skill. The
canonical command script per failure category, with sample outputs and
interpretation notes.

## Universal first commands (run for any ECS failure)

```bash
# 1. Identify the failing task(s) in the service.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{desired:desiredCount,running:runningCount,events:events[:10],deployments:deployments[*].{status:status,running:runningCount,desired:desiredCount,failed:failedTasks,rollout:rolloutState}}'

# 2. Find recently stopped tasks.
aws ecs list-tasks --cluster <cluster> --service-name <service> \
  --desired-status STOPPED --max-items 5

# 3. Find currently running tasks (for PROVISIONING / HEALTH_CHECK).
aws ecs list-tasks --cluster <cluster> --service-name <service> \
  --desired-status RUNNING --max-items 5
```

The events list is the fastest triage signal. Look for patterns:

- `"has started" / "has stopped"` alternating — crash loop or essential
  container exit.
- `"was unable to place a task"` — placement failure.
- `"circuit breaker triggered"` — deployment rollback (look at
  underlying task failure for the real cause).
- `"deregistered"` — task is in the deregistration / draining window.

## Per-category command scripts

### Category A: PROVISIONING_STUCK

```bash
# Read task attachments to identify the failing ENI or volume.
aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].{status:lastStatus,stoppedReason:stoppedReason,attachments:attachments[*].{type:type,status:status,reason:reason,subnets:details[?name==`subnetId`].value,eni:details[?name==`networkInterfaceId`].value}}'

# Check subnet available IPs (Fargate awsvpc mode).
aws ec2 describe-subnets --subnet-ids <subnet-id> \
  --query 'Subnets[*].{id:SubnetId,available:AvailableIpAddressCount,cidr:CidrBlock,az:AvailabilityZone}'

# Verify the ECS service-linked role exists.
aws iam get-role --role-name AWSServiceRoleForECS \
  --query 'Role.Arn'

# List orphaned ENIs in the subnet (status: available).
aws ec2 describe-network-interfaces \
  --filters Name=subnet-id,Values=<subnet-id> Name=status,Values=available \
  --query 'NetworkInterfaces[*].{id:NetworkInterfaceId,desc:Description,time:Attachment.Time}'
```

**Interpretation:** if `AvailableIpAddressCount` is below 5, the subnet
is critically low. If `AWSServiceRoleForECS` is missing, ENI creation
will fail across the whole account.

### Category B: ESSENTIAL_CONTAINER_EXIT

```bash
# Read container exit codes and reasons.
aws ecs describe-tasks --cluster <cluster> --tasks <arn> \
  --query 'tasks[0].{stoppedReason:stoppedReason,startedAt:startedAt,stoppedAt:stoppedAt,containers:containers[*].{name:name,exitCode:exitCode,reason:reason,lastStatus:lastStatus}}'

# Pull the application logs for the failing container.
# Use describe-tasks to get the task ID (last segment of the ARN).
aws logs get-log-events \
  --log-group-name /ecs/<family> \
  --log-stream-name "ecs/<container-name>/<task-id>" \
  --start-time $(($(date +%s) * 1000 - 60000)) \
  --limit 100

# If logs are missing, verify the log group exists and the execution
# role has logs:CreateLogStream and logs:PutLogEvents.
aws logs describe-log-groups \
  --log-group-name-prefix /ecs/<family>

aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<execution-role> \
  --action-names logs:CreateLogStream logs:PutLogEvents
```

**Interpretation:** the exit code narrows the cause. Exit 1 with no
logs suggests the container crashed before the log driver was
configured (rare) or the log group does not exist. Exit 137 = OOM.
Exit 0 = clean exit.

### Category C: OOM

```bash
# Read the task definition memory limits.
aws ecs describe-task-definition --task-definition <family:revision> \
  --query 'taskDefinition.{cpu:cpu,memory:memory,launchType:compatibilities,containers:containerDefinitions[*].{name:name,memory:memory,memoryReservation:memoryReservation}}'

# Check container Insights for memory utilisation trends.
aws logs filter-log-events \
  --log-group-name /aws/ecs/containerinsights/<cluster>/performance \
  --filter-pattern "MemoryUtilization" \
  --start-time $(($(date +%s) * 1000 - 86400000)) \
  --limit 50

# Or query CloudWatch metrics directly.
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Maximum \
  --output json
```

**Interpretation:** if `MemoryUtilization` trends toward 100% before
each crash, the container is leaking or undersized. Compare the peak
utilisation to the configured `memory` limit.

### Category D: HEALTH_CHECK

```bash
# Read the target group config.
aws elbv2 describe-target-groups --load-balancer-arn <alb-arn> \
  --query 'TargetGroups[*].{name:TargetGroupName,arn:TargetGroupArn,type:TargetType,path:HealthCheckPath,port:HealthCheckPort,protocol:HealthCheckProtocol,interval:HealthCheckIntervalSeconds,timeout:HealthCheckTimeoutSeconds,healthy:HealthyThresholdCount,unhealthy:UnhealthyThresholdCount}'

# Read per-target health (the Description field has the failure reason).
aws elbv2 describe-target-health --target-group-arn <tg-arn> \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,port:Target.Port,state:TargetHealth.State,reason:TargetHealth.Reason,desc:TargetHealth.Description}'

# Read the service's grace period.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{grace:healthCheckGracePeriodSeconds,lb:loadBalancers}'

# Read the task definition's health check (separate from ALB).
aws ecs describe-task-definition --task-definition <family:revision> \
  --query 'taskDefinition.containerDefinitions[*].{name:name,health:healthCheck}'

# Verify the security group rules on the task ENI (awsvpc mode).
aws ec2 describe-security-groups --group-ids <task-sg> \
  --query 'SecurityGroups[*].{inbound:IpPermissions,outbound:IpPermissionsEgress}'

# Shell into the container and curl the health endpoint directly.
aws ecs execute-command --cluster <cluster> --task <arn> \
  --container <container> --command "curl -i http://localhost:<port><path>" \
  --interactive
```

**Interpretation:** `describe-target-health` TargetHealth.Reason
values:

- `Elb.RegistrationInProgress` — target still registering.
- `Target.ResponseCodeMismatch` — application returned a non-200
  status code.
- `Target.Timeout` — request timed out (security group, port mapping,
  or app hanging).
- `Target.FailedHealthCheck` — app did not respond to the configured
  path/port.

### Category E: CRASH_LOOP

```bash
# Read the deployment circuit breaker state.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{circuit:deploymentConfiguration.deploymentCircuitBreaker,rollback:deploymentConfiguration.rollback,deployments:deployments[*].{status:status,running:runningCount,desired:desiredCount,failed:failedTasks,rollout:rolloutState,createdAt:createdAt}}'

# Filter logs for error patterns in the last 10 minutes.
aws logs filter-log-events \
  --log-group-name /ecs/<family> \
  --filter-pattern "ERROR Exception Traceback Fatal Panic ConnectionRefused" \
  --start-time $(($(date +%s) * 1000 - 600000)) \
  --limit 50

# Read the latest task definition revision vs the previous.
aws ecs describe-task-definition --task-definition <family:latest>
aws ecs describe-task-definition --task-definition <family:<latest-1>>
```

**Interpretation:** if `failedTasks` is high and `rolloutState` is
`ROLLED_BACK`, the circuit breaker has fired. Find the failing
revision and fix it; the service is now running the previous revision.

### Category F: IMAGE_PULL

```bash
# Verify the image exists in ECR.
aws ecr describe-images --repository-name <repo> \
  --image-ids imageTag=<tag>

aws ecr list-images --repository-name <repo> \
  --filter tagStatus=TAGGED

# Read the repo policy (cross-account pulls).
aws ecr get-repository-policy --repository-name <repo>

# Read the lifecycle policy (image purges).
aws ecr get-lifecycle-policy --repository-name <repo>

# Simulate the execution role's ECR permissions.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<execution-role> \
  --action-names ecr:GetAuthorizationToken ecr:BatchCheckLayerAvailability \
                  ecr:GetDownloadUrlForLayer ecr:BatchGetImage \
  --resource-arns arn:aws:ecr:<region>:<account>:repository/<repo>

# Verify VPC endpoints for ECR (for tasks in private subnets).
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.<region>.ecr.api \
                     com.amazonaws.<region>.ecr.dkr \
  --query 'VpcEndpoints[*].{id:VpcEndpointId,service:ServiceName,state:State,subnets:SubnetIds}'
```

**Interpretation:**

- `manifest unknown` → image tag does not exist or was purged.
- `RequestError` → network issue (NAT or VPC endpoint missing).
- `AccessDenied` for `ecr:BatchGetImage` → execution role policy
  missing.
- Cross-account pull works from CLI in account A but fails in ECS →
  repo policy in account B does not include account A.

### Category G: PLACEMENT

```bash
# List container instances registered to the cluster.
aws ecs list-container-instances --cluster <cluster>

# Read each instance's registered and remaining resources + attributes.
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <ci-1> <ci-2> ... \
  --query 'containerInstances[*].{id:containerInstanceArn,status:status,agent:agentConnected,registered:registeredResources,remaining:remainingResources,attributes:attributes,running:runningTasksCount}'

# Read the capacity provider configuration.
aws ecs describe-capacity-providers --cluster <cluster>

# Read the service's capacity provider strategy and placement.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{placement:placementConstraints,strategy:placementStrategy,capacity:capacityProviderStrategy,azs:availabilityZones}'
```

**Interpretation:**

- `remainingResources.cpu` / `memory` for each instance — sum these
  against the task definition's request. If no instance fits, the
  placement fails.
- `attributes` includes capability flags like
  `ecs.capability.execution-role-awslogs`, `ecs.capability.gpu`,
  `ecs.capability.cpu.architecture.arm64`. Missing attributes cause
  `"unsatisfiable: attribute ..."` errors.
- `agentConnected: false` → the ECS agent on the host is unhealthy;
  the scheduler will not place new tasks on that instance.

## Combining signals

The richest single response is `describe-tasks` for a stopped task.
It surfaces:

- `stoppedReason` — task-level (often generic).
- `containers[].reason` — per-container (often specific).
- `containers[].exitCode` — exit code (137 = OOM, 1 = app error, 0 =
  clean exit).
- `attachments[].status` and `reason` — for ENI/EBS attachment
  failures.
- `healthStatus` — UNHEALTHY / HEALTHY / UNKNOWN at the task level.
- `startedAt` and `stoppedAt` — timing reveals drain-killed tasks.

Always start with `describe-tasks`. The category letter (A-G) follows
from the fields it surfaces.

## Output verification commands

After applying a fix:

```bash
# For task definition changes: run a one-off task before updating the service.
aws ecs run-task --cluster <cluster> \
  --task-definition <family:new-revision> \
  --count 1 --launch-type <FARGATE|EC2> \
  --network-configuration awsvpcConfiguration=...

# For service config changes: monitor the deployment.
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].deployments[*].{status:status,running:runningCount,desired:desiredCount,rollout:rolloutState}'

# For health check fixes: watch target health.
aws elbv2 describe-target-health --target-group-arn <tg-arn>

# For capacity fixes: watch container instance registration.
aws ecs describe-container-instances --cluster <cluster> \
  --container-instances <new-ci> \
  --query 'containerInstances[*].{status:status,agent:agentConnected,remaining:remainingResources}'
```
