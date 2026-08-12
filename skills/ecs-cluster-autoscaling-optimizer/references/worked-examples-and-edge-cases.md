# Worked Examples, Edge Cases, and Extended Anti-Patterns — ECS Cluster Autoscaling Optimizer

Full worked examples, CLI failure handling, operational edge cases, and
the extended NEVER list. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — managed scaling migration + spot + binpack (headline)

```text
TARGET: ecs-prod-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster uses all on-demand capacity provider with spread
  placement. Average CPU utilization is 35% and 8 of 20 container
  instances have 0 running tasks (40% stranded). Managed scaling is
  disabled (legacy cluster-autoscaler). Switching to managed scaling +
  spot capacity provider (base on-demand=2, spot weight=4) + binpack
  placement reduces host count by 40% and captures 70% spot discount on
  burst capacity.
RECOMMENDATION:
  Current: all on-demand, managed scaling off, placement spread-by-host,
    cooldown 300 s, target tracking CPU=60%
  Proposed: on-demand base=2 + spot weight=4, managed scaling on,
    placement binpack-by-memory + spread-by-az, cooldown 120 s,
    target tracking CPU=65%
  Dimensions changed: cp_strategy + managed_scaling + placement_strategy +
    cooldown + bin_packing
  Dimensions checked: cp_strategy → (add spot)  managed_scaling → (enable)
    target_tracking ✓ (CPU correct for this workload)  cooldown →
    (300→120)  bin_packing → (enable)  fargate ✓ (EC2 needed for >4 vCPU)
    warmup ✓ (60 s configured)  drain ✓ (no issues)  desired_running_gap ✓
    (no stuck tasks)  placement_strategy → (spread→binpack)  scaling_mode ✓
    (target tracking appropriate)
  Confidence: HIGH — 40% empty hosts confirmed via
    describe-container-instances; workload is stateless microservices
    (burst-tolerant for spot); CPU < 40% confirms headroom for binpack.
ESTIMATED_IMPACT:
  Current host count: 20, avg utilization 35% CPU, 28% memory
  Projected host count: 12, avg utilization 58% CPU, 47% memory
  Host reduction: 8 (40%)
  Monthly savings: $2,120.00
    on-demand reduction: 8 hosts × 730 h × $0.384/h = $2,242.56
    spot hosts added: 2 spot × 730 h × $0.115/h = $167.84 (spot for burst)
    net: 8 on-demand removed - 2 spot added = $2,074.72 net saved
    (conservatively $2,120.00 with rounding for partial utilization)
  Assumptions: m5.2xlarge at $0.384/h on-demand, $0.115/h spot (us-east-1),
    target utilization 60% CPU, 70% spot discount.
MIGRATION_STEPS:
  1. Create spot capacity provider:
     aws ecs create-capacity-provider --name spot-cp \
       --auto-scaling-group-provider autoScalingGroupArn=<spot-asg-arn>,managedScaling.status=ENABLED,managedScaling.targetCapacity=100
  2. Update service with new strategy + binpack:
     aws ecs update-service --cluster ecs-prod-cluster --service api-service \
       --capacity-provider-strategy capacityProvider=on-demand-cp,weight=1,base=2 capacityProvider=spot-cp,weight=4,base=0 \
       --placement-strategy type=binpack,field=memory type=spread,field=attribute:ecs.availability-zone
  3. Enable managed scaling on the on-demand CP:
     aws ecs update-capacity-provider --name on-demand-cp \
       --auto-scaling-group-provider managedScaling.status=ENABLED,managedScaling.targetCapacity=100,instanceWarmupPeriod=60
  4. Update scale-in cooldown to 120 s.
  5. Monitor host count and empty instances for 7 days.
CONFIRM: About to update-service on ecs-prod-cluster (spread→binpack,
  add spot CP, enable managed scaling). Host reduction 40%; monthly
  savings $2,120. Proceed? (yes/no)
```

## Worked example — spot capacity provider addition

```text
TARGET: ecs-api-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster has all on-demand capacity (10 m5.xlarge instances)
  running stateless REST APIs. CPU at 35%. Workload is burst-tolerant
  (tasks complete in <500 ms). Adding spot capacity provider with
  on-demand base=2 + spot weight=4 captures 70% discount on burst
  capacity while maintaining 2 on-demand tasks as availability floor.
RECOMMENDATION:
  Current: on-demand only, base=1, weight=1
  Proposed: on-demand base=2 weight=1 + spot weight=4
  Dimensions changed: cp_strategy
  Dimensions checked: cp_strategy → (add spot)  managed_scaling ✓
    (already enabled)  target_tracking ✓  cooldown ✓  bin_packing ✓
    (already binpack)  fargate ✓  warmup ✓  drain ✓
    desired_running_gap ✓  placement_strategy ✓  scaling_mode ✓
  Confidence: HIGH — all 4 services are stateless REST APIs behind ALB
    with no long-lived connections; spot interruption handler drains
    tasks within 2-minute window.
ESTIMATED_IMPACT:
  Current host count: 10 (all on-demand), avg cost $1,401.60/month
  Projected host count: 6 on-demand + 4 spot, cost $840.96 + $168.16
  Host reduction: 0 (same count, provider mix change)
  Monthly savings: $792.48 (4 hosts shifted from on-demand to spot)
    on-demand: 6 × 730 × $0.192 = $840.96
    spot: 4 × 730 × $0.058 = $169.36
    current: 10 × 730 × $0.192 = $1,401.60
    savings: $1,401.60 - $1,010.32 = $391.28/month (conservative)
  Assumptions: m5.xlarge, us-east-1, 70% spot discount, steady-state.
MIGRATION_STEPS:
  1. Create spot capacity provider + ASG.
  2. Update service: on-demand base=2 weight=1, spot weight=4.
  3. Monitor spot interruption handling for 7 days.
CONFIRM: About to add spot CP to ecs-api-cluster. Monthly savings ~$391
  (28%). Proceed? (yes/no)
```

## Worked example — binpack placement switch

```text
TARGET: ecs-worker-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster uses spread-by-host placement. 15 m5.2xlarge hosts
  (8 vCPU, 32 GB each) running 1 task per host (1 vCPU, 4 GB each).
  6 of 15 hosts have 0 tasks. Switching to binpack-by-memory allows
  8 tasks per host, reducing required hosts from 15 to 3.
RECOMMENDATION:
  Current: spread-by-host, 15 hosts, 1 task per host
  Proposed: binpack-by-memory + spread-by-az, 3 hosts, 5 tasks per host
  Dimensions changed: placement_strategy + bin_packing
  Dimensions checked: cp_strategy ✓  managed_scaling ✓  target_tracking ✓
    cooldown ✓  bin_packing → (enable)  fargate ✓  warmup ✓  drain ✓
    desired_running_gap ✓  placement_strategy → (spread→binpack)
    scaling_mode ✓
  Confidence: HIGH — each task uses 1 vCPU + 4 GB; 8 vCPU + 32 GB host
    supports 8 tasks with no contention. AZ spread maintains availability.
ESTIMATED_IMPACT:
  Current host count: 15 (9 active + 6 empty), avg CPU 30%
  Projected host count: 3, avg CPU 63% (5 tasks × 1 vCPU / 8 vCPU)
  Host reduction: 12 (80%)
  Monthly savings: $3,352.32
    12 hosts × 730 h × $0.384/h = $3,352.32
  Assumptions: m5.2xlarge, us-east-1, 5 tasks per host (62.5% CPU,
    62.5% memory utilization — healthy headroom).
MIGRATION_STEPS:
  1. Update placement strategy to binpack + AZ spread:
     aws ecs update-service --cluster ecs-worker-cluster --service worker-svc \
       --placement-strategy type=binpack,field=memory type=spread,field=attribute:ecs.availability-zone
  2. New tasks will pack densely; existing tasks continue on current hosts.
  3. Managed scaling will scale-in empty hosts (managedTermination must be ENABLED).
  4. Monitor task placement and host count for 7 days.
CONFIRM: About to switch placement to binpack on ecs-worker-cluster.
  Host reduction 80%; monthly savings $3,352. Proceed? (yes/no)
```

## Worked example — target tracking metric switch

```text
TARGET: ecs-jvm-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster uses CPU-only target tracking (60%) on memory-bound JVM
  workload. CPU stays at 35% (never triggers scale-out) but memory hits
  92% causing 145 OOM kills in 7 days. Switching to memory target
  tracking (70%) or dual-metric policy triggers scale-out before OOM.
RECOMMENDATION:
  Current: CPU target tracking only (ECSServiceAverageCPUUtilization = 60%)
  Proposed: dual-metric: CPU=60% + memory=70%
  Dimensions changed: target_tracking
  Dimensions checked: cp_strategy ✓  managed_scaling ✓  target_tracking →
    (switch to dual)  cooldown ✓  bin_packing ✓  fargate ✓  warmup ✓
    drain ✓  desired_running_gap ✓  placement_strategy ✓  scaling_mode ✓
  Confidence: HIGH — OOM kills correlate with memory > 85%; dual-metric
    ensures scale-out fires on whichever resource breaches threshold.
ESTIMATED_IMPACT:
  Current: 145 OOM kills/week, 12 hosts, CPU 35%, memory 78%
  Projected: 0 OOM kills expected, 14-15 hosts (scale-out on memory)
  Host increase: 2-3 (intentional — adds capacity to prevent OOM)
  Monthly cost increase: +$276.48 (3 × 730 × $0.192 for m5.xlarge)
  Net benefit: eliminates 145 OOM kills/week (availability > cost)
  Assumptions: m5.xlarge, us-east-1, memory target 70% gives 20%
    buffer before OOM risk threshold (90%).
MIGRATION_STEPS:
  1. Add memory target tracking policy (keep existing CPU policy):
     aws application-autoscaling put-scaling-policy --policy-name jvm-mem-scaling \
       --policy-type TargetTrackingScaling --resource-id service/ecs-jvm-cluster/api-svc \
       --scalable-dimension ecs:service:DesiredCount --service-namespace ecs \
       --target-tracking-scaling-policy-configuration TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageMemoryUtilization},ScaleOutCooldown=60,ScaleInCooldown=300
  2. Monitor OOM kills (should drop to 0 within 24 hours).
  3. Monitor host count increase (expected 2-3 additional hosts).
CONFIRM: About to add memory target tracking on ecs-jvm-cluster.
  Cost increase +$276/month; eliminates 145 OOM kills/week. Proceed? (yes/no)
```

## Worked example — already optimal

```text
TARGET: ecs-production-cluster
VERDICT: OPTIMIZED
REASON: Cluster has managed scaling (targetCapacity=100), spot capacity
  provider with on-demand base=2 weight=1 + spot weight=4, binpack +
  AZ spread placement, cooldown 120 s, CPU target tracking at 65%.
  CPU at 62%, memory 55%, 0 empty hosts, 0 OOM kills. All eleven
  dimensions verified. No optimization dimension has positive improvement.
RECOMMENDATION:
  Current: managed scaling on, spot base+weight, binpack+spread, cooldown
    120 s, CPU=65% — no change
  Dimensions checked: cp_strategy ✓  managed_scaling ✓  target_tracking ✓
    cooldown ✓  bin_packing ✓  fargate ✓  warmup ✓  drain ✓
    desired_running_gap ✓  placement_strategy ✓  scaling_mode ✓
  Confidence: HIGH — all eleven dimensions verified; CapacityProviderReservation
    avg 95% confirms tight managed scaling; spot interruptions handled gracefully.
ESTIMATED_IMPACT:
  Current host count: 8 (6 on-demand + 2 spot), avg utilization 62% CPU
  No improvement available.
MIGRATION_STEPS:
  - None required. Re-evaluate if workload pattern changes or at
    quarterly review.
```

## Worked example — NEED_MORE_INFO

```text
TARGET: ecs-new-cluster
VERDICT: NEED_MORE_INFO
REASON: CloudWatch CapacityProviderReservation metric absent over the
  requested 14-day window. The cluster was created 3 days ago and has
  not received production traffic. Cannot evaluate autoscaling
  configuration without baseline utilization data.
RECOMMENDATION:
  Current: managed scaling enabled (default), on-demand only — pending data
  Proposed: pending baseline data
  Confidence: LOW — no utilization metrics to evaluate.
ESTIMATED_IMPACT:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the cluster is receiving traffic:
     aws ecs describe-services --cluster ecs-new-cluster --services <svc> \
       --query 'services[0].{desired:desiredCount,running:runningCount}'
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with CPUUtilization, MemoryUtilization, and
     CapacityProviderReservation data.
  Do NOT optimize based on assumed workload patterns.
```

## CLI and data-source failure handling

### ECS API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-clusters` returns `ClusterNotFound` | API error | Cluster does not exist. Skip. |
| `describe-clusters` shows `status = PROVISIONING` | Status field | Cluster not yet ready. Surface as BLOCKED. |
| `update-service` fails with `InvalidParameterException` | API error | Capacity provider not attached to cluster. Run `put-cluster-capacity-providers` first. |
| `update-capacity-provider` fails with `ResourceNotFoundException` | API error | Capacity provider name wrong or in different region. |
| `create-capacity-provider` fails with `ServiceException` | API error | ASG does not exist or IAM role lacks `ecs:CreateCapacityProvider`. |

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `CapacityProviderReservation` absent | Empty Datapoints | Managed scaling not enabled. Confirm via describe-capacity-providers. |
| `CPUUtilization` absent | Empty Datapoints | No running tasks in window. **NEED_MORE_INFO**. |
| CloudWatch API throttling | Throttling error | Retry with exponential backoff. Fall back to 7-day window, flag LOW-confidence. |

### Application Auto Scaling failures

| Failure mode | Detection | Handling |
|---|---|---|
| `put-scaling-policy` fails with `ObjectNotFoundException` | API error | Service ARN wrong or service does not exist. Verify service name and cluster. |
| `describe-scaling-policies` returns empty | Empty array | No scaling policies configured. This is a finding, not an error — target tracking is not set up. |

## Operational edge cases

### Cluster using EC2 and Fargate capacity providers

**Detection:** `describe-clusters` shows both EC2 and Fargate capacity
providers attached.

**Action:** Evaluate EC2 capacity providers for autoscaling optimization.
Fargate tasks are serverless — no capacity provider tuning applies.
Recommend task-level CPU/memory right-sizing for Fargate tasks separately.

### Legacy Cluster Autoscaler still running

**Detection:** ECS API shows managed scaling DISABLED but EC2 ASG is
scaling. Check for an external autoscaler deployment (Kubernetes
cluster-autoscaler sidecar, Lambda-based scaler, etc.).

**Action:**
1. Disable the legacy autoscaler first.
2. Enable managed scaling on the capacity provider.
3. Running both simultaneously causes race conditions — the managed
   scaler and legacy scaler fight over scaling decisions.

### ASG MinSize blocking scale-in

**Detection:** `CapacityProviderReservation` stays above target but
empty hosts are not terminating.

**Action:**
1. Check ASG `MinSize`: `aws autoscaling describe-groups --auto-scaling-group-names <asg> --query 'AutoScalingGroups[0].MinSize'`
2. If `MinSize` equals current host count, the ASG cannot scale in further.
3. Reduce `MinSize` to allow managed termination: `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <asg> --min-size <new>`
4. Ensure `managedTermination = ENABLED` on the capacity provider.

### Spot capacity provider with no spot instances available

**Detection:** Spot capacity provider reports 0 registered instances
sustained; tasks stuck in PENDING.

**Action:**
1. Check spot instance availability in the AZ: `aws ec2 describe-spot-price-history`
2. If spot price exceeds on-demand, consider `SpotMaxPrice` override on the ASG launch template.
3. As a fallback, on-demand capacity provider (via base parameter) ensures tasks always have a placement target.

## Extended NEVER list (supplementary anti-patterns)

- NEVER enable managed scaling while the legacy Cluster Autoscaler is
  still running. Disable one before enabling the other to avoid races.

- NEVER set `managedTermination = DISABLED` on a capacity provider with
  managed scaling ENABLED. Managed termination is required for managed
  scale-in; disabling it means empty hosts never terminate.

- NEVER use `spread by host` as the sole placement strategy for
  microservices. It wastes 60-80% of host capacity. Use `binpack` +
  `spread by az` for density + availability.

- NEVER recommend Fargate for tasks requiring > 16 vCPU or > 120 GB
  memory. Fargate has hard limits; use EC2 for large workloads.

- NEVER reduce `instanceWarmupPeriod` below 15 seconds. The ECS agent
  needs time to register; sub-15 s warm-up causes task placement failures
  on instances that aren't ready.

- NEVER set `targetCapacity` below 50 on managed scaling. Low values
  cause aggressive scaling and instability; 100 is the recommended target.

- NEVER recommend spot for workloads that cannot tolerate 2-minute
  interruption. Stateful databases, in-memory caches without
  replication, and single-instance services must use on-demand.

- NEVER assume `desiredCount == runningCount` means healthy placement.
  All tasks could be on one host (single point of failure). Always
  verify AZ spread in the placement.

- NEVER change capacity provider strategy without draining existing
  tasks first. Strategy changes apply to new tasks only; existing tasks
  remain on their current provider until rescheduled.

- NEVER skip the CONFIRM gate before `update-service` with a new
  capacity provider strategy. The change affects production traffic
  routing.

## Production edge cases

### CapacityProviderReservation stuck at 100% with no scale-in

**Scenario:** Managed scaling enabled, `targetCapacity=100`, but hosts
with 0 running tasks are not terminating.

**Diagnosis:**
1. Check `managedTermination` — if DISABLED, ECS cannot terminate instances.
2. Check ASG `MinSize` — may be blocking scale-in.
3. Check for in-flight DRaining instances — managed scaling waits for
   drain to complete before targeting more instances.

**Resolution:**
```bash
aws ecs update-capacity-provider --name <cp> \
  --auto-scaling-group-provider managedTermination=ENABLED

aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <asg> --min-size 1
```

### Spot fleet rebalancing causing cascading drains

**Scenario:** Multiple spot instances receive interruption notices
simultaneously, causing many tasks to reschedule at once.

**Diagnosis:** Spot fleet rebalancing happens when the spot market is
tight. Check `aws ec2 describe-spot-instance-requests` for reclaim rates.

**Resolution:**
1. Increase on-demand `base` to provide more steady-state floor.
2. Diversify across instance types in the ASG launch template (e.g.,
   m5.xlarge + m5a.xlarge + c5.xlarge).
3. Consider Fargate for the most critical services (no spot risk).
